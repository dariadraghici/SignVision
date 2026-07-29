from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QStackedWidget, QWidget
)

from app.background import BackgroundWidget
from app.branding import BrandHeader
from app.source_card import SourceCard
from app.footer_bar import FooterBar
from app.camera_window import CameraWindow
from app.video_window import VideoWindow


class LauncherWindow(QMainWindow):
    """Startup window: container cu ecrane interschimbabile."""

    SUPPORTED_EXTENSIONS = (".mp4", ".mov", ".avi")

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SignVision")
        self.setMinimumSize(1020, 840)

        # Widget-ul principal de fundal
        self.background_widget = BackgroundWidget()
        self.setCentralWidget(self.background_widget)

        bg_layout = QVBoxLayout(self.background_widget)
        bg_layout.setContentsMargins(0, 0, 0, 0)

        # StackedWidget controlează ce ecran este afișat în cadrul aceleiași ferestre
        self.stacked_widget = QStackedWidget()
        bg_layout.addWidget(self.stacked_widget)

        # Ecran 0: Meniul Principal
        self.menu_widget = QWidget()
        self.setup_menu_ui()
        self.stacked_widget.addWidget(self.menu_widget)

        # Ecran 1: Stream-ul Camerei
        self.camera_page = CameraWindow(on_back_click=self.go_to_menu)
        self.stacked_widget.addWidget(self.camera_page)

        # Ecran 2: Player-ul Video
        self.video_page = VideoWindow(on_back_click=self.go_to_menu)
        self.stacked_widget.addWidget(self.video_page)

    def setup_menu_ui(self):
        root = QVBoxLayout(self.menu_widget)
        root.setContentsMargins(60, 40, 60, 32)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignHCenter)

        # Brand header
        root.addWidget(BrandHeader(), alignment=Qt.AlignHCenter)
        root.addSpacing(36)

        # Carduri de opțiuni
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
        self.stacked_widget.setCurrentWidget(self.camera_page)
        self.camera_page.start_camera()

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

        self.video_page.load_video(file_path)
        self.stacked_widget.setCurrentWidget(self.video_page)

    def go_to_menu(self):
        self.camera_page.stop_camera()
        self.video_page.stop_video()
        self.stacked_widget.setCurrentWidget(self.menu_widget)
