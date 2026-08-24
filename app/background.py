import math
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QColor, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class BackgroundWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()

        painter.fillRect(rect, QColor("#121414"))

        painter.end()

    def _draw_organic_leaf_left(self, painter, rect):
        painter.save()
        pen = QPen(QColor(138, 176, 144, 20))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.setBrush(QColor(138, 176, 144, 8))

        w, h = rect.width(), rect.height()

        leaf1 = QPainterPath()
        leaf1.moveTo(0, h * 0.05)
        leaf1.cubicTo(w * 0.15, h * 0.08, w * 0.22, h * 0.2, w * 0.25, h * 0.3)
        leaf1.cubicTo(w * 0.15, h * 0.35, w * 0.05, h * 0.38, 0, h * 0.4)
        painter.drawPath(leaf1)

        leaf2 = QPainterPath()
        leaf2.moveTo(0, h * 0.55)
        leaf2.cubicTo(w * 0.12, h * 0.6, w * 0.18, h * 0.75, w * 0.2, h * 0.85)
        leaf2.cubicTo(w * 0.12, h * 0.88, w * 0.04, h * 0.9, 0, h * 0.95)
        painter.drawPath(leaf2)

        painter.restore()

    def _draw_organic_leaf_right(self, painter, rect):
        painter.save()
        pen = QPen(QColor(200, 157, 124, 15))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.setBrush(QColor(200, 157, 124, 6))

        w, h = rect.width(), rect.height()

        leaf1 = QPainterPath()
        leaf1.moveTo(w, h * 0.15)
        leaf1.cubicTo(w * 0.88, h * 0.18, w * 0.82, h * 0.3, w * 0.78, h * 0.4)
        leaf1.cubicTo(w * 0.85, h * 0.45, w * 0.92, h * 0.48, w, h * 0.5)
        painter.drawPath(leaf1)

        leaf2 = QPainterPath()
        leaf2.moveTo(w, h * 0.65)
        leaf2.cubicTo(w * 0.9, h * 0.68, w * 0.85, h * 0.8, w * 0.82, h * 0.9)
        leaf2.cubicTo(w * 0.88, h * 0.92, w * 0.95, h * 0.95, w, h * 0.98)
        painter.drawPath(leaf2)

        painter.restore()

    def _draw_subtle_organic_lines(self, painter, rect):
        painter.save()
        w, h = rect.width(), rect.height()
        pen = QPen(QColor(255, 255, 255, 5))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        for i in range(2):
            path = QPainterPath()
            y_offset = h * (0.3 + i * 0.4)
            path.moveTo(0, y_offset)
            path.cubicTo(w * 0.3, y_offset - 60, w * 0.7, y_offset + 60, w, y_offset - 20)
            painter.drawPath(path)

        painter.restore()
