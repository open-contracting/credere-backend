import logging


def test_log_level(monkeypatch, capsys):
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    from app.core.settings import app_settings  # noqa: F401

    logger = logging.getLogger(__name__)
    logger.info("a")
    logger.warning("b")
    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err[23:] == " WARNING [tests.test_settings:11] b\n"
