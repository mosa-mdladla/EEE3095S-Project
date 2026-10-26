import math

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

# Glow = the soft halo colour, core = the bright centre of the pen stroke
X_GLOW = QColor(34, 211, 238)
X_CORE = QColor("#67E8F9")
O_GLOW = QColor(255, 107, 90)
O_CORE = QColor("#FF8A7A")


def _partial_path(points, fraction):
    """Path through the first `fraction` (0..1) of a list of points."""
    path = QPainterPath()
    if fraction <= 0.0 or len(points) < 2:
        return path

    fraction = min(fraction, 1.0)
    exact = fraction * (len(points) - 1)
    whole = int(exact)

    path.moveTo(points[0])
    for point in points[1:whole + 1]:
        path.lineTo(point)

    if whole < len(points) - 1:
        a, b = points[whole], points[whole + 1]
        t = exact - whole
        path.lineTo(QPointF(a.x() + (b.x() - a.x()) * t,
                            a.y() + (b.y() - a.y()) * t))
    return path


def _bowed_stroke(start, end, bow, steps=28):
    """A slightly curved line from start to end (like a quick pen stroke)."""
    mid_x = (start.x() + end.x()) / 2
    mid_y = (start.y() + end.y()) / 2
    dx, dy = end.x() - start.x(), end.y() - start.y()
    length = math.hypot(dx, dy) or 1.0
    # push the middle sideways by `bow` pixels
    ctrl_x = mid_x + (-dy / length) * bow
    ctrl_y = mid_y + (dx / length) * bow

    points = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        points.append(QPointF(
            u * u * start.x() + 2 * u * t * ctrl_x + t * t * end.x(),
            u * u * start.y() + 2 * u * t * ctrl_y + t * t * end.y()))
    return points


def _clamp01(value):
    return max(0.0, min(1.0, value))


class Cell(QWidget):
    """One square. Draws its own X / O as if they were being written."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mark = "."
        self.progress = 1.0          # 0 = nothing drawn yet, 1 = finished
        self.hovered = False
        self.highlight = False       # part of the winning line
        self.dimmed = False          # not part of the winning line

        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.valueChanged.connect(self._on_progress)

        self.setMinimumSize(48, 48)

    # ---------------- state ----------------
    def set_mark(self, mark):
        """Set X, O or '.'. A newly placed mark is written out with an animation."""
        if mark == self.mark:
            return

        self._anim.stop()
        self.mark = mark

        if mark == ".":
            self.progress = 1.0
        else:
            self.progress = 0.0
            # quick and subtle: the mark just "wipes in" rather than being
            # obviously drawn
            self._anim.setDuration(220)
            self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            self._anim.start()

        self.update()

    def _on_progress(self, value):
        self.progress = float(value)
        self.update()

    # ---------------- mouse ----------------
    def enterEvent(self, event):
        self.hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if (self.isEnabled()
                and event.button() == Qt.MouseButton.LeftButton
                and self.rect().contains(event.position().toPoint())):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    # ---------------- stroke geometry ----------------
    def _x_strokes(self):
        """Two perfectly straight lines."""
        w, h = self.width(), self.height()
        s = min(w, h)
        cx, cy = w / 2, h / 2
        a = s * 0.225

        first = [QPointF(cx - a, cy - a), QPointF(cx + a, cy + a)]
        second = [QPointF(cx + a, cy - a), QPointF(cx - a, cy + a)]
        return first, second

    def _o_points(self):
        """A clean circle starting at the top."""
        w, h = self.width(), self.height()
        s = min(w, h)
        cx, cy = w / 2, h / 2
        radius = s * 0.235

        points = []
        steps = 72
        for i in range(steps + 1):
            angle = -math.pi / 2 + 2 * math.pi * i / steps
            points.append(QPointF(cx + radius * math.cos(angle),
                                  cy + radius * math.sin(angle)))
        return points

    # ---------------- painting ----------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        side = min(w, h)
        rect = QRectF(1, 1, w - 2, h - 2)
        radius = side * 0.17

        glow, core = (X_GLOW, X_CORE) if self.mark == "X" else (O_GLOW, O_CORE)

        fill = QColor(12, 18, 32, 205)
        border = QColor(255, 255, 255, 24)
        if self.highlight and self.mark != ".":
            fill = QColor(glow.red(), glow.green(), glow.blue(), 30)
            border = QColor(glow.red(), glow.green(), glow.blue(), 170)
        elif self.hovered and self.isEnabled():
            fill = QColor(18, 28, 46, 225)
            border = QColor(34, 211, 238, 150)

        painter.setPen(QPen(border, 1.2))
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, radius, radius)

        if self.mark == ".":
            return

        if self.dimmed:
            painter.setOpacity(0.35)

        # Each stroke gets a wide faint halo, a medium one, then the bright core
        if self.mark == "X":
            first, second = self._x_strokes()
            # first line, then the second, with no pause in between
            parts = [(first, _clamp01(self.progress / 0.5)),
                     (second, _clamp01((self.progress - 0.5) / 0.5))]
        else:
            parts = [(self._o_points(), self.progress)]

        pen_width = max(4.0, side * 0.07)
        layers = [(3.4, 22, glow), (2.1, 48, glow), (1.0, 255, core)]

        painter.setBrush(Qt.BrushStyle.NoBrush)
        for points, fraction in parts:
            path = _partial_path(points, fraction)
            if path.isEmpty():
                continue
            for width_scale, alpha, colour in layers:
                pen_colour = QColor(colour)
                pen_colour.setAlpha(alpha)
                pen = QPen(pen_colour, pen_width * width_scale)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                painter.drawPath(path)


class BoardWidget(QWidget):
    """3x3 grid of Cells that fills all the space it is given."""

    cell_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cells = []

        for index in range(9):
            cell = Cell(self)
            cell.clicked.connect(lambda i=index: self.cell_clicked.emit(i))
            self.cells.append(cell)

        self.setMinimumSize(240, 240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)

    def resizeEvent(self, event):
        # The cells fill the whole area they are given
        w, h = self.width(), self.height()
        gap = max(8, round(min(w, h) * 0.028))
        cell_w = (w - 2 * gap) // 3
        cell_h = (h - 2 * gap) // 3

        for index, cell in enumerate(self.cells):
            cell.setGeometry((index % 3) * (cell_w + gap),
                             (index // 3) * (cell_h + gap),
                             cell_w, cell_h)
        super().resizeEvent(event)


class PlayerCard(QWidget):
    """Badge + name + status line. Glows when it is this player's move."""

    def __init__(self, mark, parent=None):
        super().__init__(parent)
        self.mark = mark
        self.active = False

        self.badge = QLabel(mark)
        self.badge.setObjectName("badgeX" if mark == "X" else "badgeO")
        self.badge.setFixedSize(34, 34)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.name_label = QLabel("")
        self.name_label.setObjectName("cardName")
        self.name_label.setTextFormat(Qt.TextFormat.PlainText)

        self.sub_label = QLabel("")
        self.sub_label.setObjectName("cardSub")
        self.sub_label.setTextFormat(Qt.TextFormat.PlainText)

        text_column = QVBoxLayout()
        text_column.setSpacing(0)
        text_column.addWidget(self.name_label)
        text_column.addWidget(self.sub_label)

        row = QHBoxLayout(self)
        row.setContentsMargins(22, 16, 22, 16)
        row.setSpacing(12)
        row.addStretch(1)
        row.addWidget(self.badge)
        row.addLayout(text_column)
        row.addStretch(1)

        self.setMinimumHeight(72)

    def set_state(self, name, subtitle, active):
        self.name_label.setText(name)
        self.sub_label.setText(subtitle)
        self.active = active
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        glow = X_GLOW if self.mark == "X" else O_GLOW
        rect = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        radius = 18

        if self.active:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(1, 8):
                halo = QColor(glow)
                halo.setAlpha((8 - i) * 5)
                painter.setPen(QPen(halo, 1.6))
                painter.drawRoundedRect(rect.adjusted(-i, -i, i, i),
                                        radius + i, radius + i)

        if self.active:
            border = QColor(glow.red(), glow.green(), glow.blue(), 190)
            border_width = 1.5
        else:
            border = QColor(255, 255, 255, 28)
            border_width = 1.0

        painter.setPen(QPen(border, border_width))
        painter.setBrush(QColor(13, 19, 33, 215))
        painter.drawRoundedRect(rect, radius, radius)