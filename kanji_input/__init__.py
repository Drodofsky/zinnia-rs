import os
import re
import platform
import importlib.util
import sys
from pathlib import Path
from typing import Optional
from aqt import gui_hooks
from anki.cards import Card

from aqt import mw
from aqt.utils import showCritical
from aqt.qt import QVBoxLayout

from .widget import KanjiReviewerWidget

def _select_native_lib() -> Optional[Path]:
    system = platform.system()
    machine = platform.machine().lower()
    addon_dir = Path(os.path.dirname(os.path.normpath(__file__)))

    if system == "Windows":
        filename = "zinnia_py.windows-x86_64.pyd"
    elif system == "Linux":
        filename = "zinnia_py.linux-x86_64.so"
    elif system == "Darwin":
        if "arm" in machine or "aarch64" in machine:
            filename = "zinnia_py.macos-arm64.so"
        else:
            filename = "zinnia_py.macos-x86_64.so"
    else:
        return None

    return addon_dir / "lib" / filename


def _load_native_module():
    lib_path = _select_native_lib()

    if lib_path is None or not lib_path.exists():
        showCritical(
            "Kanji Input Add-on Error\n\n"
            f"Native library not found: {lib_path}\n\n"
            "This is likely an unsupported platform."
        )
        return None

    module_name = f"{__name__}.zinnia_py"
    spec = importlib.util.spec_from_file_location(module_name, lib_path)
    if spec is None or spec.loader is None:
        showCritical(f"Kanji Input: Failed to load import spec for {lib_path}")
        return None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _model_path() -> Path:
    return Path(os.path.dirname(os.path.normpath(__file__))) / "model" / "handwriting-ja.model"


def _test_recognizer(zinnia_py) -> None:
    """smoke test — recognizes 一 from a single horizontal stroke"""
    model = _model_path()
    if not model.exists():
        showCritical(f"Kanji Input: model not found at {model}")
        return

    try:
        r = zinnia_py.Recognizer()
        r.open(str(model))

        ch = zinnia_py.Character()
        ch.set_width(300)
        ch.set_height(300)
        ch.add(0, 50, 150)
        ch.add(0, 120, 150)
        ch.add(0, 190, 150)
        ch.add(0, 260, 150)

        result = r.classify(ch, 5)
        print(f"[kanji-input] smoke test passed — top result: {result[0][0]}")

    except Exception as e:
        showCritical(f"Kanji Input: recognizer test failed\n\n{e}")

def _get_expected_answer(card: Card) -> str:
    """Extract the expected answer from the card's type:answer field."""
    if mw is None:
        return ""
    
    qfmt = card.template().get("qfmt", "")
    if not isinstance(qfmt, str):
        return ""

    # find {{type:FieldName}} in the template
    match = re.search(r"\{\{type:(.+?)\}\}", qfmt)
    if match is None:
        return ""

    field_name = match.group(1)
    note = card.note()
    
    # find the field value
    for name, value in note.items():
        if name == field_name:
            # strip HTML tags if any
            clean = re.sub(r"<[^>]+>", "", value)
            return clean.strip()

    return ""



_zinnia = _load_native_module()

if _zinnia is not None:
    _test_recognizer(_zinnia)




_reviewer_widget: KanjiReviewerWidget | None = None

def _on_question_shown(card: Card) -> None:
    global _reviewer_widget
    if mw is None or mw.reviewer is None:
        return

    qfmt = card.template().get("qfmt", "")
    if not isinstance(qfmt, str) or "type:" not in qfmt:
        return

    mw.reviewer.web.eval(
        "var t = document.getElementById('typeans');"
        "if (t) t.style.display = 'none';"
    )

    expected = _get_expected_answer(card)

    if _reviewer_widget is None:
        _reviewer_widget = KanjiReviewerWidget(canvas_size=300)
        _reviewer_widget.set_zinnia(
            _zinnia,
            str(_model_path())
        )
        web_parent = mw.reviewer.web.parentWidget()
        if web_parent is None:
            return
        layout = web_parent.layout()
        if isinstance(layout, QVBoxLayout):
            web_index = layout.indexOf(mw.reviewer.web)
            layout.insertWidget(web_index + 1, _reviewer_widget)

    _reviewer_widget.set_expected_answer(expected)
    _reviewer_widget.reset()

def _on_js_message(handled: tuple[bool, object], message: str, context: object) -> tuple[bool, object]:
    global _reviewer_widget
    if message == "ans" and _reviewer_widget is not None and _reviewer_widget.isVisible():
        _reviewer_widget.auto_submit()
        _reviewer_widget.hide()
    return handled
gui_hooks.reviewer_did_show_question.append(_on_question_shown)
gui_hooks.webview_did_receive_js_message.append(_on_js_message)