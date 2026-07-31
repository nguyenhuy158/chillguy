"""Importing chillguy.main (and thus the CLI) must not eagerly import
textual/chillguy.tui — the TUI is an optional extra loaded on demand."""

import sys


def test_tui_import_is_lazy(monkeypatch):
    # Temporarily hide chillguy.tui from the module cache (restored by
    # monkeypatch after the test — a bare `del sys.modules[...]` here would
    # leak: a later `mock.patch("chillguy.tui...")` would then re-import a
    # *second*, distinct chillguy.tui module object to patch, while classes/
    # functions already loaded from the original module keep referencing the
    # original's globals, silently breaking the mock for other tests).
    monkeypatch.delitem(sys.modules, "chillguy.tui", raising=False)

    import chillguy.main  # noqa: F401

    assert "chillguy.tui" not in sys.modules


def test_launch_tui_missing_textual_gives_friendly_error(monkeypatch):
    import chillguy.main as main
    import typer

    # Simulate the optional dependency being absent: forcing chillguy.tui's
    # entry in sys.modules to None makes any import of it raise ImportError,
    # without actually touching import machinery or the real textual app.
    monkeypatch.setitem(sys.modules, "chillguy.tui", None)

    try:
        main._launch_tui()
    except typer.Exit as exc:
        assert exc.exit_code == 1
    else:
        raise AssertionError("expected typer.Exit to be raised")
