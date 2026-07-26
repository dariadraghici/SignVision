import os
import cv2
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


class VideoWindow(QMainWindow):
    _POLL_INTERVAL_MS = 15 # polling interval for video frame updates in milliseconds

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

        # audio playback (sound only, no video surface)
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
            self.toggle_play()  # reached end of video
            return

        current_frame = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
        if target_frame <= current_frame: # on time or ahead, just read the next frame
            return

        if target_frame - current_frame > 2: # more than 2 frames behind, seek to the target frame
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

        ok, frame = self.capture.read()
        if not ok:
            self.toggle_play()  # reached end of video
            return

        frame = self.process_frame(frame)
        self.display_frame(frame)

        current = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
        self.slider.blockSignals(True)
        self.slider.setValue(min(current, self.slider.maximum()))
        self.slider.blockSignals(False)

    def process_frame(self, frame):
        """Placeholder hook for CV/model inference. Customize later."""
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
        if self.capture is not None:
            self.capture.release()
        event.accept()
