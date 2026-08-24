import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QGraphicsDropShadowEffect
)

from app.icons import make_icon_pixmap, hex_to_rgb


class SubtitleReadyDialog(QDialog):
    """Small themed popup shown when a video finishes playing or is closed."""

    ACCENT = "#8ab090"

    def __init__(self, transcript_text: str, default_filename: str = "video_subtitles.txt",
                 heading: str = "Playback finished", on_downloaded=None, parent=None):
        super().__init__(parent)
        self.transcript_text = transcript_text or ""
        self.default_filename = default_filename
        self.saved = False
        self.on_downloaded = on_downloaded

        self.setWindowTitle("Video Subtitles")
        self.setModal(True)
        self.setFixedSize(440, 340)
        self.setStyleSheet("""
            QDialog {
                background-color: #121414;
            }
            QLabel {
                background: transparent;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 26)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignHCenter)

        accent_rgb = hex_to_rgb(self.ACCENT)

        icon_circle = QLabel()
        icon_circle.setFixedSize(58, 58)
        icon_circle.setAlignment(Qt.AlignCenter)
        icon_circle.setStyleSheet(f"""
            background-color: rgba({accent_rgb}, 30);
            border: 1px solid rgba({accent_rgb}, 60);
            border-radius: 29px;
        """)
        icon_label = QLabel(icon_circle)
        icon_pixmap = make_icon_pixmap("file_play", "#e8e4dc", 26)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedSize(26, 26)
        icon_label.move(16, 16)
        root.addWidget(icon_circle, alignment=Qt.AlignHCenter)
        root.addSpacing(16)

        title = QLabel(heading)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #e8e4dc; font-size: 18px; font-weight: 700;")
        root.addWidget(title)
        root.addSpacing(8)

        description = QLabel(
            "The subtitles for the video you watched are ready below.\n"
            "You can download them, or close this window."
        )
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        description.setStyleSheet("color: #b8b3a8; font-size: 13px;")
        root.addWidget(description)
        root.addSpacing(20)

        self.download_btn = QPushButton("Download .txt file")
        self.download_btn.setFixedHeight(44)
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4d6150, stop:1 #3a4a3d
                );
                color: #e8e4dc;
                font-size: 14px;
                font-weight: 600;
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 22px;
                padding: 0 22px;
            }}
            QPushButton:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3a4a3d, stop:1 #4d6150
                );
            }}
        """)
        self.download_btn.clicked.connect(self._handle_download)
        root.addWidget(self.download_btn)
        root.addSpacing(10)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #8ab090; font-size: 12px;")
        root.addWidget(self.status_label)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(shadow)

    def _handle_download(self):
        suggested_path = self.default_filename
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Subtitles", suggested_path, "Text Files (*.txt)"
        )
        if not path:
            return

        if not path.lower().endswith(".txt"):
            path += ".txt"

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.transcript_text)
            self.saved = True
            self.status_label.setText(f"Saved successfully: {os.path.basename(path)}")
            self.status_label.setStyleSheet("color: #8ab090; font-size: 12px;")
            if self.on_downloaded:
                self.on_downloaded()
        except OSError as e:
            self.status_label.setText(f"Error saving file: {e}")
            self.status_label.setStyleSheet("color: #d98c8c; font-size: 12px;")
