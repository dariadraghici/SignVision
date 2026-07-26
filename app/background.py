import math
import random

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class BackgroundWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        random.seed(7)
        self._dots = [
            (random.random(), random.random(), random.uniform(1.0, 2.4))
            for _ in range(80)
        ]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        painter.fillRect(rect, QColor("#0c0d1f"))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 16))
        for fx, fy, r in self._dots:
            painter.drawEllipse(QPointF(fx * rect.width(), fy * rect.height()), r, r)

        glow = QRadialGradient(rect.width() / 2, 150, 260)
        glow.setColorAt(0.0, QColor(168, 85, 247, 55))
        glow.setColorAt(0.55, QColor(99, 102, 241, 22))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(glow)
        painter.drawEllipse(QPointF(rect.width() / 2, 150), 300, 300)

        width = min(rect.width(), 460)

        painter.setBrush(Qt.NoBrush)
        for path, alpha in self._wave_paths(rect.height() - 6, width):
            pen = QPen(QColor(59, 130, 246, alpha))
            pen.setWidthF(1.4)
            painter.setPen(pen)
            painter.drawPath(path)

        painter.save()
        painter.translate(rect.width(), 70)
        painter.scale(-1, -1)
        for path, alpha in self._wave_paths(6, width):
            pen = QPen(QColor(168, 85, 247, alpha))
            pen.setWidthF(1.4)
            painter.setPen(pen)
            painter.drawPath(path)
        painter.restore()

        self._draw_sparkles(painter, rect)

        painter.end()

    @staticmethod
    def _wave_paths(base_y, width):
        paths = []
        steps = 40
        for i in range(4):
            path = QPainterPath()
            amplitude = 16 + i * 6
            y0 = base_y - i * 16
            path.moveTo(0, y0)
            for step in range(steps + 1):
                x = width * step / steps
                y = y0 - amplitude * math.sin(step / steps * math.pi * 1.4)
                path.lineTo(x, y)
            paths.append((path, max(6, 46 - i * 9)))
        return paths

    def _draw_sparkles(self, painter, rect):
        painter.setPen(Qt.NoPen)
        rng = random.Random(42)
        for _ in range(9):
            x = rng.random() * rect.width()
            y = rng.random() * rect.height() * 0.6
            size = rng.uniform(3, 6)
            painter.setBrush(QColor(199, 179, 255, 90))

            path = QPainterPath()
            path.moveTo(x, y - size)
            path.lineTo(x + size * 0.3, y - size * 0.3)
            path.lineTo(x + size, y)
            path.lineTo(x + size * 0.3, y + size * 0.3)
            path.lineTo(x, y + size)
            path.lineTo(x - size * 0.3, y + size * 0.3)
            path.lineTo(x - size, y)
            path.lineTo(x - size * 0.3, y - size * 0.3)
            path.closeSubpath()
            painter.drawPath(path)
