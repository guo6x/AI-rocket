"""QPainter-only, read-only 2D attitude fallback for unavailable OpenGL.

Displays *reported* synthetic/live roll and pitch without asserting hardware
orientation, yaw, CAD geometry, attitude control or sensor-source authenticity.
No pyqtgraph, GL context, I/O, UDP or commands are imported.
"""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget


class AttitudeFallbackWidget(QWidget):
    """Two independent schematic instruments; NOT a 3D view or CAD model."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.roll_deg = 0.0
        self.pitch_deg = 0.0
        self.setMinimumHeight(200)
        self.setAccessibleName("Read-only 2D roll and pitch attitude fallback")
        self.setToolTip("2D software display only; axes/mounting and sensor provenance unverified")

    def update_attitude(self, roll, pitch, yaw=0.0):
        del yaw  # Production 'yaw' is gz angular rate, NOT heading.
        values = (roll, pitch)
        if any(type(v) not in (int, float) for v in values):
            raise ValueError("2D fallback requires finite numeric roll/pitch")
        try:
            finite = all(math.isfinite(v) for v in values)
        except (TypeError, ValueError, OverflowError):
            finite = False
        if not finite:
            raise ValueError("2D fallback rejects non-finite/overflow attitude")
        self.roll_deg, self.pitch_deg = float(roll), float(pitch)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#18232c"))
        w = self.width()
        h = self.height()
        p.setFont(QFont("Sans Serif", 10))
        pane_w = w / 2.0
        radius = max(12.0, min(pane_w * 0.25, h * 0.27))
        y = h * 0.49
        for center_x, angle, title, accent in (
            (pane_w / 2, self.pitch_deg, "SIDE: PITCH", "#5fd8ff"),
            (pane_w * 1.5, self.roll_deg, "FRONT: ROLL", "#e7b86a"),
        ):
            p.save()
            pen = QPen(QColor("#536575"), 1.5)
            p.setPen(pen)
            p.drawLine(QPointF(center_x - radius * 1.25, y), QPointF(center_x + radius * 1.25, y))
            p.drawLine(QPointF(center_x, y - radius * 1.25), QPointF(center_x, y + radius * 1.25))
            p.translate(center_x, y)
            # Schematic, not a measured mount/coordinate transform.
            p.rotate(angle)
            p.setPen(QPen(QColor(accent), 2))
            p.setBrush(QBrush(QColor(accent)))
            if title.startswith("SIDE"):
                p.drawRoundedRect(QRectF(-radius * .13, -radius, radius * .26, radius * 2), 3, 3)
                p.drawLine(QPointF(-radius * .6, radius * .6), QPointF(radius * .6, radius * .6))
            else:
                points = QPolygonF([
                    QPointF(0, -radius),
                    QPointF(radius * .72, radius * .6),
                    QPointF(0, radius * .28),
                    QPointF(-radius * .72, radius * .6),
                ])
                p.drawPolygon(points)
            p.restore()
            p.setPen(QColor("#e7edf2"))
            p.drawText(QRectF(center_x - pane_w / 2 + 3, 6, pane_w - 6, 30),
                       Qt.AlignmentFlag.AlignCenter, title)
            p.drawText(QRectF(center_x - pane_w / 2 + 3, h - 44, pane_w - 6, 24),
                       Qt.AlignmentFlag.AlignCenter, f"{angle:+.1f} deg")
        p.setPen(QColor("#ffbe5c"))
        p.setFont(QFont("Sans Serif", 8))
        p.drawText(QRectF(4, h - 20, w - 8, 18),
                   Qt.AlignmentFlag.AlignCenter,
                   "2D FALLBACK | reported attitude only | yaw unavailable | NOT CAD")
        p.end()
