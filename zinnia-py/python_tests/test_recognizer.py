# zinnia-py/python_tests/test_recognizer.py
import pytest
import zinnia_py

MODEL_PATH = "../model/handwriting-ja.model"


def make_ichi():
    ch = zinnia_py.Character()
    ch.set_width(300)
    ch.set_height(300)
    ch.add(0, 50, 150)
    ch.add(0, 120, 150)
    ch.add(0, 190, 150)
    ch.add(0, 260, 150)
    return ch


def make_juu():
    ch = zinnia_py.Character()
    ch.set_width(300)
    ch.set_height(300)
    ch.add(0, 90, 150)
    ch.add(0, 130, 150)
    ch.add(0, 170, 150)
    ch.add(0, 210, 150)
    ch.add(1, 150, 90)
    ch.add(1, 150, 130)
    ch.add(1, 150, 170)
    ch.add(1, 150, 210)
    return ch


@pytest.fixture(scope="session")
def recognizer():
    r = zinnia_py.Recognizer()
    r.open(MODEL_PATH)
    return r


def test_recognizer_can_be_created():
    zinnia_py.Recognizer()


def test_open_nonexistent_model_fails():
    r = zinnia_py.Recognizer()
    with pytest.raises(RuntimeError):
        r.open("/definitely/not/found.model")


def test_open_valid_model_works():
    r = zinnia_py.Recognizer()
    r.open(MODEL_PATH)


def test_character_can_be_created():
    zinnia_py.Character()


def test_classify_ichi_top_candidate(recognizer):
    result = recognizer.classify(make_ichi(), 10)
    assert result[0][0] == "一", f"got: {result}"


def test_classify_juu_top_candidate(recognizer):
    result = recognizer.classify(make_juu(), 10)
    assert result[0][0] == "十", f"got: {result}"


def test_ichi_in_candidates(recognizer):
    result = recognizer.classify(make_ichi(), 10)
    assert any(c[0] == "一" for c in result), f"got: {result}"


def test_juu_in_candidates(recognizer):
    result = recognizer.classify(make_juu(), 10)
    assert any(c[0] == "十" for c in result), f"got: {result}"