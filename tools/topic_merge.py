#!/usr/bin/env python
import argparse
import json
import re
from pathlib import Path


def _slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9\-]+", "", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value


def _load_merge_map(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Merge map must be a JSON object: {\"old-slug\": \"new-slug\"}.")
    out: dict[str, str] = {}
    for old_raw, new_raw in data.items():
        old_slug = _slugify(str(old_raw))
        new_slug = _slugify(str(new_raw))
        if not old_slug or not new_slug or old_slug == new_slug:
            continue
        out[old_slug] = new_slug
    return out


def _replace_topic_links(text: str, merge_map: dict[str, str]) -> tuple[str, int]:
    total = 0
    updated = text
    for old_slug, new_slug in merge_map.items():
        # Replace explicit topic paths emitted by NORA, with or without .md.
        patterns = [
            (f"[[Topics/{old_slug}|", f"[[Topics/{new_slug}|"),
            (f"[[Topics/{old_slug}]]", f"[[Topics/{new_slug}]]"),
            (f"[[Topics/{old_slug}.md|", f"[[Topics/{new_slug}|"),
            (f"[[Topics/{old_slug}.md]]", f"[[Topics/{new_slug}]]"),
        ]
        for src, dst in patterns:
            count = updated.count(src)
            if count:
                updated = updated.replace(src, dst)
                total += count
    return updated, total


def _write_redirect_stub(old_path: Path, new_slug: str) -> None:
    title = old_path.stem.replace("-", " ").strip().title() or old_path.stem
    content = (
        "---\n"
        "type: topic-redirect\n"
        f"redirect_to: \"Topics/{new_slug}\"\n"
        "status: merged\n"
        "---\n"
        f"# {title}\n\n"
        f"This topic was merged into [[Topics/{new_slug}]].\n"
    )
    old_path.write_text(content, encoding="utf-8")


def run(vault_path: Path, merge_map: dict[str, str], apply: bool, delete_old: bool) -> None:
    instagram_dir = vault_path / "Instagram Notes"
    topics_dir = vault_path / "Topics"
    if not instagram_dir.exists():
        raise FileNotFoundError(f"Instagram Notes folder not found: {instagram_dir}")
    if not topics_dir.exists():
        raise FileNotFoundError(f"Topics folder not found: {topics_dir}")

    note_rewrites: list[tuple[Path, int]] = []
    for note_path in sorted(instagram_dir.glob("*.md")):
        original = note_path.read_text(encoding="utf-8")
        updated, count = _replace_topic_links(original, merge_map)
        if count > 0:
            note_rewrites.append((note_path, count))
            if apply:
                note_path.write_text(updated, encoding="utf-8")

    hub_actions: list[str] = []
    for old_slug, new_slug in merge_map.items():
        old_path = topics_dir / f"{old_slug}.md"
        new_path = topics_dir / f"{new_slug}.md"
        if not old_path.exists():
            hub_actions.append(f"skip missing old hub: {old_path.as_posix()}")
            continue
        if not new_path.exists():
            hub_actions.append(f"create missing canonical hub: {new_path.as_posix()}")
            if apply:
                new_path.write_text(f"# {new_slug.replace('-', ' ').title()}\n\n## Related Videos\n", encoding="utf-8")
        if delete_old:
            hub_actions.append(f"delete old hub: {old_path.as_posix()}")
            if apply:
                old_path.unlink(missing_ok=True)
        else:
            hub_actions.append(f"write redirect stub: {old_path.as_posix()} -> Topics/{new_slug}")
            if apply:
                _write_redirect_stub(old_path, new_slug)

    mode = "APPLY" if apply else "DRY-RUN"
    print(f"[topic-merge] mode={mode}")
    print(f"[topic-merge] vault={vault_path}")
    print(f"[topic-merge] merges={len(merge_map)}")
    print(f"[topic-merge] notes_with_link_rewrites={len(note_rewrites)}")
    print(f"[topic-merge] total_link_rewrites={sum(count for _, count in note_rewrites)}")
    for path, count in note_rewrites:
        print(f"  - rewrite {count} link(s): {path.as_posix()}")
    for action in hub_actions:
        print(f"  - {action}")
    if not apply:
        print("[topic-merge] No files were modified. Re-run with --apply to write changes.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge and dedupe NORA topic hubs in a local Obsidian vault.")
    parser.add_argument("--vault", required=True, help="Path to OBSIDIAN_VAULT_PATH root.")
    parser.add_argument("--map", required=True, dest="map_path", help="Path to merge JSON map.")
    parser.add_argument("--apply", action="store_true", help="Write changes. Default is dry-run.")
    parser.add_argument(
        "--delete-old",
        action="store_true",
        help="Delete old topic hubs instead of replacing them with redirect stubs.",
    )
    args = parser.parse_args()

    vault_path = Path(args.vault).expanduser().resolve()
    map_path = Path(args.map_path).expanduser().resolve()
    merge_map = _load_merge_map(map_path)
    if not merge_map:
        raise ValueError("Merge map has no valid old->new pairs.")
    run(vault_path=vault_path, merge_map=merge_map, apply=args.apply, delete_old=args.delete_old)


if __name__ == "__main__":
    main()
