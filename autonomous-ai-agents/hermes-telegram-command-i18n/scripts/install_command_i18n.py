#!/usr/bin/env python3
"""Install Hermes Telegram command i18n package into a Hermes profile."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def hermes_home(value: str | None = None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser().resolve()


def skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def has_token(home: Path) -> bool:
    env = home / ".env"
    if not env.exists():
        return False
    return any(line.strip().startswith("TELEGRAM_BOT_TOKEN=") for line in env.read_text(encoding="utf-8", errors="ignore").splitlines())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install Telegram command i18n hook/runtime into HERMES_HOME")
    parser.add_argument("--hermes-home", default=None, help="Hermes home/profile directory; defaults to HERMES_HOME or ~/.hermes")
    parser.add_argument("--lang", choices=["zh", "en"], default="zh", help="initial language")
    parser.add_argument("--apply", action="store_true", help="immediately call Telegram setMyCommands after install")
    parser.add_argument("--force", action="store_true", help="overwrite existing installed files")
    args = parser.parse_args(argv)

    home = hermes_home(args.hermes_home)
    src = skill_dir()
    runtime = home / "command_i18n"
    hook = home / "hooks" / "telegram-command-i18n"

    if runtime.exists() and not args.force:
        print(f"Runtime already exists: {runtime} (use --force to overwrite)", file=sys.stderr)
        return 2
    if hook.exists() and not args.force:
        print(f"Hook already exists: {hook} (use --force to overwrite)", file=sys.stderr)
        return 2

    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "translations").mkdir(parents=True, exist_ok=True)
    hook.mkdir(parents=True, exist_ok=True)

    copy_file(src / "scripts" / "apply_command_i18n.py", runtime / "apply_command_i18n.py")
    copy_file(src / "references" / "translations-zh.json", runtime / "translations" / "zh.json")
    copy_file(src / "templates" / "HOOK.yaml", hook / "HOOK.yaml")
    copy_file(src / "templates" / "handler.py", hook / "handler.py")
    (home / "cmd_language.json").write_text(json.dumps({"lang": args.lang}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Installed runtime: {runtime}")
    print(f"Installed hook:    {hook}")
    print(f"Language config:   {home / 'cmd_language.json'}")
    print(f"Token present:     {has_token(home)}")

    if args.apply:
        cmd = [sys.executable, str(runtime / "apply_command_i18n.py"), args.lang, "--hermes-home", str(home)]
        print("Applying:", " ".join(cmd))
        completed = subprocess.run(cmd, text=True)
        return completed.returncode

    print("Next: run `hermes gateway restart` so the startup hook is active, or pass --apply to register immediately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
