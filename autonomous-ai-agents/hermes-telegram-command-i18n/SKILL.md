---
name: hermes-telegram-command-i18n
description: Use when migrating or installing localized Telegram slash command descriptions for Hermes Agent. Provides a profile-safe skill package with installer, apply/status/uninstall scripts, startup hook templates, and Chinese command translations including a /lang toggle.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, telegram, i18n, l10n, slash-commands, gateway, hooks]
    related_skills: [hermes-agent, hermes-agent-skill-authoring]
---

# Hermes Telegram Command i18n

## Overview

This skill packages the Telegram slash-command description translation workaround as a reusable, migration-friendly component. It does **not** patch Hermes source code. It uses Hermes' official command registry and gateway startup hook mechanism, then calls Telegram's `setMyCommands` API to overwrite the command descriptions shown in the Telegram `/` menu.

The installed package supports:

- Chinese or English command descriptions.
- A persistent language file at `~/.hermes/cmd_language.json`.
- A `/lang` menu entry so the user can type `/lang zh` or `/lang en` conversationally.
- Direct re-apply without restarting the gateway.
- Automatic recovery after gateway startup via a hook.
- Profile-safe deployment through `--hermes-home` or `HERMES_HOME`.

## When to Use

Use this skill when:

- Migrating Hermes Telegram command translations to a new VPS or profile.
- Re-registering `/lang` after a gateway update or restart.
- The Telegram `/` menu descriptions are in English and the user wants Chinese.
- The user wants a portable way to install the command translation setup on another machine.

Do **not** use this for translating the agent's natural-language replies. Hermes' `agent/i18n.py` handles gateway response strings; this skill only handles Telegram slash command descriptions.

## Files in This Skill

```text
scripts/
  install_command_i18n.py    # install hook + runtime package into HERMES_HOME
  apply_command_i18n.py      # apply zh/en/status directly via Telegram Bot API
  uninstall_command_i18n.py  # remove hook/runtime package and restore English commands
templates/
  HOOK.yaml                  # gateway:startup hook manifest
  handler.py                 # startup hook; delegates to installed apply module
references/
  translations-zh.json       # Chinese command description translations
```

## Quick Install

From this skill directory:

```bash
python3 scripts/install_command_i18n.py --lang zh --apply
hermes gateway restart
```

For a non-default profile:

```bash
python3 scripts/install_command_i18n.py --hermes-home ~/.hermes/profiles/oracle --lang zh --apply
```

The installer copies files into:

```text
$HERMES_HOME/hooks/telegram-command-i18n/
$HERMES_HOME/command_i18n/
$HERMES_HOME/cmd_language.json
```

## Switching Language

No gateway restart is required for normal switching:

```bash
python3 scripts/apply_command_i18n.py zh
python3 scripts/apply_command_i18n.py en
python3 scripts/apply_command_i18n.py status
```

The scripts update Telegram's server-side command list directly. Telegram clients may cache the menu briefly, but `getMyCommands` verification happens immediately.

## How `/lang` Works

`/lang` is intentionally appended to Telegram's command menu but is not registered in Hermes' `COMMAND_REGISTRY`. When the user types `/lang zh` or `/lang en`, Hermes treats it as a normal message. The agent should then run the apply script:

```bash
python3 $HERMES_HOME/command_i18n/apply_command_i18n.py zh
```

or:

```bash
python3 $HERMES_HOME/command_i18n/apply_command_i18n.py en
```

Because `/lang` remains appended in both languages, the menu entry stays discoverable after switching back to English.

## Migration Recipe

On the source machine:

```bash
git clone https://github.com/aiocy/hermes-skills.git
```

On the target VPS/profile:

```bash
cd hermes-skills/autonomous-ai-agents/hermes-telegram-command-i18n
python3 scripts/install_command_i18n.py --lang zh --apply
hermes gateway restart
python3 scripts/apply_command_i18n.py status
```

If `python3` cannot import Hermes modules, the script tries to discover the Hermes install path by running `hermes --version` and adding the reported `Project:` path to `sys.path`.

## Token Lookup

The Telegram token is read from:

```text
$HERMES_HOME/.env
TELEGRAM_BOT_TOKEN=...
```

Do not use `hermes_cli.config.load_config().platforms.telegram.token`; on current Hermes deployments the token often lives only in `.env`, so config lookup returns empty.

## Common Pitfalls

1. **Thinking `/lang` is an official Hermes command.** It is a menu entry plus conversational handling. The underlying mechanism is official gateway hooks and Telegram Bot API calls.

2. **Forgetting to restart after install.** The `--apply` flag updates Telegram immediately, but the startup hook only becomes active after `hermes gateway restart`.

3. **Running scripts with the wrong profile.** Always pass `--hermes-home` when deploying to a non-default profile.

4. **Telegram topic scopes.** The scripts update `default`, `all_private_chats`, and `all_group_chats`. Forum topic-specific `BotCommandScopeChat` menus may still be managed by Hermes lazily.

5. **New Hermes commands stay English until translated.** The script falls back to Hermes' English description for commands missing from `translations-zh.json`.

6. **Telegram command limits.** Telegram officially documents a 100-command limit and 1-256 char descriptions. This package uses Hermes' 30-menu-command list plus `/lang`, so it stays safely below the limit.

## Verification Checklist

- [ ] `python3 scripts/install_command_i18n.py --lang zh --apply` exits successfully.
- [ ] `$HERMES_HOME/hooks/telegram-command-i18n/HOOK.yaml` exists.
- [ ] `$HERMES_HOME/command_i18n/apply_command_i18n.py` exists.
- [ ] `$HERMES_HOME/cmd_language.json` contains `{"lang": "zh"}` or `{"lang": "en"}`.
- [ ] `python3 scripts/apply_command_i18n.py status` shows `lang` in registered commands.
- [ ] Telegram `/` menu shows `/lang` and localized command descriptions.
- [ ] After `hermes gateway restart`, `status` still shows the desired language.
