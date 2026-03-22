#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize the safe-grow workflow in a project."
    )
    parser.add_argument("target", help="Target project directory")
    parser.add_argument(
        "--project-name",
        help="Project name used inside templates. Defaults to target directory name.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files instead of skipping them.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned writes without modifying files.",
    )
    return parser.parse_args()


def render_template(template_path: Path, project_name: str) -> str:
    content = template_path.read_text(encoding="utf-8")
    return content.replace("{{PROJECT_NAME}}", project_name)


def main() -> int:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    template_root = script_dir.parent / "templates" / "safe-grow"
    target_root = Path(args.target).expanduser().resolve()
    project_name = args.project_name or target_root.name

    if not template_root.exists():
        raise SystemExit(f"Template directory not found: {template_root}")

    planned_writes: list[tuple[Path, str]] = []
    skipped: list[Path] = []

    for template_path in sorted(template_root.rglob("*.tpl")):
        relative = template_path.relative_to(template_root)
        destination = target_root / relative.with_suffix("")
        rendered = render_template(template_path, project_name)

        if destination.exists() and not args.force:
            skipped.append(destination)
            continue

        planned_writes.append((destination, rendered))

    if args.dry_run:
        print(f"[dry-run] target: {target_root}")
        for destination, _ in planned_writes:
            print(f"write {destination}")
        for destination in skipped:
            print(f"skip  {destination}")
        return 0

    for destination, rendered in planned_writes:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
        print(f"wrote {destination}")

    for destination in skipped:
        print(f"skipped existing {destination}")

    if planned_writes:
        print("")
        print("Next steps:")
        print(
            f"1. Fill {target_root / '.claude/loop/PROJECT_GROWTH.md'} with project-specific goals."
        )
        print(
            f"2. Paste audit results into {target_root / '.claude/loop/GLM_AUDIT.md'}."
        )
        print("3. Run /safe-grow inside the target project.")
    else:
        print("No files written.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
