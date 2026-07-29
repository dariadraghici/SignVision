import os
import urllib.request
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap

# Legăturile dintre cele 21 de articulații ale mâinii
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),                # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),                # index finger
    (5, 9), (9, 10), (10, 11), (11, 12),           # middle finger
    (9, 13), (13, 14), (14, 15), (15, 16),         # ring finger
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)# little finger
]


class CameraWindow(QMainWindow):
    """Opens the laptop's default camera and streams frames into the app."""

    def __init__(self, camera_index: int = 0):
        super().__init__()
        self.setWindowTitle("Laptop Camera")
        self.resize(900, 650)

        self.camera_index = camera_index
        self.capture = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        self.detector = self._init_detector()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.video_label = QLabel("Camera is off")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white;")
        self.video_label.setMinimumSize(800, 550)
        layout.addWidget(self.video_label)

        controls = QHBoxLayout()
        self.start_btn = QPushButton("Start Camera")
        self.start_btn.clicked.connect(self.start_camera)
        self.stop_btn = QPushButton("Stop Camera")
        self.stop_btn.clicked.connect(self.stop_camera)
        self.stop_btn.setEnabled(False)

        controls.addWidget(self.start_btn)
        controls.addWidget(self.stop_btn)
        layout.addLayout(controls)

        self.start_camera()

    def _init_detector(self):
        """Descarcă automat modelul hand_landmarker.task dacă nu există și instanțiază detectorul."""
        model_path = "hand_landmarker.task"
        if not os.path.exists(model_path):
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            urllib.request.urlretrieve(url, model_path)

        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        return vision.HandLandmarker.create_from_options(options)

    def start_camera(self):
        if self.capture is not None:
            return

        self.capture = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.capture.isOpened():
            self.video_label.setText("Could not open camera")
            self.capture = None
            return

        self.timer.start(30)  # ~33 FPS
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_camera(self):
        self.timer.stop()
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        self.video_label.setText("Camera is off")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def update_frame(self):
        if self.capture is None:
            return

        ok, frame = self.capture.read()
        if not ok:
            return

        frame = cv2.flip(frame, 1)
        frame = self.process_frame(frame)
        self.display_frame(frame)

    def process_frame(self, frame):
        """Detecție și desenare pe cadru utilizând noul API MediaPipe Tasks."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        result = self.detector.detect(mp_image)

        h, w, _ = frame.shape
        if result.hand_landmarks:
            for hand_landmarks in result.hand_landmarks:
                points = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks]

                for start_idx, end_idx in HAND_CONNECTIONS:
                    cv2.line(frame, points[start_idx], points[end_idx], (212, 212, 45), 2)

                for x, y in points:
                    cv2.circle(frame, (x, y), 5, (247, 85, 168), -1)

        return frame

    def display_frame(self, frame):
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image).scaled(
            self.video_label.width(), self.video_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pixmap)

    def closeEvent(self, event):
        self.stop_camera()
        if hasattr(self, 'detector') and self.detector:
            self.detector.close()
        event.accept()
