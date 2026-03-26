# CCNotifier

[简体中文](./README.md)

> This project is based on [kdush/Claude-Code-Notifier](https://github.com/kdush/Claude-Code-Notifier), with a simplified and reworked implementation for the goals of this repository.

**A lightweight notification system for Claude Code, focused on permission prompts, task completion notifications, and high-risk operation alerts.**

## ✨ Features

- **Permission alerts** — notify immediately when Claude Code enters a permission confirmation flow
- **Stop alerts** — notify when Claude Code finishes work and waits for you to review results or continue
- **High-risk warnings** — notify when a high-risk Bash rule is matched
- **Rate limiting** — fixed-window throttling to avoid notification bursts
- **Simple integration** — includes CLI commands for config initialization and hook installation/uninstallation

## 🚀 Quick start

Install the project:

```bash
pip install -e .
```

Initialize the default config:

```bash
python -m ccnotifier init-config
```

Install hooks into local Claude Code settings:

```bash
python -m ccnotifier install-hooks --target local
```

Default config path:

```text
~/.ccnotifier/config.yaml
```

## 📌 Supported events

| Internal event | Claude Code source | Description |
| -------------- | ------------------ | ----------- |
| `permission-needed` | `Notification.permission_prompt` | Claude Code is waiting for permission approval |
| `claude-stopped` | `Stop` | Claude Code has stopped and handed control back to the user |
| `sensitive-operation` | `PreToolUse.Bash` | A Bash command matched a high-risk rule |

## 📬 Notification channels

| Channel | Current status |
| ------- | -------------- |
| Telegram | ✅ Supported |
| Webhook | ✅ Supported |
| DingTalk | 🚧 Planned |
| Feishu | 🚧 Planned |
| WeCom | 🚧 Planned |
| Email | 🚧 Planned |
| ServerChan | 🚧 Planned |

## ⚙️ Configuration

Default configuration example:

```yaml
default_channels:
  - telegram

events:
  permission-needed:
    channels: [telegram]
  claude-stopped:
    channels: [telegram]
  sensitive-operation:
    channels: [telegram]
  idle-prompt:
    channels: [telegram]

channels:
  telegram:
    enabled: true
    bot_token: "<your bot token>"
    chat_id: "<your chat id>"
    parse_mode: Markdown
    timeout_seconds: 10
    proxy_url: "" # optional HTTP proxy, for example http://127.0.0.1:7890

  webhook:
    enabled: false
    url: ""
    timeout_seconds: 10

rate_limit:
  enabled: true
  window_seconds: 10
  max_events_per_window: 3
  scope: global
```

## 🔧 Hook installation and removal

Install into local Claude Code settings:

```bash
python -m ccnotifier install-hooks --target local
```

Install into global Claude Code settings:

```bash
python -m ccnotifier install-hooks --target global
```

Uninstall:

```bash
python -m ccnotifier uninstall-hooks --target local
```

Installation behavior:

- `--target local` writes to `~/.claude/settings.local.json`
- `--target global` writes to `~/.claude/settings.json`
- the installer backs up the existing target file before modification
- only entries tagged with `ccnotifier-managed` are replaced
- unrelated hooks are preserved

## 🐍 Python interpreter behavior

The installed hook command uses the Python interpreter that runs `install-hooks`.

Implementation details:

- the installer uses `sys.executable`
- the absolute interpreter path is written into Claude Code settings
- future hook executions directly use that recorded interpreter

This means:

- the Python environment used during `install-hooks` matters
- if you switch environments later, reinstall hooks in the new environment

## ⚠️ Current high-risk Bash rules

Current built-in rules include:

- `rm -rf`
- `sudo rm`
- `delete from ... where`
- `drop table`
- `truncate table`
- `git push --force`
- `npm publish`
- `docker rm -f`
- `kill -9`
- `chmod 777`

## 🧰 CLI

Available commands:

```bash
python -m ccnotifier init-config
python -m ccnotifier print-default-config
python -m ccnotifier install-hooks --target local
python -m ccnotifier install-hooks --target global
python -m ccnotifier uninstall-hooks --target local
python -m ccnotifier uninstall-hooks --target global
```

## 📁 Project structure

```text
.
├─ pyproject.toml
├─ README.md
├─ README.en.md
├─ src/
│  └─ ccnotifier/
│     ├─ cli.py
│     ├─ channels/
│     │  ├─ base.py
│     │  ├─ telegram.py
│     │  └─ webhook.py
│     ├─ core/
│     │  ├─ config.py
│     │  ├─ events.py
│     │  ├─ notifier.py
│     │  └─ rate_limit.py
│     └─ hooks/
│        ├─ handler.py
│        └─ installer.py
└─ tests/
```
