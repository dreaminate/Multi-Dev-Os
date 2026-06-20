#!/usr/bin/env python3
"""Deploy project skills to Claude discovery directories by default.

Source of truth:
  dev/skills/{skill-name}/SKILL.md

Default install targets:
  .claude/skills/{skill-name}/SKILL.md   (Claude Code project)
  ~/.claude/skills/{skill-name}/SKILL.md (Claude Code user)
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


DEV = Path(__file__).resolve().parents[1]
ROOT = DEV.parent
SOURCE = DEV / "skills"
TARGETS = {
    "project": {
        "claude": ROOT / ".claude" / "skills",
        "codex": ROOT / ".agents" / "skills",
    },
    "user": {
        "claude": Path.home() / ".claude" / "skills",
        "codex": Path.home() / ".agents" / "skills",
    },
}


def discover_skills(source: Path) -> list[Path]:
    if not source.is_dir():
        return []
    return sorted(path for path in source.iterdir() if path.is_dir() and (path / "SKILL.md").is_file())


def copy_skill(src: Path, dst: Path, replace: bool) -> None:
    if dst.exists():
        if not replace:
            raise FileExistsError(f"{dst} already exists; pass --replace to overwrite")
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        else:
            shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"))


def symlink_skill(src: Path, dst: Path, replace: bool) -> None:
    if dst.exists() or dst.is_symlink():
        if not replace:
            raise FileExistsError(f"{dst} already exists; pass --replace to overwrite")
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        else:
            shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.symlink_to(src.resolve(), target_is_directory=True)


def target_sets(scope: str) -> list[tuple[str, dict[str, Path]]]:
    if scope == "project":
        return [("project", TARGETS["project"])]
    if scope == "user":
        return [("user", TARGETS["user"])]
    return [("project", TARGETS["project"]), ("user", TARGETS["user"])]


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def deploy(write: bool, replace: bool, mode: str, scope: str, targets: set[str]) -> list[str]:
    skills = discover_skills(SOURCE)
    if not skills:
        return [f"no skills found under {SOURCE}"]
    messages: list[str] = []
    for skill in skills:
        for scope_name, all_targets in target_sets(scope):
            selected = {name: path for name, path in all_targets.items() if name in targets}
            for tool_name, target_root in selected.items():
                dst = target_root / skill.name
                action = "symlink" if mode == "symlink" else "copy"
                messages.append(f"{action} [{scope_name}/{tool_name}]: {skill.relative_to(ROOT)} -> {display_path(dst)}")
                if not write:
                    continue
                if mode == "symlink":
                    symlink_skill(skill, dst, replace)
                else:
                    copy_skill(skill, dst, replace)
    return messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deploy dev/skills to Claude skill paths by default.")
    parser.add_argument("--write", action="store_true", help="Actually create/update selected skill deployment paths.")
    parser.add_argument("--replace", action="store_true", help="Overwrite existing deployed skill directories.")
    parser.add_argument("--mode", choices=("copy", "symlink"), default="copy", help="Deploy by copying or symlinking.")
    parser.add_argument("--scope", choices=("project", "user", "both"), default="project", help="Deploy to project paths, user-home paths, or both.")
    parser.add_argument("--target", choices=("claude", "codex"), action="append", default=["claude"], help="Deployment target; default: claude. Repeatable.")
    args = parser.parse_args(argv)

    try:
        messages = deploy(
            write=args.write,
            replace=args.replace,
            mode=args.mode,
            scope=args.scope,
            targets=set(args.target),
        )
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(("WRITE" if args.write else "DRY-RUN") + ": skill deployment")
    for message in messages:
        print(message)
    if not args.write:
        print("preview only: rerun with --write to deploy; add --replace to refresh existing deployments")
    return 0


if __name__ == "__main__":
    sys.exit(main())
