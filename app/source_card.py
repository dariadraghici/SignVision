from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QColor

from app.icons import make_icon_pixmap, hex_to_rgb


class SourceCard(QFrame):

    def __init__(
        self,
        icon_name: str,
        accent_start: str,
        accent_end: str,
        title: str,
        description: str,
        button_text: str,
        button_icon: str,
        on_click,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("sourceCard")
        self.setMinimumSize(320, 300)

        accent_rgb = hex_to_rgb(accent_start)
        self.setStyleSheet(f"""
            QFrame#sourceCard {{
                background-color: rgba(255, 255, 255, 5);
                border: 1.5px solid rgba({accent_rgb}, 70);
                border-radius: 18px;
            }}
            QLabel#cardTitle {{
                color: #e8e4dc;
                font-size: 20px;
                font-weight: 700;
                background: transparent;
                border: none;
            }}
            QLabel#cardDescription {{
                color: #b8b3a8;
                font-size: 13px;
                background: transparent;
                border: none;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 32, 28, 28)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignHCenter)

        icon_circle = QLabel()
        icon_circle.setFixedSize(64, 64)
        icon_circle.setAlignment(Qt.AlignCenter)
        icon_circle.setStyleSheet(f"""
            background-color: rgba({accent_rgb}, 30);
            border: 1px solid rgba({accent_rgb}, 50);
            border-radius: 32px;
        """)
        icon_pixmap = make_icon_pixmap(icon_name, "#e8e4dc", 30)
        icon_label = QLabel(icon_circle)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedSize(30, 30)
        icon_label.move(17, 17)
        layout.addWidget(icon_circle, alignment=Qt.AlignHCenter)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setObjectName("cardDescription")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addStretch()

        button = QPushButton()
        button.setFixedHeight(46)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {accent_start}, stop:1 {accent_end}
                );
                color: #e8e4dc;
                font-size: 14px;
                font-weight: 600;
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 23px;
                padding: 0 22px;
            }}
            QPushButton:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {accent_end}, stop:1 {accent_start}
                );
            }}
        """)
        button.setIcon(_as_icon(make_icon_pixmap(button_icon, "#e8e4dc", 16)))
        button.setText(f"  {button_text}")
        button.clicked.connect(on_click)
        layout.addWidget(button)


def _as_icon(pixmap):
    from PySide6.QtGui import QIcon
    return QIcon(pixmap)
