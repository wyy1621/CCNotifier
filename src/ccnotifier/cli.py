from __future__ import annotations

import argparse
from pathlib import Path

from .core.config import DEFAULT_CONFIG_PATH, ensure_parent_dir, render_default_config
from .hooks.installer import install_hooks, uninstall_hooks


def main() -> int:
    parser = argparse.ArgumentParser(prog="ccnotifier")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-config", help="Write default config file")
    init_parser.add_argument("--path", default=str(DEFAULT_CONFIG_PATH))

    install_parser = subparsers.add_parser("install-hooks", help="Install Claude Code hooks")
    install_parser.add_argument(
        "--target",
        choices=["local", "project", "user"],
        default="user",
        help="Settings scope: user=~/.claude/settings.json, project=.claude/settings.json, local=.claude/settings.local.json",
    )

    uninstall_parser = subparsers.add_parser("uninstall-hooks", help="Remove Claude Code hooks")
    uninstall_parser.add_argument(
        "--target",
        choices=["local", "project", "user"],
        default="user",
        help="Settings scope: user=~/.claude/settings.json, project=.claude/settings.json, local=.claude/settings.local.json",
    )

    subparsers.add_parser("print-default-config", help="Print default YAML config")

    args = parser.parse_args()

    if args.command == "init-config":
        config_path = Path(args.path)
        ensure_parent_dir(config_path)
        if not config_path.exists():
            config_path.write_text(render_default_config(), encoding="utf-8")
        print(str(config_path))
        return 0

    if args.command == "install-hooks":
        installed_path = install_hooks(args.target)
        print(str(installed_path))
        return 0

    if args.command == "uninstall-hooks":
        installed_path = uninstall_hooks(args.target)
        print(str(installed_path))
        return 0

    if args.command == "print-default-config":
        print(render_default_config())
        return 0

    raise AssertionError(f"Unknown command: {args.command}")
