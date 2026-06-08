"""Hermes gateway startup hook for Telegram command i18n.

Installed at: $HERMES_HOME/hooks/telegram-command-i18n/handler.py
Delegates to: $HERMES_HOME/command_i18n/apply_command_i18n.py
"""
from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser().resolve()


def _load_apply_module(home: Path):
    path = home / "command_i18n" / "apply_command_i18n.py"
    spec = importlib.util.spec_from_file_location("hermes_command_i18n_apply", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load apply module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def handle(event_type: str, context: dict) -> None:
    if event_type != "gateway:startup":
        return
    home = _home()
    try:
        module = _load_apply_module(home)
        lang = module.read_language(home)
        logger.info("[telegram-command-i18n] applying Telegram commands lang=%s", lang)
        # apply_language is synchronous urllib; run off the event loop.
        await asyncio.to_thread(module.apply_language, home, lang, True)
        logger.info("[telegram-command-i18n] applied Telegram command descriptions")
    except Exception as exc:
        logger.warning("[telegram-command-i18n] failed: %s", exc, exc_info=True)
