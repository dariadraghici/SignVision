import os
import urllib.request
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap

from app.sign_recognizer import SignLanguageRecognizer

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),                # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),                # index finger
    (5, 9), (9, 10), (10, 11), (11, 12),           # middle finger
    (9, 13), (13, 14), (14, 15), (15, 16),         # ring finger
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)# little finger
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
    (11, 12),  # shoulders
    (11, 13),  # left shoulder -> left elbow
    (13, 15),  # left elbow -> left wrist
    (12, 14),  # right shoulder -> right elbow
    (14, 16),  # right elbow -> right wrist
    (11, 23),  # left shoulder -> left hip
    (12, 24),  # right shoulder -> right hip
    (23, 24),  # base of the torso
]


class CameraWindow(QWidget):
    """Integrated camera stream with hand, face, and pose detection, plus sign language recognition."""

    def __init__(self, on_back_click=None, camera_index: int = 0, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.capture = None
        self.on_back_click = on_back_click

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        self.hand_detector, self.face_detector, self.pose_detector = self._init_detectors()
        self.sign_recognizer = SignLanguageRecognizer()

        self.spelled_text = ""
        self.last_detected_letter = ""
        self.letter_hold_counter = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)

        top_bar = QHBoxLayout()
        self.back_btn = QPushButton("← Back to Menu")
        self.back_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 15);
                color: white;
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 30); }
        """)
        if self.on_back_click:
            self.back_btn.clicked.connect(self.on_back_click)
        top_bar.addWidget(self.back_btn)

        self.clear_text_btn = QPushButton("Șterge Text")
        self.clear_text_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.2);
                color: #fca5a5;
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover { background: rgba(239, 68, 68, 0.4); }
        """)
        self.clear_text_btn.clicked.connect(self.clear_spelled_text)
        top_bar.addWidget(self.clear_text_btn)

        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.video_label = QLabel("Camera is off")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white; border-radius: 12px;")
        self.video_label.setMinimumSize(800, 500)
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

    def clear_spelled_text(self):
        self.spelled_text = ""
        self.last_detected_letter = ""

    def _init_detectors(self):
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

    def start_camera(self):
        if self.capture is not None:
            return

        self.capture = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.capture.isOpened():
            self.video_label.setText("Could not open camera")
            self.capture = None
            return

        self.timer.start(30)
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
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        h, w, _ = frame.shape
        chin_point = None

        # face
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

        # body pose
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

        # hand and sign recognition
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

                # sign language recognition
                letter, confidence = self.sign_recognizer.predict(hand_landmarks)
                if letter:
                    detected_sign = letter
                    min_x = max(0, min([p[0] for p in points]) - 15)
                    min_y = max(0, min([p[1] for p in points]) - 40)
                    max_x = min(w, max([p[0] for p in points]) + 15)
                    max_y = min(h, max([p[1] for p in points]) + 15)

                    cv2.rectangle(frame, (min_x, min_y), (max_x, max_y), (45, 212, 191), 2)
                    badge_text = f"Letter: {letter} ({int(confidence*100)}%)"
                    
                    (text_w, text_h), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                    cv2.rectangle(frame, (min_x, min_y - text_h - 10), (min_x + text_w + 12, min_y), (15, 23, 42), -1)
                    cv2.putText(frame, badge_text, (min_x + 6, min_y - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (45, 212, 191), 2, cv2.LINE_AA)

        # Update spelled text based on detected sign
        if detected_sign:
            if detected_sign == self.last_detected_letter:
                self.letter_hold_counter += 1
                if self.letter_hold_counter == 3:
                    self.spelled_text += detected_sign
            else:
                self.last_detected_letter = detected_sign
                self.letter_hold_counter = 0
        else:
            self.letter_hold_counter = 0

        # HUD bar for displaying the spelled text
        overlay = frame.copy()
        cv2.rectangle(overlay, (20, h - 65), (w - 20, h - 15), (15, 23, 42), -1)
        frame = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)
        cv2.rectangle(frame, (20, h - 65), (w - 20, h - 15), (45, 212, 191), 1)

        hud_text = f"Detected Text: {self.spelled_text if self.spelled_text else '[Waiting for signs...]'}"
        cv2.putText(frame, hud_text, (35, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)

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
        if hasattr(self, 'hand_detector') and self.hand_detector:
            self.hand_detector.close()
        if hasattr(self, 'face_detector') and self.face_detector:
            self.face_detector.close()
        if hasattr(self, 'pose_detector') and self.pose_detector:
            self.pose_detector.close()
        event.accept()
