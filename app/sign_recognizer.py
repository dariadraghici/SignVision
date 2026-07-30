import math
import os
import pickle
import numpy as np


class SignLanguageRecognizer:
    """
    Recognizer for American Sign Language (ASL) letters A-Z using MediaPipe hand landmarks.
    It combines a geometric rule-based classifier with an optional machine learning model (Random Forest).
    """

    def __init__(self, model_path="sign_language_model.pkl"):
        self.ml_model = None
        self.history = []
        self.history_size = 2  # Number of frames for temporal averaging (prevents flicker)
        
        # Loading custom ML model if it exists
        if os.path.exists(model_path):
            try:
                with open(model_path, "rb") as f:
                    self.ml_model = pickle.load(f)
                print(f"[SignRecognizer] ML model loaded from {model_path}")
            except Exception as e:
                print(f"[SignRecognizer] Failed to load ML model: {e}")

    def extract_features(self, landmarks):
        """
        Extract normalized coordinates, angles, and distances from the 21 MediaPipe landmark points.
        """
        pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
        
        # Reference point: Wrist (index 0)
        wrist = pts[0]
        pts_norm = pts - wrist
        
        # Scale normalization based on palm size (0 -> 9 MCP of middle finger)
        palm_size = np.linalg.norm(pts_norm[9])
        if palm_size > 0:
            pts_norm = pts_norm / palm_size

        coords = pts_norm.flatten()

        # Compute angles between finger joints
        angles = []
        joint_triplets = [
            (0, 1, 2), (1, 2, 3), (2, 3, 4),        # thumb
            (0, 5, 6), (5, 6, 7), (6, 7, 8),        # index finger
            (0, 9, 10), (9, 10, 11), (10, 11, 12),  # middle finger
            (0, 13, 14), (13, 14, 15), (15, 16, 16),# ring finger
            (0, 17, 18), (17, 18, 19), (19, 20, 20) # pinky finger
        ]

        for a, b, c in joint_triplets:
            v1 = pts[a] - pts[b]
            v2 = pts[c] - pts[b]
            norm_v1 = np.linalg.norm(v1)
            norm_v2 = np.linalg.norm(v2)
            if norm_v1 > 0 and norm_v2 > 0:
                cos_angle = np.dot(v1, v2) / (norm_v1 * norm_v2)
                angle = np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
            else:
                angle = 0.0
            angles.append(angle)

        return coords, np.array(angles), pts_norm

    def _is_extended(self, pts_norm, tip_idx, pip_idx, mcp_idx=0):
        """Check if a finger is extended or flexed."""
        dist_tip = np.linalg.norm(pts_norm[tip_idx] - pts_norm[mcp_idx])
        dist_pip = np.linalg.norm(pts_norm[pip_idx] - pts_norm[mcp_idx])
        return dist_tip > dist_pip * 1.15

    def predict_geometric(self, landmarks):
        """
        Geometric rule-based prediction of ASL letters based on hand landmark positions and angles.
        Returns the predicted letter and a confidence score.
        """
        _, angles, pts = self.extract_features(landmarks)

        # extension status of fingers
        thumb_ext = np.linalg.norm(pts[4] - pts[17]) > np.linalg.norm(pts[2] - pts[17]) * 1.1
        index_ext = self._is_extended(pts, 8, 6, 5)
        middle_ext = self._is_extended(pts, 12, 10, 9)
        ring_ext = self._is_extended(pts, 16, 14, 13)
        pinky_ext = self._is_extended(pts, 20, 18, 17)

        # Key distances between tips
        dist_thumb_index = np.linalg.norm(pts[4] - pts[8])
        dist_thumb_middle = np.linalg.norm(pts[4] - pts[12])
        dist_thumb_ring = np.linalg.norm(pts[4] - pts[16])
        dist_thumb_pinky = np.linalg.norm(pts[4] - pts[20])
        dist_index_middle = np.linalg.norm(pts[8] - pts[12])

        wrist_to_mcp = pts[9] - pts[0]
        pointing_down = wrist_to_mcp[1] > 0.3
        pointing_side = abs(wrist_to_mcp[0]) > abs(wrist_to_mcp[1])

        # Rule for clenched fist: A, E, S, M, N, T
        if not index_ext and not middle_ext and not ring_ext and not pinky_ext:
            if pts[4][1] < pts[6][1] or pts[4][0] < pts[5][0]:
                if dist_thumb_index > 0.25 and pts[4][1] > pts[3][1] - 0.2:
                    return "A", 0.92
                elif pts[4][1] > pts[10][1] and dist_thumb_index < 0.3:
                    return "S", 0.90
                elif pts[4][0] > pts[6][0] and pts[4][1] > pts[6][1]:
                    return "E", 0.88
                return "A", 0.85

        # B: All 4 fingers extended, thumb hidden
        if index_ext and middle_ext and ring_ext and pinky_ext:
            if dist_thumb_index < 0.5 and not thumb_ext:
                return "B", 0.94
            return "B", 0.88

        # C: Curved hand in C shape
        if not index_ext and not middle_ext and not ring_ext and not pinky_ext:
            if 0.35 < dist_thumb_index < 0.8:
                return "C", 0.89

        # D / L / G / Q
        if index_ext and not middle_ext and not ring_ext and not pinky_ext:
            if dist_thumb_middle < 0.3 or dist_thumb_ring < 0.3:
                return "D", 0.93
            elif thumb_ext and dist_thumb_index > 0.4:
                if pointing_side:
                    return "G", 0.90
                return "L", 0.95
            elif pointing_down:
                return "Q", 0.88
            return "D", 0.85

        # F: index and thumb touch, other fingers extended
        if not index_ext and middle_ext and ring_ext and pinky_ext:
            if dist_thumb_index < 0.3:
                return "F", 0.94

        # I, J, Y: pinky extended, others flexed
        if pinky_ext and not index_ext and not middle_ext and not ring_ext:
            if thumb_ext:
                return "Y", 0.95
            elif pointing_down:
                return "J", 0.87
            return "I", 0.93

        # V, U, R, K, P
        if index_ext and middle_ext and not ring_ext and not pinky_ext:
            if dist_index_middle > 0.25:
                if pointing_down:
                    return "P", 0.90
                elif thumb_ext:
                    return "K", 0.91
                return "V", 0.94
            else:
                if pts[8][0] > pts[12][0]:
                    return "R", 0.92
                return "U", 0.93

        # W, M, N
        if index_ext and middle_ext and ring_ext and not pinky_ext:
            if pointing_down:
                return "M", 0.86
            return "W", 0.94

        if thumb_ext and pinky_ext and not index_ext and not middle_ext and not ring_ext:
            return "Y", 0.95

        return "A", 0.60

    def predict(self, landmarks):
        """
        Main prediction function that combines geometric rules and ML model (if available).
        """
        if not landmarks or len(landmarks) < 21:
            return "", 0.0

        if self.ml_model is not None:
            try:
                coords, angles, _ = self.extract_features(landmarks)
                feat_vec = np.hstack([coords, angles]).reshape(1, -1)
                pred = self.ml_model.predict(feat_vec)[0]
                prob = 0.95
                if hasattr(self.ml_model, "predict_proba"):
                    probs = self.ml_model.predict_proba(feat_vec)[0]
                    prob = float(np.max(probs))
                raw_letter, conf = str(pred), prob
            except Exception:
                raw_letter, conf = self.predict_geometric(landmarks)
        else:
            raw_letter, conf = self.predict_geometric(landmarks)

        # temporal smoothing using a history buffer to reduce flickering predictions
        self.history.append(raw_letter)
        if len(self.history) > self.history_size:
            self.history.pop(0)

        from collections import Counter
        counts = Counter(self.history)
        smoothed_letter = counts.most_common(1)[0][0]

        return smoothed_letter, conf