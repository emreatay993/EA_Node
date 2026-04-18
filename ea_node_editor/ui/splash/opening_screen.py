from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import (
    QEasingCurve,
    QElapsedTimer,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import QApplication, QWidget


SPLASH_W = 720
SPLASH_H = 440

# Mark geometry: design uses a 260-unit canvas; scale k = size/260.
MARK_SIZE = 188
BREATHE_MS = 2000

# Boot sequence mirrors the React design (splash/monolith_variants.jsx · M1).
BOOT_STEPS: tuple[str, ...] = (
    "Initialising runtime…",
    "Loading registry",
    "Scanning plug-ins",
    "Warming DPF",
    "Ready",
)
STEP_MS = 720


@dataclass(frozen=True)
class _Palette:
    bg_deep: QColor
    bg_card: QColor
    bg_node: QColor
    border: QColor
    border_soft: QColor
    fg: QColor
    fg_muted: QColor
    fg_dim: QColor
    blue: QColor
    cyan: QColor
    soft_blue: QColor


COREX = _Palette(
    bg_deep=QColor("#05080F"),
    bg_card=QColor("#0B0F1A"),
    bg_node=QColor("#1A2130"),
    border=QColor("#1F2A40"),
    border_soft=QColor("#182138"),
    fg=QColor("#E6EEFB"),
    fg_muted=QColor("#8895B2"),
    fg_dim=QColor("#4A566F"),
    blue=QColor("#2F6BFF"),
    cyan=QColor("#00D1FF"),
    soft_blue=QColor("#6FA8FF"),
)


class OpeningSplash(QWidget):
    """
    COREX opening screen · M1 Breathe.

    Frameless 720x440 card: radial glow, breathing COREX mark, wordmark,
    version string, and a 2px progress bar that advances through the
    boot sequence. Use `finish(next_widget)` to dismiss once the app is ready.
    """

    boot_completed = pyqtSignal()

    def __init__(
        self,
        *,
        version: str = "v0.9.3",
        mark_size: int = MARK_SIZE,
        breathe_ms: int = BREATHE_MS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFixedSize(QSize(SPLASH_W, SPLASH_H))

        self._version = str(version)
        self._mark_size = int(mark_size)
        self._breathe_ms = int(breathe_ms)

        # Breathing animation drives the core radius between 18k..22k.
        # We store a 0..1 phase; paintEvent maps it to an eased radius.
        self._breathe_phase = 0.0
        self._breathe_anim = QVariantAnimation(self)
        self._breathe_anim.setStartValue(0.0)
        self._breathe_anim.setEndValue(1.0)
        self._breathe_anim.setDuration(self._breathe_ms)
        self._breathe_anim.setLoopCount(-1)
        self._breathe_anim.setEasingCurve(QEasingCurve.Type.Linear)
        self._breathe_anim.valueChanged.connect(self._on_breathe)

        # Sheen slides across the progress fill on a 1.6s linear loop.
        self._sheen_phase = 0.0
        self._sheen_anim = QVariantAnimation(self)
        self._sheen_anim.setStartValue(0.0)
        self._sheen_anim.setEndValue(1.0)
        self._sheen_anim.setDuration(1600)
        self._sheen_anim.setLoopCount(-1)
        self._sheen_anim.setEasingCurve(QEasingCurve.Type.Linear)
        self._sheen_anim.valueChanged.connect(self._on_sheen)

        # Boot sequence driver.
        self._step_index = 0
        self._boot_timer = QTimer(self)
        self._boot_timer.setInterval(STEP_MS)
        self._boot_timer.timeout.connect(self._advance_step)

        # Tracks how long the splash has actually been visible, so we can
        # keep it on screen for a minimum duration even if the shell is
        # ready instantly (cold-start "flash" is jarring otherwise).
        self._shown_timer = QElapsedTimer()

    # ------------------------------------------------------------------ api

    def show_centered(self, screen=None) -> None:
        target = screen or QApplication.primaryScreen()
        if target is not None:
            geometry = target.availableGeometry()
            self.move(
                geometry.center().x() - SPLASH_W // 2,
                geometry.center().y() - SPLASH_H // 2,
            )
        self.show()
        self._shown_timer.start()
        self._breathe_anim.start()
        self._sheen_anim.start()
        self._boot_timer.start()

    def finish(self, next_widget: QWidget | None = None, *, min_visible_ms: int = 1200) -> None:
        """Close the splash and raise the main window, enforcing a minimum visible time."""
        elapsed = self._shown_timer.elapsed() if self._shown_timer.isValid() else 0
        remaining = max(0, min_visible_ms - int(elapsed))

        def _close() -> None:
            self._boot_timer.stop()
            self._breathe_anim.stop()
            self._sheen_anim.stop()
            if next_widget is not None:
                next_widget.show()
                next_widget.raise_()
                next_widget.activateWindow()
            self.close()

        if remaining == 0:
            _close()
        else:
            QTimer.singleShot(remaining, _close)

    # ------------------------------------------------------------ animation

    def _on_breathe(self, value: float) -> None:
        self._breathe_phase = float(value)
        self.update()

    def _on_sheen(self, value: float) -> None:
        self._sheen_phase = float(value)
        self.update()

    def _advance_step(self) -> None:
        if self._step_index < len(BOOT_STEPS) - 1:
            self._step_index += 1
            self.update()
            if self._step_index == len(BOOT_STEPS) - 1:
                self._boot_timer.stop()
                # Let "Ready" paint before any caller-triggered blocking work.
                QTimer.singleShot(0, self.boot_completed.emit)

    # --------------------------------------------------------------- paint

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        self._paint_frame(painter)
        self._paint_glow(painter)
        self._paint_mark(painter)
        self._paint_wordmark(painter)
        self._paint_progress(painter)

    # --- frame -------------------------------------------------------------

    def _paint_frame(self, p: QPainter) -> None:
        rect = QRectF(0.5, 0.5, SPLASH_W - 1, SPLASH_H - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(COREX.bg_card)
        p.drawPath(path)

        p.setClipPath(path)  # keep glow + traces inside the rounded card
        p.setPen(QPen(COREX.border, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 8, 8)

    # --- background glow ---------------------------------------------------

    def _paint_glow(self, p: QPainter) -> None:
        # Matches the React node: radial-gradient(ellipse 55% 55% at 50% 45%,
        #   rgba(47,107,255,0.16), transparent 60%)
        cx = SPLASH_W / 2
        cy = SPLASH_H * 0.45
        radius = SPLASH_W * 0.55 / 2

        grad = QRadialGradient(QPointF(cx, cy), radius)
        inner = QColor(COREX.blue)
        inner.setAlphaF(0.16)
        grad.setColorAt(0.0, inner)
        grad.setColorAt(0.6, QColor(0, 0, 0, 0))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRect(0, 0, SPLASH_W, SPLASH_H)

    # --- mark --------------------------------------------------------------

    def _paint_mark(self, p: QPainter) -> None:
        """
        Renders the COREX mark (mirrors the React `Mark` component in
        splash/v1_variations.jsx). All geometry is scaled against a 260-unit
        canvas, identical to the design source, so the proportions match
        pixel-for-pixel at any `size`.
        """
        size = self._mark_size
        k = size / 260.0

        # The mark sits above center; wordmark + subtitle stack below it.
        # Vertical layout: [mark][28px gap][wordmark][8px gap][subtitle].
        wordmark_size = 36
        subtitle_size = 11
        gap_1 = 28
        gap_2 = 8
        block_h = size + gap_1 + wordmark_size + gap_2 + subtitle_size
        top = (SPLASH_H - block_h) / 2
        left = (SPLASH_W - size) / 2

        cx = left + size / 2
        cy = top + size / 2

        # Corner nodes (4), inner-X endpoints, core.
        corners = [
            (left + 56 * k, top + 56 * k),
            (left + 204 * k, top + 56 * k),
            (left + 56 * k, top + 204 * k),
            (left + 204 * k, top + 204 * k),
        ]

        # Halo discs behind the core.
        halo_big = QColor(COREX.soft_blue)
        halo_big.setAlphaF(0.10)
        halo_small = QColor(COREX.soft_blue)
        halo_small.setAlphaF(0.22)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(halo_big)
        p.drawEllipse(QPointF(cx, cy), 36 * k, 36 * k)
        p.setBrush(halo_small)
        p.drawEllipse(QPointF(cx, cy), 26 * k, 26 * k)

        # Diagonal connection lines (gradient blue → cyan, round caps).
        for ox, oy in corners:
            grad = QLinearGradient(QPointF(ox, oy), QPointF(cx, cy))
            grad.setColorAt(0.0, COREX.blue)
            grad.setColorAt(1.0, COREX.cyan)
            pen = QPen(QBrush(grad), 7 * k)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(QPointF(ox, oy), QPointF(cx, cy))

        # Inner "X" crossing through the core.
        soft = QColor(COREX.soft_blue)
        soft.setAlphaF(0.92)
        pen = QPen(soft, 3 * k)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(left + 92 * k, top + 92 * k), QPointF(left + 168 * k, top + 168 * k))
        p.drawLine(QPointF(left + 168 * k, top + 92 * k), QPointF(left + 92 * k, top + 168 * k))

        # Corner rings — filled node body over outer blue stroke.
        for ox, oy in corners:
            p.setBrush(COREX.bg_node)
            p.setPen(QPen(COREX.blue, 4 * k))
            p.drawEllipse(QPointF(ox, oy), 12 * k, 12 * k)

        # Breathing core — r cycles 18k..22k on a sin wave.
        import math

        breathe_t = 0.5 - 0.5 * math.cos(self._breathe_phase * 2 * math.pi)
        core_r = (18 + 4 * breathe_t) * k

        core_grad = QRadialGradient(QPointF(cx, cy), core_r)
        core_grad.setColorAt(0.0, COREX.cyan)
        core_grad.setColorAt(1.0, COREX.blue)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(core_grad))
        p.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # Faint outer ring.
        faint = QColor(COREX.soft_blue)
        faint.setAlphaF(0.35)
        pen = QPen(faint, 2.7 * k)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), 28 * k, 28 * k)

        # Stash layout for the wordmark block.
        self._wordmark_top = top + size + gap_1
        self._wordmark_size = wordmark_size
        self._subtitle_top = self._wordmark_top + wordmark_size + gap_2
        self._subtitle_size = subtitle_size

    # --- wordmark ----------------------------------------------------------

    def _paint_wordmark(self, p: QPainter) -> None:
        wordmark_size = self._wordmark_size

        base_font = QFont("Segoe UI Variable", -1, QFont.Weight.DemiBold)
        base_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        base_font.setPixelSize(wordmark_size)
        # Design sets letterSpacing: size * 0.08 → ~2.88px at 36px.
        base_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, wordmark_size * 0.08)

        metrics = QFontMetricsF(base_font)
        core_text = "CORE"
        x_text = "X"
        core_w = metrics.horizontalAdvance(core_text)
        x_w = metrics.horizontalAdvance(x_text)
        total_w = core_w + x_w

        # The font's letter-spacing pads trailing advance equally for CORE
        # and X; to keep "COREX" feeling continuous we let them touch.
        baseline = self._wordmark_top + metrics.ascent()
        left = (SPLASH_W - total_w) / 2

        p.setFont(base_font)
        p.setPen(COREX.fg)
        p.drawText(QPointF(left, baseline), core_text)

        x_left = left + core_w
        x_rect = QRectF(x_left, self._wordmark_top, x_w, metrics.height())
        grad = QLinearGradient(x_rect.topLeft(), x_rect.bottomRight())
        grad.setColorAt(0.0, COREX.blue)
        grad.setColorAt(1.0, COREX.cyan)
        p.setPen(QPen(QBrush(grad), 1))
        p.drawText(QPointF(x_left, baseline), x_text)

        # Subtitle: "Node Editor · v<version>" — uppercase, tracked.
        subtitle_font = QFont("Segoe UI", -1, QFont.Weight.Medium)
        subtitle_font.setPixelSize(self._subtitle_size)
        subtitle_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        subtitle_font.setCapitalization(QFont.Capitalization.AllUppercase)
        p.setFont(subtitle_font)
        p.setPen(COREX.fg_dim)
        sub_metrics = QFontMetricsF(subtitle_font)
        subtitle = f"Node Editor · {self._version}"
        sub_w = sub_metrics.horizontalAdvance(subtitle)
        p.drawText(
            QPointF((SPLASH_W - sub_w) / 2, self._subtitle_top + sub_metrics.ascent()),
            subtitle,
        )

    # --- progress ----------------------------------------------------------

    def _paint_progress(self, p: QPainter) -> None:
        margin = 32
        bar_y = SPLASH_H - 22 - 2
        bar_w = SPLASH_W - margin * 2

        # Label row above the bar.
        label_font = QFont("Segoe UI", -1, QFont.Weight.Medium)
        label_font.setPixelSize(11)
        label_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)
        label_font.setCapitalization(QFont.Capitalization.AllUppercase)
        p.setFont(label_font)
        p.setPen(COREX.fg_muted)
        label_metrics = QFontMetricsF(label_font)
        label_baseline = bar_y - 8 - (label_metrics.descent() - label_metrics.leading())

        step_label = BOOT_STEPS[self._step_index]
        p.drawText(QPointF(margin, label_baseline - label_metrics.descent()), step_label)

        progress = (
            self._step_index / (len(BOOT_STEPS) - 1) if len(BOOT_STEPS) > 1 else 1.0
        )

        sub_font = QFont("Cascadia Mono", -1, QFont.Weight.Medium)
        sub_font.setPixelSize(11)
        p.setFont(sub_font)
        p.setPen(COREX.fg_dim)
        sub_metrics = QFontMetricsF(sub_font)
        sub_text = f"{int(round(progress * 100))}%"
        sub_w = sub_metrics.horizontalAdvance(sub_text)
        p.drawText(
            QPointF(SPLASH_W - margin - sub_w, label_baseline - sub_metrics.descent()),
            sub_text,
        )

        # Track background.
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(COREX.border_soft)
        p.drawRect(QRect(margin, bar_y, bar_w, 2))

        # Progress fill (blue→cyan gradient, cyan glow) — clipped to bar rect.
        fill_w = int(bar_w * progress)
        if fill_w > 0:
            fill_rect = QRectF(margin, bar_y, fill_w, 2)
            grad = QLinearGradient(fill_rect.topLeft(), fill_rect.topRight())
            grad.setColorAt(0.0, COREX.blue)
            grad.setColorAt(1.0, COREX.cyan)
            p.setBrush(QBrush(grad))
            p.drawRect(fill_rect)

            # Sheen: 80px-wide soft highlight sliding across the fill only.
            p.save()
            p.setClipRect(fill_rect)
            sheen_w = 80.0
            # Animate from -120% → +340% of fill width (matches React keyframe).
            travel = fill_w + sheen_w * 2
            sheen_x = margin - sheen_w + self._sheen_phase * travel
            sheen_rect = QRectF(sheen_x, bar_y, sheen_w, 2)
            sheen_grad = QLinearGradient(sheen_rect.topLeft(), sheen_rect.topRight())
            transparent = QColor(255, 255, 255, 0)
            highlight = QColor(255, 255, 255, 140)
            sheen_grad.setColorAt(0.0, transparent)
            sheen_grad.setColorAt(0.5, highlight)
            sheen_grad.setColorAt(1.0, transparent)
            p.setBrush(QBrush(sheen_grad))
            p.drawRect(sheen_rect)
            p.restore()


__all__ = ["OpeningSplash", "BOOT_STEPS"]
