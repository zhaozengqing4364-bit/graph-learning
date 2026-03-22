#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install the global safe-grow kit into ~/.claude."
    )
    parser.add_argument(
        "--claude-home",
        default="~/.claude",
        help="Claude home directory. Defaults to ~/.claude",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing installed files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned writes without modifying files.",
    )
    return parser.parse_args()


def render_template(template_path: Path, replacements: dict[str, str]) -> str:
    content = template_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        content = content.replace(key, value)
    return content


def plan_template_writes(
    source_root: Path, destination_root: Path, replacements: dict[str, str]
) -> list[tuple[Path, str]]:
    writes: list[tuple[Path, str]] = []
    for template_path in sorted(source_root.rglob("*.tpl")):
        relative = template_path.relative_to(source_root)
        destination = destination_root / relative.with_suffix("")
        writes.append((destination, render_template(template_path, replacements)))
    return writes


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    claude_home = Path(args.claude_home).expanduser().resolve()
    kit_root = claude_home / "safe-grow-kit"
    command_path = claude_home / "commands" / "init-safe-grow.md"

    project_template_root = repo_root / "templates" / "safe-grow"
    global_template_root = repo_root / "templates" / "safe-grow-global"
    if not project_template_root.exists():
        raise SystemExit(f"Project template root not found: {project_template_root}")
    if not global_template_root.exists():
        raise SystemExit(f"Global template root not found: {global_template_root}")

    replacements = {"{{SAFE_GROW_KIT_PATH}}": str(kit_root)}
    planned_writes = []
    planned_writes.extend(
        plan_template_writes(
            global_template_root / "safe-grow-kit" / "bin",
            kit_root / "bin",
            replacements,
        )
    )
    planned_writes.extend(
        plan_template_writes(
            global_template_root / ".claude" / "commands",
            claude_home / "commands",
            replacements,
        )
    )

    copied_tree_source = project_template_root
    copied_tree_destination = kit_root / "templates" / "safe-grow"

    if args.dry_run:
        print(f"[dry-run] install to {claude_home}")
        print(f"copy tree {copied_tree_source} -> {copied_tree_destination}")
        for destination, _ in planned_writes:
            print(f"write {destination}")
        return 0

    (claude_home / "commands").mkdir(parents=True, exist_ok=True)
    (kit_root / "bin").mkdir(parents=True, exist_ok=True)
    (kit_root / "templates").mkdir(parents=True, exist_ok=True)

    if copied_tree_destination.exists():
        if not args.force:
            raise SystemExit(
                f"{copied_tree_destination} already exists. Re-run with --force to overwrite."
            )
        shutil.rmtree(copied_tree_destination)
    shutil.copytree(copied_tree_source, copied_tree_destination)
    print(f"copied {copied_tree_source} -> {copied_tree_destination}")

    for destination, rendered in planned_writes:
        if destination.exists() and not args.force:
            raise SystemExit(
                f"{destination} already exists. Re-run with --force to overwrite."
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
        print(f"wrote {destination}")

    init_script = kit_root / "bin" / "init_safe_grow.py"
    init_script.chmod(0o755)

    print("")
    print("Installed global safe-grow kit.")
    print(f"- command: {command_path}")
    print(f"- kit root: {kit_root}")
    print("")
    print("Usage:")
    print("1. cd into any project root")
    print("2. run /init-safe-grow")
    print("3. fill PROJECT_GROWTH.md and paste GLM audit")
    print("4. run /safe-grow inside that project")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
