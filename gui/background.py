import math
import time

from PySide6.QtCore import QPointF, QTimer
from PySide6.QtGui import QBrush, QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget

# The animation position comes from one shared clock, so every page that
# derives from AnimatedBackground draws exactly the same frame. Switching
# pages therefore looks like one continuous background.
_START = time.monotonic()
_SPEED = 0.45          # radians per second


class AnimatedBackground(QWidget):
    """Base page: dark base with two slowly drifting colour glows."""

    def __init__(self):
        super().__init__()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)

    def showEvent(self, event):
        self._timer.start(40)
        super().showEvent(event)

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        phase = (time.monotonic() - _START) * _SPEED

        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#070B14"))

        w, h = self.width(), self.height()
        radius = max(w, h) * 0.75

        # (colour, phase offset): the two glows orbit on opposite sides
        glows = [
            (QColor(20, 120, 140, 150), 0.0),           # teal
            (QColor(160, 50, 75, 120), math.pi),        # rose
        ]
        for colour, offset in glows:
            cx = w * (0.5 + 0.38 * math.cos(phase + offset))
            cy = h * (0.5 + 0.38 * math.sin(phase * 0.8 + offset))
            gradient = QRadialGradient(QPointF(cx, cy), radius)
            gradient.setColorAt(0.0, colour)
            fade = QColor(colour)
            fade.setAlpha(0)
            gradient.setColorAt(1.0, fade)
            painter.fillRect(self.rect(), QBrush(gradient))