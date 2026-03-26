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

安装 hooks 到 Claude Code 本地设置：

```bash
python -m ccnotifier install-hooks --target local
```

默认配置文件路径：

```text
~/.ccnotifier/config.yaml
```

## 📌 当前支持的事件

| 内部事件                | Claude Code 来源                   | 说明                                 |
| ----------------------- | ---------------------------------- | ------------------------------------ |
| `permission-needed`   | `Notification.permission_prompt` | Claude Code 正在等待权限确认         |
| `claude-stopped`      | `Stop`                           | Claude Code 已停止并把控制权交回用户 |
| `sensitive-operation` | `PreToolUse.Bash`                | Bash 命令命中高风险规则              |

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
```

## 🔧 Hook 安装与卸载

安装到本地 Claude Code 设置：

```bash
python -m ccnotifier install-hooks --target local
```

安装到全局 Claude Code 设置：

```bash
python -m ccnotifier install-hooks --target global
```

卸载：

```bash
python -m ccnotifier uninstall-hooks --target local
```

安装行为说明：

- `--target local` 写入 `~/.claude/settings.local.json`
- `--target global` 写入 `~/.claude/settings.json`
- 安装器会在修改前备份已有目标文件
- 只会替换带有 `ccnotifier-managed` 标记的条目
- 不会删除其他无关 hooks

## 🐍 Python 解释器行为

安装后的 hook 命令会固定使用执行 `install-hooks` 时对应的 Python 解释器。

实现方式：

- 安装器使用 `sys.executable`
- 将该解释器绝对路径写入 Claude Code 设置文件
- 后续 hook 执行时直接调用该解释器

这意味着：

- 执行 `install-hooks` 时所处的 Python 环境会影响后续 hook 执行
- 如果之后切换了环境，应在新环境里重新执行安装

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

## 🧰 CLI

可用命令：

```bash
python -m ccnotifier init-config
python -m ccnotifier print-default-config
python -m ccnotifier install-hooks --target local
python -m ccnotifier install-hooks --target global
python -m ccnotifier uninstall-hooks --target local
python -m ccnotifier uninstall-hooks --target global
```

## 📁 项目结构

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
