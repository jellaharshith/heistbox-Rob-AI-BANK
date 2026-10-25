import pytest
from integrations import status as status_module


def test_z3_stub_success():
    msg = status_module._z3_check()
    assert "z3" in msg
    assert "UNSAT" in msg


def test_z3_stub_failure_fallback():
    import z3
    s = z3.Solver()
    x = z3.Int("x")
    s.add(x > 10, x < 5)
    assert s.check() == z3.unsat


def test_z3_live_smoke():
    msg = status_module._z3_check()
    assert "loaded" in msg
