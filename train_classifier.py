"""
Script for training machine learning models for ASL sign recognition.

There are two, independent pipelines here:

  1. Static pose pipeline (option 1/2): collects one hand-landmark snapshot
     per sample for the 24 letters that are a fixed handshape, and trains
     the Random Forest used by SignLanguageRecognizer.

  2. Motion pipeline (option 3/4): collects a short *sequence* of frames per
     sample for J and Z (which are drawn as a movement, not a pose), and
     trains the small Random Forest used by MotionGestureRecognizer.

J and Z are intentionally excluded from the static pipeline. Trying to
represent them as a single frozen frame is what made them collide with I and
D-like poses and hurt accuracy on the other letters. If your existing
sign_dataset.pkl still has old J/Z entries in it from before, they're
filtered out automatically when the dataset is loaded - you don't need to
recollect the other 24 letters.
"""

import os
import cv2
import pickle
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

from app.sign_recognizer import SignLanguageRecognizer
from app.motion_recognizer import (
    BUFFER_SIZE as MOTION_BUFFER_SIZE,
    palm_size as motion_palm_size,
    extract_trajectory_features,
    FINGERTIP_INDEX,
)

MOTION_LETTERS = ["J", "Z"]
STATIC_LETTERS = [chr(i) for i in range(ord('A'), ord('Z') + 1) if chr(i) not in MOTION_LETTERS]


def _ensure_hand_model():
    hand_model_path = "hand_landmarker.task"
    if not os.path.exists(hand_model_path):
        import urllib.request
        url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
        urllib.request.urlretrieve(url, hand_model_path)
    return hand_model_path


def collect_dataset(output_file="sign_dataset.pkl", samples_per_class=100):
    """Collects static, single-frame samples for every letter EXCEPT J and Z."""
    print("=== Dataset Collection for American Sign Language (static letters) ===")

    existing_data = []
    existing_labels = []
    if os.path.exists(output_file):
        with open(output_file, "rb") as f:
            existing = pickle.load(f)
        raw_data = list(existing["data"])
        raw_labels = list(existing["labels"])

        # Drop any J/Z samples left over from before this file was split
        # into a static + motion pipeline - they don't belong in the static
        # dataset and would hurt the other letters again if kept.
        dropped = 0
        for d, l in zip(raw_data, raw_labels):
            if l in MOTION_LETTERS:
                dropped += 1
                continue
            existing_data.append(d)
            existing_labels.append(l)

        if dropped:
            print(f"Removed {dropped} old J/Z sample(s) from '{output_file}' "
                  f"(those are now collected separately, see collect_motion_dataset).")
        print(f"Found existing dataset '{output_file}' with {len(existing_labels)} usable samples. "
              f"New samples will be appended to it.")

    hand_model_path = _ensure_hand_model()
    options = vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=hand_model_path),
        num_hands=1
    )
    detector = vision.HandLandmarker.create_from_options(options)
    recognizer = SignLanguageRecognizer()

    cap = cv2.VideoCapture(0)
    data = existing_data
    labels = existing_labels

    for letter in STATIC_LETTERS:
        print(f"Prepare for letter: {letter}. Press 'SPACE' to start recording...")
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            cv2.putText(frame, f"Letter: {letter} - Press SPACE to start recording", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.imshow("Dataset Collector", frame)
            key = cv2.waitKey(1)
            if key == 32:  # Space
                break
            elif key == 27:  # Esc
                cap.release()
                cv2.destroyAllWindows()
                if len(labels) > len(existing_labels):
                    with open(output_file, "wb") as f:
                        pickle.dump({"data": np.array(data), "labels": np.array(labels)}, f)
                    print(f"Stopped early. Progress saved to {output_file} "
                          f"({len(labels)} total samples).")
                else:
                    print("Stopped early. No new samples were collected, nothing changed.")
                return

        collected = 0
        while collected < samples_per_class:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = detector.detect(mp_img)

            if res.hand_landmarks:
                lms = res.hand_landmarks[0]
                coords, angles, _ = recognizer.extract_features(lms)
                feat_vec = np.hstack([coords, angles])
                data.append(feat_vec)
                labels.append(letter)
                collected += 1

            cv2.putText(frame, f"Collecting {letter}: {collected}/{samples_per_class}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200, 0), 2)
            cv2.imshow("Dataset Collector", frame)
            cv2.waitKey(20)

    cap.release()
    cv2.destroyAllWindows()

    with open(output_file, "wb") as f:
        pickle.dump({"data": np.array(data), "labels": np.array(labels)}, f)
    print(f"Dataset saved successfully to {output_file}! ({len(labels)} total samples)")


def collect_motion_dataset(output_file="motion_dataset.pkl", samples_per_class=40):
    """
    Collects motion samples for J and Z. Each sample is a short sequence of
    MOTION_BUFFER_SIZE consecutive frames recorded right after SPACE is
    pressed, capturing the whole stroke rather than a single pose.
    """
    print("=== Dataset Collection for American Sign Language (motion letters: J, Z) ===")
    print(f"Each sample records {MOTION_BUFFER_SIZE} frames - perform the full "
          f"gesture right after pressing SPACE and keep going until it stops recording.")

    existing_data = []
    existing_labels = []
    if os.path.exists(output_file):
        with open(output_file, "rb") as f:
            existing = pickle.load(f)
        existing_data = list(existing["data"])
        existing_labels = list(existing["labels"])
        print(f"Found existing motion dataset '{output_file}' with {len(existing_labels)} samples. "
              f"New samples will be appended to it.")

    hand_model_path = _ensure_hand_model()
    options = vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=hand_model_path),
        num_hands=1
    )
    detector = vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    data = existing_data
    labels = existing_labels

    for letter in MOTION_LETTERS:
        print(f"Prepare for letter: {letter}. Press 'SPACE' to start recording a stroke...")
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            cv2.putText(frame, f"Letter: {letter} - Press SPACE to record a full gesture", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.imshow("Motion Dataset Collector", frame)
            key = cv2.waitKey(1)
            if key == 32:  # Space
                break
            elif key == 27:  # Esc
                cap.release()
                cv2.destroyAllWindows()
                if len(labels) > len(existing_labels):
                    with open(output_file, "wb") as f:
                        pickle.dump({"data": np.array(data), "labels": np.array(labels)}, f)
                    print(f"Stopped early. Progress saved to {output_file} "
                          f"({len(labels)} total samples).")
                else:
                    print("Stopped early. No new samples were collected, nothing changed.")
                return

        collected = 0
        while collected < samples_per_class:
            stroke_points = []
            frames_needed = MOTION_BUFFER_SIZE
            while frames_needed > 0:
                ok, frame = cap.read()
                if not ok:
                    break
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                res = detector.detect(mp_img)

                if res.hand_landmarks:
                    lms = res.hand_landmarks[0]
                    palm = motion_palm_size(lms)
                    tip = lms[FINGERTIP_INDEX]
                    stroke_points.append((tip.x / palm, tip.y / palm))
                    frames_needed -= 1

                cv2.putText(frame, f"Recording {letter}: sample {collected + 1}/{samples_per_class}",
                            (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200, 0), 2)
                cv2.imshow("Motion Dataset Collector", frame)
                cv2.waitKey(20)

            if len(stroke_points) == MOTION_BUFFER_SIZE:
                features = extract_trajectory_features(np.array(stroke_points))
                data.append(features)
                labels.append(letter)
                collected += 1
            # if the hand was lost mid-stroke, the sample is simply discarded
            # and this iteration retries the same letter/count

    cap.release()
    cv2.destroyAllWindows()

    with open(output_file, "wb") as f:
        pickle.dump({"data": np.array(data), "labels": np.array(labels)}, f)
    print(f"Motion dataset saved successfully to {output_file}! ({len(labels)} total samples)")


def train_model(dataset_file="sign_dataset.pkl", model_file="sign_language_model.pkl"):
    if not os.path.exists(dataset_file):
        print(f"File {dataset_file} does not exist! Please collect the data first.")
        return

    with open(dataset_file, "rb") as f:
        dataset = pickle.load(f)

    X = list(dataset["data"])
    y = list(dataset["labels"])

    # Defensive filter: never let J/Z train the static model, even if an
    # older dataset file still has them in it.
    filtered = [(xi, yi) for xi, yi in zip(X, y) if yi not in MOTION_LETTERS]
    if len(filtered) < len(X):
        print(f"Ignoring {len(X) - len(filtered)} J/Z sample(s) found in the static dataset.")
    X, y = [xi for xi, _ in filtered], [yi for _, yi in filtered]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)

    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"Trained Static Model Accuracy: {acc * 100:.2f}%")

    with open(model_file, "wb") as f:
        pickle.dump(clf, f)
    print(f"Model saved successfully to {model_file}!")


def train_motion_model(dataset_file="motion_dataset.pkl", model_file="motion_model.pkl"):
    if not os.path.exists(dataset_file):
        print(f"File {dataset_file} does not exist! Please collect motion data first (option 3).")
        return

    with open(dataset_file, "rb") as f:
        dataset = pickle.load(f)

    X = dataset["data"]
    y = dataset["labels"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(n_estimators=60, max_depth=6, random_state=42)
    clf.fit(X_train, y_train)

    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"Trained Motion Model Accuracy (J/Z): {acc * 100:.2f}%")

    with open(model_file, "wb") as f:
        pickle.dump(clf, f)
    print(f"Motion model saved successfully to {model_file}!")


if __name__ == "__main__":
    print("1. Collect New Static Dataset (A-Z except J, Z)")
    print("2. Train Static Model from Existing Dataset")
    print("3. Collect New Motion Dataset (J, Z only)")
    print("4. Train Motion Model from Existing Motion Dataset")
    choice = input("Choose option (1/2/3/4): ").strip()
    if choice == "1":
        collect_dataset()
        train_model()
        print("Done! The static model has been saved and will be loaded automatically by the application.")
    elif choice == "2":
        train_model()
    elif choice == "3":
        collect_motion_dataset()
        train_motion_model()
        print("Done! The motion model has been saved and will be loaded automatically by the application.")
    elif choice == "4":
        train_motion_model()
