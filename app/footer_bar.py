from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget, QLabel

from app.icons import make_icon_pixmap

# Every section (including its icon/badge + text) is forced to this width,
# so all four footer items line up symmetrically regardless of content length.
SECTION_WIDTH = 210


def _icon_label(name: str, color: str, size: int = 18) -> QLabel:
    label = QLabel()
    label.setPixmap(make_icon_pixmap(name, color, size))
    return label


def _cc_badge() -> QLabel:
    label = QLabel("CC")
    label.setStyleSheet("""
        color: #c4b5fd;
        border: 1.5px solid #c4b5fd;
        border-radius: 5px;
        font-size: 10px;
        font-weight: 700;
        padding: 2px 4px;
        background: transparent;
    """)
    return label


class FooterBar(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("footerBar")
        self.setStyleSheet("""
            QFrame#footerBar {
                background-color: rgba(255, 255, 255, 6);
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 16px;
            }
            QLabel {
                background: transparent;
            }
        """)

        row = QHBoxLayout(self)
        row.setContentsMargins(28, 16, 28, 16)
        row.setSpacing(0)

        sections = [
            self._formats_section(),
            self._simple_section("lightning", "#2dd4bf", "Real-time\nDetection"),
            self._simple_section("target", "#a855f7", "High\nAccuracy"),
            self._cc_section(),
        ]

        row.addStretch(1)
        for index, section in enumerate(sections):
            row.addWidget(section)
            if index < len(sections) - 1:
                row.addWidget(self._divider())
        row.addStretch(1)

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 20); border: none;")
        line.setFixedWidth(1)
        return line

    def _make_section(self, inner_layout: QHBoxLayout) -> QWidget:
        container = QWidget()
        container.setFixedWidth(SECTION_WIDTH)
        outer = QHBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignCenter)
        outer.addLayout(inner_layout)
        return container

    def _formats_section(self) -> QWidget:
        layout = QHBoxLayout()
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignVCenter)

        icon = _icon_label("file_play", "#c4b5fd", 22)
        layout.addWidget(icon, alignment=Qt.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setAlignment(Qt.AlignVCenter)

        label1 = QLabel("Supported video formats:")
        label1.setStyleSheet("color: #9ca3af; font-size: 12px;")
        text_col.addWidget(label1)

        label2 = QLabel(
            '<span style="color:#5eead4;">.mp4</span>&nbsp;&nbsp;'
            '<span style="color:#c084fc;">.mov</span>&nbsp;&nbsp;'
            '<span style="color:#93c5fd;">.avi</span>'
        )
        label2.setStyleSheet("font-size: 13px; font-weight: 600;")
        text_col.addWidget(label2)

        layout.addLayout(text_col)
        return self._make_section(layout)

    def _simple_section(self, icon_name: str, color: str, text: str) -> QWidget:
        layout = QHBoxLayout()
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignVCenter)

        icon = _icon_label(icon_name, color, 18)
        layout.addWidget(icon, alignment=Qt.AlignVCenter)

        label = QLabel(text)
        label.setStyleSheet("color: #d1d5db; font-size: 12px;")
        label.setAlignment(Qt.AlignVCenter)
        layout.addWidget(label, alignment=Qt.AlignVCenter)
        return self._make_section(layout)

    def _cc_section(self) -> QWidget:
        layout = QHBoxLayout()
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignVCenter)

        layout.addWidget(_cc_badge(), alignment=Qt.AlignVCenter)

        label = QLabel("Instant\nSubtitles")
        label.setStyleSheet("color: #d1d5db; font-size: 12px;")
        label.setAlignment(Qt.AlignVCenter)
        layout.addWidget(label, alignment=Qt.AlignVCenter)
        return self._make_section(layout)
