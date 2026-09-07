# SignVision

SignVision is a desktop application that recognizes American Sign Language (ASL) in real time using a webcam or a pre-recorded video, and turns it into readable text. It is built with PySide6 (Qt for Python), OpenCV and Google MediaPipe.

The application currently supports the full ASL alphabet (A-Z). The architecture is intentionally modular so that additional vocabulary, gesture sets, or entire sign languages can be added later without rewriting the recognition pipeline.

## Overview

SignVision offers two ways to translate sign language into text:
1. Live camera mode: point your webcam at your hand and the app detects ASL letters in real time, spelling out words on screen as you sign them.
2. Video upload mode: load a `.mp4`, `.mov` or `.avi` file, and the app plays it back while detecting signs frame by frame, producing subtitles you can download as a `.txt` file at the end.

Both modes overlay hand, face and upper-body landmarks on the video feed for visual feedback, and both share the exact same underlying recognition engine.

## Features

- Real-time ASL alphabet recognition (A-Z), including the two motion-based letters J and Z.
- Two independent input sources: live webcam and local video file.
- Hand skeleton, face mesh and upper-body pose overlay drawn directly on the video feed, sampled from the user's own skin tone for a natural look.
- Temporal smoothing to reduce flickering between predictions.
- Automatic "hold to confirm" logic so a letter is only added to the spelled-out text once it has been steady for a few consecutive frames.
- Automatic line wrapping of the on-screen subtitle bar, with full transcript history preserved even when the visible line resets.
- Downloadable `.txt` transcript for video sessions, including a confirmation dialog when the video finishes playing or the window is closed early.
- Custom-drawn UI: gradient logo, iconography rendered from inline SVG, and a soft dark theme built entirely with Qt style sheets (no external image assets required).
- Lazy loading of MediaPipe models: the hand, face and pose landmarkers are only downloaded and initialized the first time the camera or a video is actually opened, keeping application startup fast.
- Fallback rule-based classifier: if no trained machine learning model is present, the app still works using a hand-crafted geometric classifier based on finger angles and distances.
- PyInstaller spec file included for packaging the app as a standalone Windows executable.

## How Recognition Works

Sign language recognition happens in two layers, because ASL letters fall into two different categories:

### 1. Static letters (A, B, C, D, E, F, G, H, I, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y)

Most ASL letters are a fixed hand pose. For every video frame:

1. MediaPipe's Hand Landmarker extracts 21 3D landmarks per detected hand.
2. Landmarks are normalized relative to the wrist and scaled by palm size, so the classifier is independent of hand position, distance from the camera and camera resolution.
3. A feature vector is built from the normalized coordinates plus a set of joint angles (thumb, index, middle, ring and pinky).
4. If a trained Random Forest model (`sign_language_model.pkl`) is available, it predicts the letter and a confidence score.
5. If no trained model is present, a rule-based geometric fallback (`predict_geometric`) infers the letter from finger extension states and fingertip distances (for example: all four fingers extended and thumb tucked in is classified as B).
6. A short rolling history buffer smooths predictions across a couple of frames to reduce flicker between visually similar poses.

### 2. Motion letters (J and Z)

J and Z are not static poses, they are drawn as a movement in the air. A single frozen frame of either one looks identical to an unrelated static letter (I or D), so they are handled by a completely separate pipeline:

1. The index fingertip position is tracked across a rolling buffer of frames (normalized by palm size, so it does not matter how close the hand is to the camera).
2. Once enough motion has been recorded, the path is checked for three things: total distance traveled, net displacement from start to end, and directionality (a deliberate stroke rather than jitter or trembling).
3. If the movement looks like a real gesture, the trajectory is resampled to a fixed number of points and fed into a small dedicated Random Forest model (`motion_model.pkl`).
4. As a safety check, the hand shape observed just before the motion started is compared against the expected starting handshape for that letter (an I-handshape for J, a D/1-handshape for Z), to avoid false positives from unrelated arm movements.
5. Once a motion letter is confidently recognized, it is held on screen for a short number of frames before the system returns control to the static classifier.

This split is what allows the alphabet recognizer to treat J and Z correctly instead of having them collide with, and degrade the accuracy of, the static letters I and D.

### Additional context drawn on screen

Independently from sign recognition, both the camera and video views also run MediaPipe's Face Landmarker and Pose Landmarker to draw a face mesh and an upper-body skeleton. These are purely visual overlays (colored using a sample of the user's own skin tone) and are not currently used as recognition input, but the same architecture would allow non-manual signals (such as facial expression or shoulder movement, which are meaningful in real sign languages) to be incorporated in the future.

## Project Structure

```
app/
  main.py                 app entry point
  launcher.py             main window
  background.py           custom-painted dark background widget
  branding.py             logo, title and tagline header
  source_card.py          reusable card widget for the camera and video
  footer_bar.py           informational footer strip
  icons.py                inline SVG icon and logo rendering
  camera_window.py        live webcam capture, overlay drawing and real-time subtitle building
  video_window.py         video file playback
  subtitle_dialog.py      popup dialog for saving the generated subtitles to a .txt file
  sign_recognizer.py      static ASL letter classifier (ML model + geometric fallback)
  motion_recognizer.py    motion-based classifier for the letters J and Z
  train_classifier.py     standalone scripts for collecting datasets and training both models
vision_app.spec           PyInstaller build specification
```

## Application Flow

1. `main.py` starts the Qt application and shows `LauncherWindow`.
2. `LauncherWindow` displays the branded menu with two options: "Use your computer camera" and "Upload a video". These are backed by a `QStackedWidget` that also holds the camera page and the video page, so switching between them does not create or destroy widgets.
3. Choosing the camera option starts `CameraWindow`, which opens the default webcam, lazily initializes the MediaPipe detectors, and begins a `QTimer`-driven capture loop.
4. Choosing the video option opens a file picker restricted to `.mp4`, `.mov` and `.avi`, then hands the selected path to `VideoWindow`, which plays the file back through `QMediaPlayer` for audio while independently reading and annotating frames through OpenCV for the visual overlay, keeping both in sync by video position.
5. In both windows, every video frame is passed through hand, face and pose detection. Detected hand landmarks are passed to `SignLanguageRecognizer`, which internally delegates to the motion recognizer first and falls back to the static classifier.
6. Confirmed letters are appended to an on-screen subtitle line. When a video finishes playing, or the user navigates back, or closes the app entirely, a dialog offers to save the full transcript as a `.txt` file.

## Training Your Own Models

`train_classifier.py` is a standalone command-line tool (not needed to run the app itself, since a fallback classifier is always available) used to collect training data from your own webcam and train both Random Forest models. It offers four options:

1. Collect a new static dataset (all letters except J and Z): press SPACE to begin recording samples for each letter, one landmark snapshot at a time.
2. Train the static model from the existing dataset (`sign_dataset.pkl` to `sign_language_model.pkl`).
3. Collect a new motion dataset (J and Z only): press SPACE to record a full gesture as a sequence of frames per sample.
4. Train the motion model from the existing motion dataset (`motion_dataset.pkl` to `motion_model.pkl`).

The static and motion pipelines are kept strictly separate. If an older combined dataset still contains J or Z entries, they are automatically filtered out before training the static model, since a single frozen frame of a motion letter would otherwise pollute and confuse the classifier for the static letters it visually resembles.

Both trained models are loaded automatically by the application if present in the working directory; if they are missing, `SignLanguageRecognizer` transparently falls back to its built-in geometric classifier for static letters, and simply skips motion recognition for J and Z.

## Requirements

- Python 3.9+
- PySide6 (including `QtMultimedia` and `QtSvg`)
- OpenCV (`opencv-python`)
- MediaPipe
- NumPy
- scikit-learn (only required for training or loading trained models)

Example installation:

```bash
pip install PySide6 opencv-python mediapipe numpy scikit-learn
```

On first use of the camera or a video, the application automatically downloads the required MediaPipe task files (`hand_landmarker.task`, `face_landmarker.task`, `pose_landmarker_lite.task`) into the working directory if they are not already present.

## Running the Application

```bash
python main.py
```

## Building a Standalone Executable

A PyInstaller spec file is provided for building a Windows executable:

```bash
pyinstaller vision_app.spec
```

The resulting build will be available at `dist/SignVision/SignVision.exe`.

## Roadmap

The application currently recognizes only the ASL fingerspelling alphabet. Planned directions for expansion include:
- Recognition of full ASL words and common phrases, not just individual letters.
- Support for additional sign languages beyond ASL.
- Incorporating non-manual signals (facial expression, head and shoulder movement) already captured by the pose and face overlays into the recognition logic itself.
- Two-hand gesture support (the current pipeline focuses on single-hand fingerspelling).
- Improved word-level segmentation and autocorrection of spelled-out text.