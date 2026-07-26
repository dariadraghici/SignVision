import cv2
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap


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

        # Auto-start as soon as the window opens
        self.start_camera()

    def start_camera(self):
        if self.capture is not None:
            return

        # cv2.CAP_DSHOW is the recommended backend on Windows for fast open times
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

        frame = self.process_frame(frame)

        self.display_frame(frame)

    def process_frame(self, frame):
        """Placeholder hook for CV/model inference. Customize later."""
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
        event.accept()
