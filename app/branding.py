from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from app.icons import make_logo_pixmap, make_icon_pixmap


class BrandHeader(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignHCenter)

        # Logo
        logo_label = QLabel()
        logo_label.setPixmap(make_logo_pixmap(118))
        logo_label.setFixedSize(118, 118)
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label, alignment=Qt.AlignHCenter)
        layout.addSpacing(2)

        # "SignVision" title
        title = QLabel("SignVision")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #f5f5fa; background: transparent;")
        layout.addWidget(title)
        layout.addSpacing(6)

        # Tagline with flanking dots
        tagline_row = QHBoxLayout()
        tagline_row.setAlignment(Qt.AlignCenter)
        tagline_row.setSpacing(10)

        dot_left = QLabel("•")
        dot_left.setStyleSheet("color: #a855f7; background: transparent; font-size: 13px;")
        tagline_row.addWidget(dot_left)

        tagline = QLabel('<span style="color:#5eead4;">SEE THE SIGNS.</span> ' '<span style="color:#c084fc;">UNDERSTAND EVERY WORD.</span>')
        tagline_font = QFont()
        tagline_font.setPointSize(9)
        tagline_font.setBold(True)
        tagline_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.4)
        tagline.setFont(tagline_font)
        tagline.setStyleSheet("background: transparent;")
        tagline_row.addWidget(tagline)

        dot_right = QLabel("•")
        dot_right.setStyleSheet("color: #2dd4bf; background: transparent; font-size: 13px;")
        tagline_row.addWidget(dot_right)

        layout.addLayout(tagline_row)
        layout.addSpacing(22)

        # Short description with chat-bubble icon 
        desc_row = QHBoxLayout()
        desc_row.setAlignment(Qt.AlignCenter)
        desc_row.setSpacing(14)

        bubble_holder = QLabel()
        bubble_holder.setFixedSize(42, 42)
        bubble_holder.setAlignment(Qt.AlignCenter)
        bubble_holder.setStyleSheet("""background-color: rgba(168, 85, 247, 32); border-radius: 21px; """)
        bubble_icon = QLabel(bubble_holder)
        bubble_icon.setPixmap(make_icon_pixmap("chat_bubble", "#e9d5ff", 19))
        bubble_icon.setFixedSize(19, 19)
        bubble_icon.move(11, 11)
        desc_row.addWidget(bubble_holder)

        desc_text = QLabel("Detect sign language in real-time using your camera\n" "or translate a video and get instant subtitles.")
        desc_text.setStyleSheet("color: #d1d5db; font-size: 14px; background: transparent;")
        desc_row.addWidget(desc_text)

        layout.addLayout(desc_row)
