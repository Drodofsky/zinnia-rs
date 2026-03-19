from typing import Optional
from aqt.qt import QPalette
from typing import Optional
from aqt.qt import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame,
    Qt, QFont, pyqtSignal,
    QPainter, QPen, QPointF, QImage, QRect, QEvent,
    QPaintEvent, QSize, QPalette,QColor,QTabletEvent,QMouseEvent
)


from aqt.qt import QWidget, qtmajor, QFontDatabase, QRect
from aqt import mw
import json
class KanjiInputWidget(QWidget):

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        size: int = 300,
        show_grid: bool = True,
        pen_width: float = 8.0,
    ) -> None:
        super().__init__(parent)
        palette = self.palette()

        self._canvas_size = size
        self._show_grid = show_grid
        self._bg_color = palette.color(QPalette.ColorRole.Base)
        self._ink_color = palette.color(QPalette.ColorRole.Text)
        self._pen_width = pen_width

        # strokes: list of strokes, each stroke is a list of QPointF
        self._strokes: list[list[QPointF]] = []
        self._current_stroke: list[QPointF] = []
        self._drawing = False

        self._hint_char = ""
        self._hint_offset: tuple[int, int] | None = None 

        self.setFixedSize(QSize(size, size))
        # accept tablet events
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)

    # --- public API ---
    def undo_stroke(self) -> None:
        if self._strokes:
            self._strokes.pop()
            self.update()

    def clear(self) -> None:
        """Clear all strokes and repaint."""
        self._strokes.clear()
        self._current_stroke.clear()
        self._drawing = False
        self._hint_char = ""
        self._hint_offset = None
        self.update()

    def stroke_count(self) -> int:
        return len(self._strokes)

    def strokes(self) -> list[list[QPointF]]:
        """Return a copy of all completed strokes."""
        return [list(s) for s in self._strokes]

    # --- painting ---

    def paintEvent(self, a0: QPaintEvent| None) -> None:
        if a0 is None:
            return None
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # background
        painter.fillRect(self.rect(), self._bg_color)

        # grid guide
        if self._show_grid:
            self._draw_grid(painter)
        
        if self._hint_char:
            self._draw_hint(painter)

        # completed strokes
        pen = QPen(self._ink_color, self._pen_width,
                   Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap,
                   Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        for stroke in self._strokes:
            self._draw_stroke(painter, stroke)

        # stroke currently being drawn
        if self._current_stroke:
            self._draw_stroke(painter, self._current_stroke)
    

    def set_hint(self, character: str) -> None:
        self._hint_char = character
        self._hint_offset = None  # invalidate cache
        self.update()

    def clear_hint(self) -> None:
        self._hint_char = ""
        self._hint_offset = None
        self.update()

    def _compute_hint_offset(self, font: QFont) -> tuple[int, int]:
        """Compute centering offset once and cache it."""

        size = self._canvas_size
        buf = size * 2
        img = QImage(buf, buf, QImage.Format.Format_ARGB32)
        img.fill(0)
        tmp = QPainter(img)
        tmp.setFont(font)
        tmp.setPen(QPen(QColor(255, 255, 255, 255)))
        tmp.drawText(QRect(0, 0, buf, buf),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                    self._hint_char)
        tmp.end()

        top, bottom, left, right = buf, 0, buf, 0
        found = False
        for y in range(buf):
            for x in range(buf):
                if (img.pixel(x, y) >> 24) & 0xFF > 10:
                    top = min(top, y)
                    bottom = max(bottom, y)
                    left = min(left, x)
                    right = max(right, x)
                    found = True

        if not found:
            return (0, 0)

        glyph_w = right - left + 1
        glyph_h = bottom - top + 1
        dest_x = (size - glyph_w) // 2 - left
        dest_y = (size - glyph_h) // 2 - top
        return (dest_x, dest_y)

    def _draw_hint(self, painter: QPainter) -> None:

        hint_color = QColor(self._ink_color)
        hint_color.setAlpha(30)

        font = QFont()
        available = QFontDatabase.families()
        if "Klee One" in available:
            font.setFamily("Klee One")
        font.setPixelSize(int(self._canvas_size * 0.85))

        # compute offset once, reuse on every paintEvent
        if self._hint_offset is None:
            self._hint_offset = self._compute_hint_offset(font)

        dest_x, dest_y = self._hint_offset
        size = self._canvas_size
        buf = size * 2

        painter.setFont(font)
        painter.setPen(QPen(hint_color))
        painter.drawText(
            QRect(dest_x, dest_y, buf, buf),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            self._hint_char,
        )



    def _draw_grid(self, painter: QPainter) -> None:
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        bg = self._bg_color
        text = self._ink_color
        grid_color = QColor(
        (bg.red() + text.red()) // 2,
        (bg.green() + text.green()) // 2,
        (bg.blue() + text.blue()) // 2,
        120,  # semi-transparent so it's subtle but visible
        )

        pen = QPen(grid_color, 3, Qt.PenStyle.DashLine)
        painter.setPen(pen)

        # center cross
        painter.drawLine(cx, 0, cx, h)
        painter.drawLine(0, cy, w, cy)

    def _draw_stroke(self, painter: QPainter, stroke: list[QPointF]) -> None:
        if len(stroke) < 2:
            # single point — draw a dot
            if len(stroke) == 1:
                painter.drawPoint(stroke[0])
            return
        for i in range(len(stroke) - 1):
            painter.drawLine(stroke[i], stroke[i + 1])

    # --- tablet input (stylus) ---

    def tabletEvent(self, a0: QTabletEvent | None) -> None:
        if a0 is None:
            return
        if qtmajor > 5:
            pos = a0.position()
        else:
            pos = a0.posF()  # type: ignore[attr-defined]

        point = QPointF(pos.x(), pos.y())
        event_type = a0.type()

        if event_type == QEvent.Type.TabletPress:
            self._start_stroke(point)
        elif event_type == QEvent.Type.TabletMove:
            if self._drawing:
                self._add_point(point)
        elif event_type == QEvent.Type.TabletRelease:
            self._end_stroke()

        a0.accept()

    # --- mouse input (fallback) ---

    def mousePressEvent(self, a0: QMouseEvent| None) -> None:
        if a0 is None:
            return
        if a0.button() == Qt.MouseButton.LeftButton:
            self._start_stroke(QPointF(a0.position()))
        a0.accept()

    def mouseMoveEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is None:
            return
        if self._drawing:
            self._add_point(QPointF(a0.position()))
        a0.accept()

    def mouseReleaseEvent(self, a0: QMouseEvent| None) -> None:
        if a0 is None:
            return
        if a0.button() == Qt.MouseButton.LeftButton:
            self._end_stroke()
        a0.accept()

    # --- stroke management ---

    def _start_stroke(self, point: QPointF) -> None:
        self._drawing = True
        self._current_stroke = [point]
        self.update()

    def _add_point(self, point: QPointF) -> None:
        self._current_stroke.append(point)
        self.update()

    def _end_stroke(self) -> None:
        if self._current_stroke:
            self._strokes.append(self._current_stroke)
            self._current_stroke = []
        self._drawing = False
        self.update()

    

class StrokePreviewSlot(QWidget):
    clicked_signal = pyqtSignal(int)

    def __init__(self, index: int, size: int = 60, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._index = index
        self._strokes: list[list[QPointF]] = []
        self._source_size = 300
        self._slot_size = size
        self._selected = False
        self.setFixedSize(QSize(size, size))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def set_strokes(self, strokes: list[list[QPointF]], source_size: int) -> None:
        self._strokes = [list(s) for s in strokes]
        self._source_size = source_size
        self.update()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._update_style()
        self.update()

    def clear(self) -> None:
        self._strokes = []
        self._selected = False
        self._update_style()
        self.update()

    def has_strokes(self) -> bool:
        return len(self._strokes) > 0

    def _update_style(self) -> None:
        palette = self.palette()
        bg = palette.color(QPalette.ColorRole.Base).name()
        border = "#4a90d9" if self._selected else \
            palette.color(QPalette.ColorRole.Mid).name()
        self.setStyleSheet(
            f"background-color: {bg}; border: 2px solid {border}; "
            f"border-radius: 4px;"
        )

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        if a0 is None:
            return
        super().paintEvent(a0)
        if not self._strokes:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().color(QPalette.ColorRole.Text)
        pen = QPen(ink, 2, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap,
                   Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        padding = 4
        available = self._slot_size - padding * 2
        scale = available / self._source_size
        for stroke in self._strokes:
            if len(stroke) < 2:
                if stroke:
                    x = stroke[0].x() * scale + padding
                    y = stroke[0].y() * scale + padding
                    painter.drawPoint(QPointF(x, y))
                continue
            for i in range(len(stroke) - 1):
                x1 = stroke[i].x() * scale + padding
                y1 = stroke[i].y() * scale + padding
                x2 = stroke[i + 1].x() * scale + padding
                y2 = stroke[i + 1].y() * scale + padding
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def mousePressEvent(self, a0: object) -> None:
        if self._strokes:
            self.clicked_signal.emit(self._index)



class KanjiReviewerWidget(QWidget):
  

    NUM_SLOTS = 7

    def __init__(
        self,
        canvas_size: int = 300,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._canvas_size = canvas_size
        # confirmed characters
        self._input_buffer: list[str] = []
        # ink strokes for each confirmed character (for slot display)
        self._confirmed_strokes: list[list[list[QPointF]]] = []
        self._expected_answer: str = ""
        self._zinnia: object = None  # set from __init__.py
        self._model_path: str = ""  
        self._recognizer = None
        self._build_ui()
    def set_expected_answer(self, answer: str) -> None:
        self._expected_answer = answer

    def set_zinnia(self, zinnia: object, model_path: str) -> None:
        self._zinnia = zinnia
        self._model_path = model_path
        try:
            self._recognizer = zinnia.Recognizer()  # type: ignore[attr-defined]
            self._recognizer.open(model_path)  # type: ignore[attr-defined]
        except Exception as e: 
            print(f"[kanji-input] failed to load recognizer: {e}")
            self._recognizer = None

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(4)

        # --- 7 word character slots ---
        slot_row = QHBoxLayout()
        slot_row.setSpacing(4)
        self._slots: list[StrokePreviewSlot] = []
        for i in range(self.NUM_SLOTS):
            slot = StrokePreviewSlot(i, size=60)
            slot.clicked_signal.connect(self._on_slot_clicked)
            self._slots.append(slot)
            slot_row.addWidget(slot)
        slot_row.addStretch()
        outer.addLayout(slot_row)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        outer.addWidget(line)

        # --- drawing canvas ---
        canvas_row = QHBoxLayout()
        self._canvas = KanjiInputWidget(size=self._canvas_size, show_grid=True)
        canvas_row.addWidget(self._canvas)
        outer.addLayout(canvas_row)

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        outer.addWidget(line2)

        # --- bottom row ---
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

       

        bottom_row.addStretch()


        btn_undo = QPushButton("取消")  # undo last stroke
        btn_undo.setFixedSize(64, 52)
        btn_undo.setToolTip("最後のストロークを取り消す")
        btn_undo.clicked.connect(self._on_undo_stroke)
        bottom_row.addWidget(btn_undo)

        btn_clear = QPushButton("全消")  # clear canvas
        btn_clear.setFixedSize(64, 52)
        btn_clear.setToolTip("書き直す")
        btn_clear.clicked.connect(self._canvas.clear)
        bottom_row.addWidget(btn_clear)

        btn_next = QPushButton("次へ")  # confirm + next character
        btn_next.setFixedSize(64, 52)
        btn_next.setToolTip("この字を確定して次へ")
        btn_next.clicked.connect(self._on_next)
        bottom_row.addWidget(btn_next)

        btn_backspace = QPushButton("削除")  # delete last confirmed character
        btn_backspace.setFixedSize(64, 52)
        btn_backspace.setToolTip("最後の文字を削除")
        btn_backspace.clicked.connect(self._on_backspace)
        bottom_row.addWidget(btn_backspace)

        btn_hint = QPushButton("手本")  # model/example
        btn_hint.setFixedSize(64, 52)
        btn_hint.setToolTip("手本を表示")
        btn_hint.clicked.connect(self._on_hint)
        bottom_row.addWidget(btn_hint)

        bottom_row.addStretch()


        outer.addLayout(bottom_row)
    def _recognize_current(self) -> str | None:
        
        if self._zinnia is None:
            return None

        strokes = self._canvas.strokes()
        if not strokes:
            return None

        try:

            ch = self._zinnia.Character()  # type: ignore[attr-defined]
            ch.set_width(self._canvas_size)
            ch.set_height(self._canvas_size)

            for stroke_id, stroke in enumerate(strokes):
                for point in stroke:
                    ch.add(stroke_id, int(point.x()), int(point.y()))

            if self._recognizer is None:
                return None
            candidates = self._recognizer.classify(ch, 15)
            if not candidates:
                return None

            # pick candidate matching expected answer at current position
            idx = len(self._input_buffer)
            target: str | None = None
            if self._expected_answer and idx < len(self._expected_answer):
                target = self._expected_answer[idx]

            if target is not None:
                for kanji, _score in candidates:
                    if kanji == target:
                        return kanji

            # no match found — return top candidate
            return candidates[0][0]

        except Exception as e:
            print(f"[kanji-input] recognition error: {e}")
            return None
    def _on_undo_stroke(self) -> None:
        self._canvas.undo_stroke()
    def _on_hint(self) -> None:
        idx = len(self._input_buffer)
        if self._expected_answer and idx < len(self._expected_answer):
            self._canvas.set_hint(self._expected_answer[idx])
        else:
            self._canvas.clear_hint()
    def _on_next(self) -> None:
        strokes = self._canvas.strokes()
        self._canvas.clear_hint()
        if not strokes:
            return  # nothing drawn yet

        idx = len(self._input_buffer)
        if idx >= self.NUM_SLOTS:
            return

        # recognize silently
        kanji = self._recognize_current()
        if kanji is None:
            kanji = "？"  # fallback if recognition completely fails

        self._confirmed_strokes.append(strokes)
        self._input_buffer.append(kanji)
        self._slots[idx].set_strokes(strokes, self._canvas_size)
        self._slots[idx].set_selected(False)
        self._canvas.clear()





    def _on_slot_clicked(self, index: int) -> None:
        for i, slot in enumerate(self._slots):
            slot.set_selected(i == index)

    # --- button handlers ---

    def _on_backspace(self) -> None:
        """Remove the last confirmed character."""
        if not self._input_buffer:
            return
        self._input_buffer.pop()
        idx = len(self._input_buffer)
        self._slots[idx].clear()
        if self._confirmed_strokes:
            self._confirmed_strokes.pop()



    def auto_submit(self) -> None:
        if self._canvas.strokes():
            self._on_next()

        text = "".join(self._input_buffer)
        if not text:
            return
        if mw is None or mw.reviewer is None:
            return
        escaped = json.dumps(text)
        mw.reviewer.web.eval(
            f"document.getElementById('typeans').value = {escaped};"
        )
    # --- public API ---

    def reset(self) -> None:
        """Reset for a new card."""
        self._input_buffer.clear()
        self._confirmed_strokes.clear()
        for slot in self._slots:
            slot.clear()
        self._canvas.clear()
        self.show()