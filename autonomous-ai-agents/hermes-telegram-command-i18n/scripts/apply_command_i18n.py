#!/usr/bin/env python3
"""Apply localized Telegram slash command descriptions for Hermes Agent.

Usage:
  python3 apply_command_i18n.py zh [--hermes-home ~/.hermes]
  python3 apply_command_i18n.py en [--hermes-home ~/.hermes]
  python3 apply_command_i18n.py status
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

SCOPES = [
    {"type": "default"},
    {"type": "all_private_chats"},
    {"type": "all_group_chats"},
]


def hermes_home(value: str | None = None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser().resolve()


def ensure_hermes_import_path() -> None:
    try:
        import hermes_cli.commands  # noqa: F401
        return
    except Exception:
        pass
    try:
        out = subprocess.check_output(["hermes", "--version"], text=True, stderr=subprocess.STDOUT, timeout=15)
    except Exception:
        return
    for line in out.splitlines():
        if line.startswith("Project:"):
            project = line.split(":", 1)[1].strip()
            if project and project not in sys.path:
                sys.path.insert(0, project)
            return


def read_env_token(home: Path) -> str:
    env_path = home / ".env"
    if not env_path.exists():
        raise RuntimeError(f"Missing .env: {env_path}")
    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "TELEGRAM_BOT_TOKEN":
            token = value.strip().strip("'\"")
            if token:
                return token
    raise RuntimeError(f"TELEGRAM_BOT_TOKEN not found in {env_path}")


def runtime_dir(home: Path) -> Path:
    return home / "command_i18n"


def read_language(home: Path) -> str:
    path = home / "cmd_language.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        lang = str(data.get("lang", "en")).lower().strip()
    except Exception:
        return "en"
    return "zh" if lang.startswith("zh") else "en"


def write_language(home: Path, lang: str) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "cmd_language.json").write_text(json.dumps({"lang": lang}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_translations(home: Path, lang: str) -> dict[str, str]:
    if lang == "en":
        return {}
    path = runtime_dir(home) / "translations" / f"{lang}.json"
    if not path.exists():
        raise RuntimeError(f"Missing translation file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"Translation file must be a JSON object: {path}")
    return {str(k): str(v) for k, v in data.items()}


def get_hermes_commands() -> list[tuple[str, str]]:
    ensure_hermes_import_path()
    try:
        from hermes_cli.commands import telegram_menu_commands
    except Exception as exc:
        raise RuntimeError("Cannot import hermes_cli.commands.telegram_menu_commands; run from a Hermes environment or ensure `hermes --version` works") from exc
    commands, _hidden = telegram_menu_commands(max_commands=30)
    return [(str(name), str(desc)) for name, desc in commands]


def build_bot_commands(home: Path, lang: str) -> list[dict[str, str]]:
    translations = load_translations(home, lang)
    commands = []
    for name, desc in get_hermes_commands():
        commands.append({"command": name, "description": translations.get(name, desc)})
    # Keep /lang visible in both languages so the user can switch back from English.
    commands.append({
        "command": "lang",
        "description": translations.get("lang", "Switch command description language (zh/en)"),
    })
    return commands


def telegram_api(token: str, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram API HTTP {exc.code}: {body}") from exc
    result = json.loads(body)
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API {method} failed: {result}")
    return result


def apply_language(home: Path, lang: str, verify: bool = True) -> dict[str, Any]:
    lang = "zh" if lang.lower().startswith("zh") else "en"
    token = read_env_token(home)
    commands = build_bot_commands(home, lang)
    results = []
    for scope in SCOPES:
        telegram_api(token, "setMyCommands", {"commands": commands, "scope": scope})
        results.append(scope["type"])
    write_language(home, lang)
    status = {"lang": lang, "commands_set": len(commands), "scopes": results}
    if verify:
        registered = telegram_api(token, "getMyCommands", None).get("result", [])
        status["registered_count_default"] = len(registered)
        status["has_lang_default"] = any(cmd.get("command") == "lang" for cmd in registered)
        status["sample_default"] = registered[:5]
    return status


def status(home: Path) -> dict[str, Any]:
    token = read_env_token(home)
    registered = telegram_api(token, "getMyCommands", None).get("result", [])
    return {
        "home": str(home),
        "configured_lang": read_language(home),
        "registered_count_default": len(registered),
        "has_lang_default": any(cmd.get("command") == "lang" for cmd in registered),
        "sample_default": registered[:8],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply Hermes Telegram command description language")
    parser.add_argument("command", choices=["zh", "en", "status"], help="language to apply or status")
    parser.add_argument("--hermes-home", default=None, help="Hermes home/profile directory; defaults to HERMES_HOME or ~/.hermes")
    parser.add_argument("--no-verify", action="store_true", help="skip getMyCommands verification after applying")
    args = parser.parse_args(argv)
    home = hermes_home(args.hermes_home)
    try:
        if args.command == "status":
            result = status(home)
        else:
            result = apply_language(home, args.command, verify=not args.no_verify)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
