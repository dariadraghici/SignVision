from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox
)

from app.background import BackgroundWidget
from app.branding import BrandHeader
from app.source_card import SourceCard
from app.footer_bar import FooterBar
from app.camera_window import CameraWindow
from app.video_window import VideoWindow


class LauncherWindow(QMainWindow):
    """Startup window: choose between the laptop camera or a video file."""

    SUPPORTED_EXTENSIONS = (".mp4", ".mov", ".avi")

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SignVision")
        self.setMinimumSize(1020, 840)

        self.camera_window = None
        self.video_window = None

        central = BackgroundWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(60, 40, 60, 32)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignHCenter)

        # logo, title, tagline, description
        root.addWidget(BrandHeader(), alignment=Qt.AlignHCenter)
        root.addSpacing(36)

        # Cards
        cards_row = QHBoxLayout()
        cards_row.setSpacing(28)

        camera_card = SourceCard(
            icon_name="webcam",
            accent_start="#2dd4bf",
            accent_end="#22d3ee",
            title="Use your computer camera",
            description="Open your camera and detect sign language in real-time.",
            button_text="Start Camera",
            button_icon="webcam",
            on_click=self.open_camera,
        )
        video_card = SourceCard(
            icon_name="clapper",
            accent_start="#a855f7",
            accent_end="#c026d3",
            title="Upload a video",
            description="Upload a video with sign language and get subtitles instantly.",
            button_text="Choose Video",
            button_icon="upload",
            on_click=self.open_video_dialog,
        )

        cards_row.addWidget(camera_card)
        cards_row.addWidget(video_card)
        root.addLayout(cards_row)
        root.addStretch()

        # Footer
        root.addWidget(FooterBar())

    def open_camera(self):
        self.camera_window = CameraWindow()
        self.camera_window.show()

    def open_video_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a video file",
            "",
            "Video Files (*.mp4 *.mov *.avi)"
        )
        if not file_path:
            return

        if not file_path.lower().endswith(self.SUPPORTED_EXTENSIONS):
            QMessageBox.warning(
                self, "Unsupported format",
                "Please select a .mp4, .mov or .avi file."
            )
            return

        self.video_window = VideoWindow(file_path)
        self.video_window.show()
