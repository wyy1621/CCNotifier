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

Default config path:

```text
~/.ccnotifier/config.yaml
```

There are three ways to install hooks:

### 1. Install into the User scope

Writes to: `~/.claude/settings.json`

```bash
python -m ccnotifier install-hooks --target user
```

### 2. Install into the Project scope

Writes to: `<project>/.claude/settings.json`

```bash
python -m ccnotifier install-hooks --target project
```

### 3. Install into the Local scope

Writes to: `<project>/.claude/settings.local.json`

```bash
python -m ccnotifier install-hooks --target local
```

The default target is `user`, so this command also writes to `~/.claude/settings.json`:

```bash
python -m ccnotifier install-hooks
```

Uninstall:

```bash
python -m ccnotifier uninstall-hooks --target user
python -m ccnotifier uninstall-hooks --target project
python -m ccnotifier uninstall-hooks --target local
```

The installed hook configuration is written per Claude Code hook event:
- `Notification` uses a single regex matcher: `permission_prompt|idle_prompt`
- `PreToolUse` uses a single regex matcher: `Bash|AskUserQuestion`
- `Stop` remains a separate entry

Different hook events cannot be merged into the same entry.

The managed command written during installation is always `python -m ccnotifier.hooks.handler`, so Claude settings do not bake in an absolute Python interpreter path from install time.

## 📌 Supported events

| Internal event              | Claude Code source                                                                                 | Description                                                 |
| --------------------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| `user-interaction-needed` | `Notification.permission_prompt` / `Notification.idle_prompt` / `PreToolUse.AskUserQuestion` | Claude Code needs user interaction                          |
| `claude-stopped`          | `Stop`                                                                                           | Claude Code has stopped and handed control back to the user |
| `sensitive-operation`     | `PreToolUse.Bash`                                                                                | A Bash command matched a high-risk rule                     |

## 📬 Notification channels

| Channel    | Current status |
| ---------- | -------------- |
| Telegram   | ✅ Supported   |
| Webhook    | ✅ Supported   |
| DingTalk   | 🚧 Planned     |
| Feishu     | 🚧 Planned     |
| WeCom      | 🚧 Planned     |
| Email      | 🚧 Planned     |
| ServerChan | 🚧 Planned     |

## ⚙️ Configuration

Default configuration example:

```yaml
default_channels:
  - telegram

events:
  user-interaction-needed:
    channels: [telegram]
  claude-stopped:
    channels: [telegram]
  sensitive-operation:
    channels: [telegram]

channels:
  telegram:
    enabled: true
    bot_token: "<your bot token>"
    chat_id: "<your chat id>"
    parse_mode: Markdown
    timeout_seconds: 10
    proxy_url: "" # optional HTTP proxy, for example http://127.0.0.1:7890
    auto_delete_after_seconds: 0 # block after send, then delete; 0 disables it, values below 0 clamp to 0, values above 10 clamp to 10

  webhook:
    enabled: false
    url: ""
    timeout_seconds: 10

rate_limit:
  enabled: true
  window_seconds: 10
  max_events_per_window: 3
  scope: global

logging:
  file_path: ~/.ccnotifier/ccnotifier.log
```

Notes:
- `PreToolUse.AskUserQuestion` notifications now prefer the readable question text instead of sending the full structured `tool_input`
- Telegram can auto-delete sent messages via `auto_delete_after_seconds`; after a successful send it blocks for that many seconds before calling `deleteMessage`; `0` disables it, values below `0` clamp to `0`, and values above `10` clamp to `10`
- Whether deletion succeeds still depends on Telegram's official permission rules
- Local file logging now writes the full hook debug details to the file pointed to by `logging.file_path`, which makes event intake and mapping easier to inspect

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

