"""
Motion-based recognizer for ASL letters that are drawn as a movement instead
of held as a static hand pose (currently: J and Z).

The static, per-frame classifier in sign_recognizer.py can only ever see one
"frozen" moment of a J or Z, which looks like an unrelated static letter
(I-handshape or D/1-handshape) and pollutes its training data. This module
tracks the path the index fingertip travels across a short window of frames
and classifies the *shape* of that path instead, completely separately from
the static classifier.
"""

import os
import pickle
from collections import deque

import numpy as np

# Number of consecutive frames kept in the tracking buffer
BUFFER_SIZE = 20

RESAMPLE_POINTS = 12

MOTION_PATH_THRESHOLD = 2.6

MOTION_NET_DISPLACEMENT_THRESHOLD = 1.5

MOTION_DIRECTIONALITY_MIN = 0.35

MOTION_HOLD_FRAMES = 12

# Minimum classifier confidence to accept a motion prediction at all.
MIN_MOTION_CONFIDENCE = 0.65

HANDSHAPE_MATCH_MIN_RATIO = 0.55

HANDSHAPE_DEBUG = False

FINGERTIP_INDEX = 8    # index fingertip landmark
WRIST_INDEX = 0
MIDDLE_MCP_INDEX = 9   # used for palm-size normalization, same as sign_recognizer.py

# Landmark indices for the finger-extension checks below
INDEX_TIP, INDEX_PIP, INDEX_MCP = 8, 6, 5
MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP = 12, 10, 9
RING_TIP, RING_PIP, RING_MCP = 16, 14, 13
PINKY_TIP, PINKY_PIP, PINKY_MCP = 20, 18, 17

# Fingers considered for handshape matching
_EXPECTED_HANDSHAPES = {
    # I-handshape: only the pinky extended. J is drawn starting from this pose.
    "J": {"index": False, "middle": False, "ring": False, "pinky": True},
    # D/1-handshape: only the index finger extended. Z is drawn from this pose.
    "Z": {"index": True, "middle": False, "ring": False, "pinky": False},
}


def _landmark_dist(a, b) -> float:
    """3D distance between two MediaPipe landmarks."""
    return float(np.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2))


def _finger_extended(landmarks, tip_idx, pip_idx, mcp_idx) -> bool:
    """ratio of two distances taken from the same frame"""
    dist_tip = _landmark_dist(landmarks[tip_idx], landmarks[mcp_idx])
    dist_pip = _landmark_dist(landmarks[pip_idx], landmarks[mcp_idx])
    return dist_tip > dist_pip * 1.15


def classify_handshape(landmarks) -> dict:
    """Which fingers are extended in this single frame."""
    return {
        "index": _finger_extended(landmarks, INDEX_TIP, INDEX_PIP, INDEX_MCP),
        "middle": _finger_extended(landmarks, MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP),
        "ring": _finger_extended(landmarks, RING_TIP, RING_PIP, RING_MCP),
        "pinky": _finger_extended(landmarks, PINKY_TIP, PINKY_PIP, PINKY_MCP),
    }


def _finger_extension_ratios(handshape_buffer) -> dict:
    """ Per-finger extension ratio averaged independently across the whole buffer"""
    if not handshape_buffer:
        return {"index": 0.0, "middle": 0.0, "ring": 0.0, "pinky": 0.0}
    n = len(handshape_buffer)
    return {
        finger: sum(1 for h in handshape_buffer if h[finger]) / n
        for finger in ("index", "middle", "ring", "pinky")
    }


def _handshape_match_score(ratios: dict, expected: dict) -> float:
    """Combines per-finger extension ratios into a single 0..1 agreement score
    against the letter's expected handshape."""
    scores = [ratios[finger] if should_be_extended else (1.0 - ratios[finger])
              for finger, should_be_extended in expected.items()]
    return sum(scores) / len(scores)


def palm_size(landmarks) -> float:
    wrist = landmarks[WRIST_INDEX]
    mcp = landmarks[MIDDLE_MCP_INDEX]
    size = float(np.linalg.norm([mcp.x - wrist.x, mcp.y - wrist.y]))
    return size if size > 1e-6 else 1e-6


def path_length(points: np.ndarray) -> float:
    if len(points) < 2:
        return 0.0
    diffs = np.diff(points, axis=0)
    return float(np.sum(np.linalg.norm(diffs, axis=1)))


def extract_trajectory_features(points: np.ndarray) -> np.ndarray:
    """points: array of shape (N, 2) with (x, y) already normalized by palm size """
    n = len(points)
    if n < 2:
        return np.zeros(RESAMPLE_POINTS * 2)

    src_idx = np.linspace(0, n - 1, n)
    dst_idx = np.linspace(0, n - 1, RESAMPLE_POINTS)
    resampled_x = np.interp(dst_idx, src_idx, points[:, 0])
    resampled_y = np.interp(dst_idx, src_idx, points[:, 1])
    resampled = np.stack([resampled_x, resampled_y], axis=1)

    resampled = resampled - resampled[0]

    return resampled.flatten()


class MotionGestureRecognizer:
    """Tracks the index fingertip across frames and recognizes J / Z strokes."""

    def __init__(self, model_path="motion_model.pkl"):
        self.model = None
        if os.path.exists(model_path):
            try:
                with open(model_path, "rb") as f:
                    self.model = pickle.load(f)
                print(f"[MotionRecognizer] motion model loaded from {model_path}")
            except Exception as e:
                print(f"[MotionRecognizer] Failed to load motion model: {e}")

        self._buffer = deque(maxlen=BUFFER_SIZE)
        self._handshape_buffer = deque(maxlen=BUFFER_SIZE)
        self._hold_letter = None
        self._hold_conf = 0.0
        self._hold_frames_left = 0

    def reset(self):
        self._buffer.clear()
        self._handshape_buffer.clear()
        self._hold_letter = None
        self._hold_frames_left = 0

    def _handshape_ratio(self, letter: str) -> float:
        """Handshape match score (0..1) for `letter` over the current
        buffer. Returns 1.0 (i.e. "no objection") for any letter without a
        registered expected handshape."""
        expected = _EXPECTED_HANDSHAPES.get(letter)
        if expected is None or not self._handshape_buffer:
            return 1.0
        ratios = _finger_extension_ratios(self._handshape_buffer)
        return _handshape_match_score(ratios, expected)

    def update(self, landmarks):
        """ Call once per frame with the current hand landmarks. """
        palm = palm_size(landmarks)
        tip = landmarks[FINGERTIP_INDEX]
        self._buffer.append((tip.x / palm, tip.y / palm))
        self._handshape_buffer.append(classify_handshape(landmarks))

        if self._hold_frames_left > 0:
            self._hold_frames_left -= 1
            return self._hold_letter, self._hold_conf

        if self.model is None or len(self._buffer) < BUFFER_SIZE:
            return None, 0.0

        points = np.array(self._buffer)

        total_path = path_length(points)
        if total_path < MOTION_PATH_THRESHOLD:
            return None, 0.0

        net_displacement = float(np.linalg.norm(points[-1] - points[0]))
        if net_displacement < MOTION_NET_DISPLACEMENT_THRESHOLD:
            # Traveled some distance overall, but ended up back near the
            # start - that's jitter/tremor, not a stroke.
            return None, 0.0

        if (net_displacement / total_path) < MOTION_DIRECTIONALITY_MIN:
            # Moved a lot but not in a consistent direction (lots of
            # back-and-forth) - also jitter, not a deliberate gesture.
            return None, 0.0

        features = extract_trajectory_features(points).reshape(1, -1)
        try:
            pred = self.model.predict(features)[0]
            conf = 0.75
            if hasattr(self.model, "predict_proba"):
                conf = float(np.max(self.model.predict_proba(features)[0]))
        except Exception:
            return None, 0.0

        if conf < MIN_MOTION_CONFIDENCE:
            return None, 0.0

        predicted_letter = str(pred)
        handshape_ratio = self._handshape_ratio(predicted_letter)

        if HANDSHAPE_DEBUG:
            finger_ratios = _finger_extension_ratios(self._handshape_buffer)
            expected = _EXPECTED_HANDSHAPES.get(predicted_letter, {})
            per_finger = " ".join(
                f"{finger}={finger_ratios[finger]:.2f}(want {'ext' if want else 'flex'})"
                for finger, want in expected.items()
            )
            print(f"[MotionRecognizer] predicted={predicted_letter} "
                  f"traj_conf={conf:.2f} handshape_ratio={handshape_ratio:.2f} "
                  f"(min required={HANDSHAPE_MATCH_MIN_RATIO}) | {per_finger}")

        if handshape_ratio < HANDSHAPE_MATCH_MIN_RATIO:
            return None, 0.0

        self._hold_letter = predicted_letter
        self._hold_conf = conf
        self._hold_frames_left = MOTION_HOLD_FRAMES
        self._buffer.clear()
        self._handshape_buffer.clear()
        return self._hold_letter, self._hold_conf