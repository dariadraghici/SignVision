"""
Script for training a machine learning model for ASL sign recognition using collected hand landmark data.
This script allows users to collect a dataset of hand landmarks for each letter A-Z and then train
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


def collect_dataset(output_file="sign_dataset.pkl", samples_per_class=100):
    print("=== Dataset Collection for American Sign Language ===")
    alphabet = [chr(i) for i in range(ord('A'), ord('Z') + 1)]

    existing_data = []
    existing_labels = []
    if os.path.exists(output_file):
        with open(output_file, "rb") as f:
            existing = pickle.load(f)
        existing_data = list(existing["data"])
        existing_labels = list(existing["labels"])
        print(f"Found existing dataset '{output_file}' with {len(existing_labels)} samples. "
              f"New samples will be appended to it.")

    hand_model_path = "hand_landmarker.task"
    if not os.path.exists(hand_model_path):
        import urllib.request
        url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
        urllib.request.urlretrieve(url, hand_model_path)

    options = vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=hand_model_path),
        num_hands=1
    )
    detector = vision.HandLandmarker.create_from_options(options)
    recognizer = SignLanguageRecognizer()

    cap = cv2.VideoCapture(0)
    data = existing_data
    labels = existing_labels

    for letter in alphabet:
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


def train_model(dataset_file="sign_dataset.pkl", model_file="sign_language_model.pkl"):
    if not os.path.exists(dataset_file):
        print(f"File {dataset_file} does not exist! Please collect the data first.")
        return

    with open(dataset_file, "rb") as f:
        dataset = pickle.load(f)

    X = dataset["data"]
    y = dataset["labels"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)

    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"Trained Model Accuracy: {acc * 100:.2f}%")

    with open(model_file, "wb") as f:
        pickle.dump(clf, f)
    print(f"Model saved successfully to {model_file}!")


if __name__ == "__main__":
    print("1. Collect New Dataset")
    print("2. Train Model from Existing Dataset")
    choice = input("Choose option (1/2): ").strip()
    if choice == "1":
        collect_dataset()
        train_model()
        print("Done! The model has been saved and will be loaded automatically by the application.")
    elif choice == "2":
        train_model()