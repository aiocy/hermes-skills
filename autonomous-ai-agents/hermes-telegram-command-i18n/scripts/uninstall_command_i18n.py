#!/usr/bin/env python3
"""Uninstall Hermes Telegram command i18n package from a Hermes profile."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def hermes_home(value: str | None = None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser().resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Uninstall Telegram command i18n hook/runtime")
    parser.add_argument("--hermes-home", default=None)
    parser.add_argument("--restore-en", action="store_true", help="apply English command descriptions before removing runtime")
    parser.add_argument("--keep-language-file", action="store_true")
    args = parser.parse_args(argv)
    home = hermes_home(args.hermes_home)
    runtime = home / "command_i18n"
    hook = home / "hooks" / "telegram-command-i18n"

    if args.restore_en and (runtime / "apply_command_i18n.py").exists():
        subprocess.run([sys.executable, str(runtime / "apply_command_i18n.py"), "en", "--hermes-home", str(home)], check=False)

    if hook.exists():
        shutil.rmtree(hook)
        print(f"Removed hook: {hook}")
    if runtime.exists():
        shutil.rmtree(runtime)
        print(f"Removed runtime: {runtime}")
    lang_file = home / "cmd_language.json"
    if lang_file.exists() and not args.keep_language_file:
        lang_file.unlink()
        print(f"Removed language file: {lang_file}")
    print("If the gateway is running, restart it to stop loading the removed hook.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
