# CCNotifier

[简体中文](./README.md)

> This project is based on [kdush/Claude-Code-Notifier](https://github.com/kdush/Claude-Code-Notifier), with a simplified and reworked implementation for the goals of this repository.

**A lightweight notification system for Claude Code, focused on permission prompts, task completion notifications, high-risk operation alerts, and optional LLM command review.**

## ✨ Features

- **Permission alerts** — notify immediately when Claude Code enters a permission confirmation flow
- **Stop alerts** — notify when Claude Code finishes work and waits for you to review results or continue
- **High-risk warnings** — notify when a high-risk Bash rule is matched
- **LLM command review** — optionally ask an LLM for allow / ask / deny before executing Bash
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
- `PreToolUse` uses a single regex matcher: `AskUserQuestion`
- `PermissionRequest` uses a single regex matcher: `Bash|WebFetch`
- `Stop` remains a separate entry

Different hook events cannot be merged into the same entry.

The managed command written during installation is always `python -m ccnotifier.hooks.handler`, so Claude settings do not bake in an absolute Python interpreter path from install time.

## 📌 Supported events

| Internal event              | Claude Code source                                                                                 | Description                                                 |
| --------------------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| `user-interaction-needed` | `Notification.permission_prompt` / `Notification.idle_prompt` / `PreToolUse.AskUserQuestion` | Claude Code needs user interaction                          |
| `claude-stopped`          | `Stop`                                                                                           | Claude Code has stopped and handed control back to the user |
| `sensitive-operation`     | `PermissionRequest.Bash` / `PermissionRequest.WebFetch` + LLM `deny`                             | The LLM explicitly refused a sensitive operation            |

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

llm_review:
  enabled: false
  api_base_url: "https://api.openai.com/v1"
  api_key: ""
  model_name: ""
  timeout_seconds: 10

rate_limit:
  enabled: true
  window_seconds: 10
  max_events_per_window: 3
  scope: global

logging:
  file_path: ~/.ccnotifier/ccnotifier.log
  max_bytes: 1048576
  backup_count: 4
```

Notes:
- `PreToolUse.AskUserQuestion` notifications now prefer the readable question text instead of sending the full structured `tool_input`
- When `llm_review.enabled = true`, `PermissionRequest.Bash` and `PermissionRequest.WebFetch` are reviewed by the LLM; `allow` / `deny` are decided by the hook directly, while `ask` falls through to Claude Code's normal user confirmation flow
- The LLM review reads the command or URL target, `tool_input.description`, the current working directory, and the project name; when the LLM returns `deny`, CCNotifier also sends a `sensitive-operation` notification
- Telegram can auto-delete sent messages via `auto_delete_after_seconds`; after a successful send it blocks for that many seconds before calling `deleteMessage`; `0` disables it, values below `0` clamp to `0`, and values above `10` clamp to `10`
- Whether deletion succeeds still depends on Telegram's official permission rules
- Local file logging writes the full hook debug details to the file pointed to by `logging.file_path` and rotates automatically by size; each file is capped at 1MB and at most 5 files are kept in total


