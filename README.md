# CCNotifier

[English](./README.en.md)

> 本项目参考自 [kdush/Claude-Code-Notifier](https://github.com/kdush/Claude-Code-Notifier)，做了简化与重构。

**面向 Claude Code 的轻量通知系统，聚焦权限提醒、任务结束提醒与高风险操作预警。**

## ✨ 特性

- **权限提醒**：当 Claude Code 进入权限确认流程时立即通知
- **停止提醒**：当 Claude Code 完成工作并等待你查看结果或继续处理时通知
- **高风险预警**：执行高风险 Bash 规则时发送提醒
- **限流**：固定时间窗限流，避免短时间通知洪泛
- **简洁接入**：提供配置初始化、hook 安装与卸载 CLI

## 🚀 快速开始

安装项目：

```bash
pip install -e .
```

初始化默认配置：

```bash
python -m ccnotifier init-config
```

默认配置文件路径：

```text
~/.ccnotifier/config.yaml
```

安装 hooks 有三种方式：

### 1. 安装到 User 作用域

写入位置：`~/.claude/settings.json`

```bash
python -m ccnotifier install-hooks --target user
```

### 2. 安装到 Project 作用域

写入位置：`<project>/.claude/settings.json`

```bash
python -m ccnotifier install-hooks --target project
```

### 3. 安装到 Local 作用域

写入位置：`<project>/.claude/settings.local.json`

```bash
python -m ccnotifier install-hooks --target local
```

默认 target 是 `user`，所以直接运行下面这条命令时，也会写入 `~/.claude/settings.json`：

```bash
python -m ccnotifier install-hooks
```

卸载：

```bash
python -m ccnotifier uninstall-hooks --target user
python -m ccnotifier uninstall-hooks --target project
python -m ccnotifier uninstall-hooks --target local
```

## 📌 当前支持的事件

| 内部事件                    | Claude Code 来源                                                                                   | 说明                                 |
| --------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------ |
| `user-interaction-needed` | `Notification.permission_prompt` / `Notification.idle_prompt` / `PreToolUse.AskUserQuestion` | Claude Code 需要用户交互             |
| `claude-stopped`          | `Stop`                                                                                           | Claude Code 已停止并把控制权交回用户 |
| `sensitive-operation`     | `PreToolUse.Bash`                                                                                | Bash 命令命中高风险规则              |

## 📬 通知渠道

| 渠道       | 当前状态  |
| ---------- | --------- |
| Telegram   | ✅ 已支持 |
| Webhook    | ✅ 已支持 |
| DingTalk   | 🚧 计划中 |
| Feishu     | 🚧 计划中 |
| WeCom      | 🚧 计划中 |
| Email      | 🚧 计划中 |
| ServerChan | 🚧 计划中 |

## ⚙️ 配置说明

默认配置示例：

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
    proxy_url: "" # 可选 HTTP 代理，例如 http://127.0.0.1:7890

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

## ⚠️ 当前高风险 Bash 规则

当前内置规则包括：

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

