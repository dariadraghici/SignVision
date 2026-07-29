import os
import urllib.request
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),                # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),                # index finger
    (5, 9), (9, 10), (10, 11), (11, 12),           # middle finger
    (9, 13), (13, 14), (14, 15), (15, 16),         # ring finger
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)# little finger
]


class VideoWindow(QMainWindow):
    _POLL_INTERVAL_MS = 15

    def __init__(self, file_path: str):
        super().__init__()
        self.setWindowTitle(f"Video Player - {os.path.basename(file_path)}")
        self.resize(900, 650)

        self.file_path = file_path
        self.capture = cv2.VideoCapture(file_path)
        self.fps = self.capture.get(cv2.CAP_PROP_FPS) or 30
        self.total_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.is_playing = False
        self.is_seeking = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        # Inițializăm detectorul modern MediaPipe Tasks
        self.detector = self._init_detector()

        self.audio_output = QAudioOutput()
        self.media_player = QMediaPlayer()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setSource(QUrl.fromLocalFile(file_path))

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setMinimumSize(800, 500)
        layout.addWidget(self.video_label)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, max(self.total_frames - 1, 0))
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        layout.addWidget(self.slider)

        controls = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.toggle_play)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_video)

        controls.addWidget(self.play_btn)
        controls.addWidget(self.stop_btn)
        layout.addLayout(controls)

        if not self.capture.isOpened():
            self.video_label.setText("Could not open video file")
        else:
            self.show_current_frame()

    def _init_detector(self):
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

    def toggle_play(self):
        if not self.capture.isOpened():
            return

        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_btn.setText("Pause")
            self._sync_audio_position()
            self.media_player.play()
            self.timer.start(self._POLL_INTERVAL_MS)
        else:
            self.play_btn.setText("Play")
            self.timer.stop()
            self.media_player.pause()

    def stop_video(self):
        self.is_playing = False
        self.play_btn.setText("Play")
        self.timer.stop()
        self.media_player.stop()
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.slider.setValue(0)
        self.show_current_frame()

    def update_frame(self):
        if self.is_seeking:
            return

        target_ms = self.media_player.position()
        target_frame = int(target_ms / 1000.0 * self.fps)

        if self.total_frames and target_frame >= self.total_frames:
            self.toggle_play()
            return

        current_frame = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
        if target_frame <= current_frame:
            return

        if target_frame - current_frame > 2:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

        ok, frame = self.capture.read()
        if not ok:
            self.toggle_play()
            return

        frame = self.process_frame(frame)
        self.display_frame(frame)

        current = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
        self.slider.blockSignals(True)
        self.slider.setValue(min(current, self.slider.maximum()))
        self.slider.blockSignals(False)

    def process_frame(self, frame):
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

    def show_current_frame(self):
        pos = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
        ok, frame = self.capture.read()
        if ok:
            frame = self.process_frame(frame)
            self.display_frame(frame)
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, pos)

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

    def on_slider_pressed(self):
        self.is_seeking = True
        if self.is_playing:
            self.media_player.pause()

    def on_slider_released(self):
        frame_no = self.slider.value()
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        self.is_seeking = False
        self._sync_audio_position()
        if self.is_playing:
            self.media_player.play()
        else:
            self.show_current_frame()

    def _sync_audio_position(self):
        current_frame = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
        ms = int(current_frame / self.fps * 1000)
        self.media_player.setPosition(ms)

    def closeEvent(self, event):
        self.timer.stop()
        self.media_player.stop()
        if hasattr(self, 'detector') and self.detector:
            self.detector.close()
        if self.capture is not None:
            self.capture.release()
        event.accept()
