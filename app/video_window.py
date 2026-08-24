import os
import urllib.request
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from app.sign_recognizer import SignLanguageRecognizer
from app.subtitle_dialog import SubtitleReadyDialog

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)
]

FACE_OVAL = [
    (10, 338), (338, 297), (297, 332), (332, 284), (284, 251), (251, 389), (389, 356), (356, 454),
    (454, 323), (323, 361), (361, 288), (288, 397), (397, 365), (365, 379), (379, 378), (378, 400),
    (400, 377), (377, 152), (152, 148), (148, 176), (176, 149), (149, 150), (150, 136), (136, 172),
    (172, 58), (58, 132), (132, 93), (93, 234), (234, 127), (127, 162), (162, 21), (21, 54),
    (54, 103), (103, 67), (67, 109), (109, 10)
]

LIPS = [
    (61, 146), (146, 91), (91, 181), (181, 84), (84, 17), (17, 314), (314, 405), (405, 321), (321, 375),
    (375, 291), (291, 61), (61, 185), (185, 40), (40, 39), (39, 37), (37, 0), (0, 267), (267, 269),
    (269, 270), (270, 409), (409, 291)
]

LEFT_EYE = [(33, 160), (160, 158), (158, 133), (133, 153), (153, 144), (144, 33)]
RIGHT_EYE = [(362, 385), (385, 387), (387, 263), (263, 373), (373, 380), (380, 362)]

LEFT_EYEBROW = [(70, 63), (63, 105), (105, 66), (66, 107)]
RIGHT_EYEBROW = [(336, 296), (296, 334), (334, 293), (293, 300)]

NOSE = [(168, 6), (6, 197), (197, 195), (195, 5)]

FACE_CONNECTIONS = FACE_OVAL + LIPS + LEFT_EYE + RIGHT_EYE + LEFT_EYEBROW + RIGHT_EYEBROW + NOSE

UPPER_BODY_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24)
]


class VideoWindow(QWidget):

    _POLL_INTERVAL_MS = 15
    _SIGN_HOLD_FRAMES = 3  # frames a letter must hold steady before being confirmed

    def __init__(self, file_path: str = "", on_back_click=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.on_back_click = on_back_click
        self.capture = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        # Detectors are heavy (hand + face + pose landmarkers). Loading them
        # here would block app startup even if the user never opens a video,
        # so they are created lazily on first use (see _ensure_detectors).
        self.hand_detector = None
        self.face_detector = None
        self.pose_detector = None
        self.sign_recognizer = SignLanguageRecognizer()

        self.spelled_letters = []
        self.last_detected_letter = ""
        self.letter_hold_counter = 0

        # Full record of every subtitle segment seen during this viewing
        # session, kept even after the on-screen buffer is cleared/reset,
        # so it can be exported once the video ends or is closed.
        self.transcript_lines = []
        self.subtitles_downloaded = False

        self.audio_output = QAudioOutput()
        self.media_player = QMediaPlayer()
        self.media_player.setAudioOutput(self.audio_output)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)

        top_bar = QHBoxLayout()
        self.back_btn = QPushButton("← Back to Menu")
        self.back_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 12);
                color: #e8e4dc;
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 24); }
        """)
        self.back_btn.clicked.connect(self._handle_back_clicked)
        top_bar.addWidget(self.back_btn)

        self.clear_text_btn = QPushButton("Clear Subtitles")
        self.clear_text_btn.setStyleSheet("""
            QPushButton {
                background: rgba(180, 80, 80, 0.2);
                color: #e8b0b0;
                border: 1px solid rgba(180, 80, 80, 0.35);
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover { background: rgba(180, 80, 80, 0.35); }
        """)
        self.clear_text_btn.clicked.connect(self.clear_spelled_text)
        top_bar.addWidget(self.clear_text_btn)

        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("""
            background-color: #121414;
            color: #e8e4dc;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 12);
        """)
        self.video_label.setMinimumSize(800, 480)
        layout.addWidget(self.video_label)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        layout.addWidget(self.slider)

        controls = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.play_btn.setStyleSheet("""
            QPushButton {
                background: #7a5a3e;
                color: #e8e4dc;
                border: 1px solid rgba(200, 157, 124, 0.3);
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
            }
            QPushButton:hover { background: #8c684a; }
        """)
        self.play_btn.clicked.connect(self.toggle_play)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 12);
                color: #e8e4dc;
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 24); }
        """)
        self.stop_btn.clicked.connect(self.stop_video)

        controls.addWidget(self.play_btn)
        controls.addWidget(self.stop_btn)
        layout.addLayout(controls)

        if file_path:
            self.load_video(file_path)

    def clear_spelled_text(self):
        if self.spelled_letters:
            self.transcript_lines.append(" ".join(self.spelled_letters))
        self.spelled_letters = []
        self.last_detected_letter = ""

    def load_video(self, file_path: str):
        self._ensure_detectors()

        self.file_path = file_path
        if self.capture is not None:
            self.capture.release()

        self.capture = cv2.VideoCapture(file_path)
        self.fps = self.capture.get(cv2.CAP_PROP_FPS) or 30
        self.total_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.is_playing = False
        self.is_seeking = False

        self.spelled_letters = []
        self.last_detected_letter = ""
        self.letter_hold_counter = 0
        self.transcript_lines = []
        self.subtitles_downloaded = False

        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self.slider.setRange(0, max(self.total_frames - 1, 0))

        if not self.capture.isOpened():
            self.video_label.setText("Could not open video file")
        else:
            self.show_current_frame()

    def _ensure_detectors(self):
        if self.hand_detector is not None:
            return
        self.hand_detector, self.face_detector, self.pose_detector = self._create_detectors()

    def _create_detectors(self):
        hand_model_path = "hand_landmarker.task"
        if not os.path.exists(hand_model_path):
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            urllib.request.urlretrieve(url, hand_model_path)

        hand_options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=hand_model_path),
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        hand_detector = vision.HandLandmarker.create_from_options(hand_options)

        face_model_path = "face_landmarker.task"
        if not os.path.exists(face_model_path):
            url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
            urllib.request.urlretrieve(url, face_model_path)

        face_options = vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=face_model_path),
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        face_detector = vision.FaceLandmarker.create_from_options(face_options)

        pose_model_path = "pose_landmarker.task"
        if not os.path.exists(pose_model_path):
            url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
            urllib.request.urlretrieve(url, pose_model_path)

        pose_options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=pose_model_path),
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        pose_detector = vision.PoseLandmarker.create_from_options(pose_options)

        return hand_detector, face_detector, pose_detector

    def toggle_play(self):
        if not self.capture or not self.capture.isOpened():
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
        if self.capture:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.slider.setValue(0)
        self.show_current_frame()

    def get_transcript_text(self) -> str:
        """Full record of every subtitle segment seen during this viewing
        session, including the one currently on screen."""
        lines = list(self.transcript_lines)
        if self.spelled_letters:
            lines.append(" ".join(self.spelled_letters))
        return "\n".join(lines)

    def _default_txt_filename(self) -> str:
        if self.file_path:
            base = os.path.splitext(os.path.basename(self.file_path))[0]
            return f"{base}_subtitles.txt"
        return "video_subtitles.txt"

    def _show_subtitle_dialog(self, heading: str = "Playback finished"):
        if self.subtitles_downloaded:
            return
        dialog = SubtitleReadyDialog(
            transcript_text=self.get_transcript_text(),
            default_filename=self._default_txt_filename(),
            heading=heading,
            parent=self,
        )
        dialog.exec()
        if dialog.saved:
            self.subtitles_downloaded = True

    def _finish_playback(self):
        """Called when the video reaches its final frame on its own."""
        self.is_playing = False
        self.play_btn.setText("Play")
        self.timer.stop()
        self.media_player.pause()
        self._show_subtitle_dialog(heading="Playback finished")

    def _handle_back_clicked(self):
        """Called when the user closes the video via 'Back to Menu'."""
        self._show_subtitle_dialog(heading="Video closed")
        if self.on_back_click:
            self.on_back_click()

    def update_frame(self):
        if self.is_seeking or not self.capture:
            return

        target_ms = self.media_player.position()
        target_frame = int(target_ms / 1000.0 * self.fps)

        if self.total_frames and target_frame >= self.total_frames:
            self._finish_playback()
            return

        current_frame = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
        if target_frame <= current_frame:
            return

        if target_frame - current_frame > 2:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

        ok, frame = self.capture.read()
        if not ok:
            self._finish_playback()
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

        h, w, _ = frame.shape
        chin_point = None

        face_result = self.face_detector.detect(mp_image)
        if face_result.face_landmarks:
            for face_landmarks in face_result.face_landmarks:
                pts = [(int(lm.x * w), int(lm.y * h)) for lm in face_landmarks]
                
                sample_x = max(0, min(pts[1][0], w - 1))
                sample_y = max(0, min(pts[1][1], h - 1))
                b, g, r = frame[sample_y, sample_x]
                skin_color = (int(b), int(g), int(r))

                if len(pts) > 152:
                    chin_point = pts[152]

                for start_idx, end_idx in FACE_CONNECTIONS:
                    if start_idx < len(pts) and end_idx < len(pts):
                        cv2.line(frame, pts[start_idx], pts[end_idx], skin_color, 1)

                key_indices = [1, 33, 263, 61, 291, 10, 152]
                for idx in key_indices:
                    if idx < len(pts):
                        cv2.circle(frame, pts[idx], 1, skin_color, -1)

        pose_result = self.pose_detector.detect(mp_image)
        if pose_result.pose_landmarks:
            for pose_landmarks in pose_result.pose_landmarks:
                pts = [(int(lm.x * w), int(lm.y * h)) for lm in pose_landmarks]
                
                sample_x = max(0, min(pts[11][0], w - 1))
                sample_y = max(0, min(pts[11][1], h - 1))
                b, g, r = frame[sample_y, sample_x]
                skin_color = (int(b), int(g), int(r))

                for start_idx, end_idx in UPPER_BODY_CONNECTIONS:
                    if start_idx < len(pts) and end_idx < len(pts):
                        cv2.line(frame, pts[start_idx], pts[end_idx], skin_color, 1)

                if len(pts) > 24:
                    sh_x = (pts[11][0] + pts[12][0]) // 2
                    sh_y = (pts[11][1] + pts[12][1]) // 2
                    hip_x = (pts[23][0] + pts[24][0]) // 2
                    hip_y = (pts[23][1] + pts[24][1]) // 2

                    neck_top = chin_point if chin_point is not None else pts[0]
                    cv2.line(frame, (sh_x, sh_y), neck_top, skin_color, 1)
                    cv2.line(frame, (sh_x, sh_y), (hip_x, hip_y), skin_color, 1)

                    key_body_indices = [11, 12, 13, 14, 23, 24]
                    for idx in key_body_indices:
                        if idx < len(pts):
                            cv2.circle(frame, pts[idx], 1, skin_color, -1)

        hand_result = self.hand_detector.detect(mp_image)
        detected_sign = None

        if hand_result.hand_landmarks:
            for hand_landmarks in hand_result.hand_landmarks:
                points = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks]
                
                sample_x = max(0, min(points[9][0], w - 1))
                sample_y = max(0, min(points[9][1], h - 1))
                b, g, r = frame[sample_y, sample_x]
                skin_color = (int(b), int(g), int(r))

                for start_idx, end_idx in HAND_CONNECTIONS:
                    cv2.line(frame, points[start_idx], points[end_idx], skin_color, 1)

                for x, y in points:
                    cv2.circle(frame, (x, y), 2, skin_color, -1)

                letter, confidence = self.sign_recognizer.predict(hand_landmarks)
                if letter:
                    detected_sign = letter
                    min_x = max(0, min([p[0] for p in points]) - 15)
                    min_y = max(0, min([p[1] for p in points]) - 40)
                    max_x = min(w, max([p[0] for p in points]) + 15)
                    max_y = min(h, max([p[1] for p in points]) + 15)

                    cv2.rectangle(frame, (min_x, min_y), (max_x, max_y), (74, 120, 160), 2)
                    badge_text = f"Sign: {letter} ({int(confidence*100)}%)"
                    
                    (text_w, text_h), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                    cv2.rectangle(frame, (min_x, min_y - text_h - 10), (min_x + text_w + 12, min_y), (20, 24, 22), -1)
                    cv2.putText(frame, badge_text, (min_x + 6, min_y - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 200, 220), 2, cv2.LINE_AA)

        if detected_sign:
            if detected_sign == self.last_detected_letter:
                self.letter_hold_counter += 1
                if self.letter_hold_counter == self._SIGN_HOLD_FRAMES:
                    self._append_spelled_letter(detected_sign, w)
            else:
                self.last_detected_letter = detected_sign
                self.letter_hold_counter = 0
        else:
            self.letter_hold_counter = 0

        overlay = frame.copy()
        cv2.rectangle(overlay, (20, h - 65), (w - 20, h - 15), (20, 24, 22), -1)
        frame = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)
        cv2.rectangle(frame, (20, h - 65), (w - 20, h - 15), (74, 120, 160), 1)

        hud_text = " ".join(self.spelled_letters) if self.spelled_letters else "[Processing signs...]"
        cv2.putText(frame, hud_text, (35, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (232, 228, 220), 2, cv2.LINE_AA)

        return frame

    def _append_spelled_letter(self, letter, frame_width):
        """Add a confirmed letter to the subtitle, spaced from the previous one.
        If the resulting text would overflow the subtitle box, the box is
        cleared and this letter starts the next translation instead."""
        self.spelled_letters.append(letter)
        text = " ".join(self.spelled_letters)
        max_text_width = frame_width - 20 - 35 - 15  # box edges minus text start/end padding
        (text_w, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.75, 2)
        if text_w > max_text_width:
            self.transcript_lines.append(" ".join(self.spelled_letters[:-1]))
            self.spelled_letters = [letter]

    def show_current_frame(self):
        if not self.capture or not self.capture.isOpened():
            return
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
        if self.capture:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        self.is_seeking = False
        self._sync_audio_position()
        if self.is_playing:
            self.media_player.play()
        else:
            self.show_current_frame()

    def _sync_audio_position(self):
        if not self.capture:
            return
        current_frame = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
        ms = int(current_frame / self.fps * 1000)
        self.media_player.setPosition(ms)

    def closeEvent(self, event):
        self.timer.stop()
        self.media_player.stop()
        if hasattr(self, 'hand_detector') and self.hand_detector:
            self.hand_detector.close()
        if hasattr(self, 'face_detector') and self.face_detector:
            self.face_detector.close()
        if hasattr(self, 'pose_detector') and self.pose_detector:
            self.pose_detector.close()
        if self.capture is not None:
            self.capture.release()
        event.accept()
