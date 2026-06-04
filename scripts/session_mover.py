#!/usr/bin/env python3
"""Safely relocate Codex local session metadata between project directories."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


def codex_home_from_env(value: str | None = None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    env = os.environ.get("CODEX_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def norm_path(value: str | Path) -> str:
    try:
        return str(Path(value).expanduser().resolve())
    except Exception:
        return str(value)


def path_equal(a: str | Path | None, b: str | Path | None) -> bool:
    if not a or not b:
        return False
    return norm_path(str(a)).casefold() == norm_path(str(b)).casefold()


def read_jsonl(path: Path) -> list[tuple[str, dict[str, Any] | None]]:
    rows: list[tuple[str, dict[str, Any] | None]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            rows.append((line, None))
            continue
        try:
            rows.append((line, json.loads(line)))
        except json.JSONDecodeError:
            rows.append((line, None))
    return rows


def write_jsonl(path: Path, rows: list[tuple[str, dict[str, Any] | None]]) -> None:
    out: list[str] = []
    for original, obj in rows:
        if obj is None:
            out.append(original)
        else:
            out.append(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
    path.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def recursive_find_cwds(obj: Any) -> list[str]:
    values: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in {"cwd", "current_working_directory", "workspace"} and isinstance(value, str):
                values.append(value)
            values.extend(recursive_find_cwds(value))
    elif isinstance(obj, list):
        for item in obj:
            values.extend(recursive_find_cwds(item))
    return values


def recursive_replace_cwd(obj: Any, old: str, new: str) -> int:
    changed = 0
    if isinstance(obj, dict):
        for key, value in list(obj.items()):
            if key in {"cwd", "current_working_directory", "workspace"} and isinstance(value, str) and path_equal(value, old):
                obj[key] = new
                changed += 1
            else:
                changed += recursive_replace_cwd(value, old, new)
    elif isinstance(obj, list):
        for item in obj:
            changed += recursive_replace_cwd(item, old, new)
    return changed


def session_id_from_obj(obj: dict[str, Any] | None, fallback: str) -> str:
    if not isinstance(obj, dict):
        return fallback
    candidates = [
        obj.get("session_id"),
        obj.get("id"),
        obj.get("conversation_id"),
    ]
    payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
    candidates.extend([payload.get("session_id"), payload.get("id"), payload.get("conversation_id")])
    for item in candidates:
        if isinstance(item, str) and item.strip():
            return item.strip()
    return fallback


def title_from_obj(obj: dict[str, Any] | None) -> str:
    if not isinstance(obj, dict):
        return ""
    payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
    for key in ("thread_name", "title", "name", "summary"):
        value = obj.get(key) or payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def json_text_contains(path: Path, needle: str) -> bool:
    if not needle:
        return True
    try:
        return needle.casefold() in path.read_text(encoding="utf-8", errors="replace").casefold()
    except Exception:
        return False


@dataclass
class Candidate:
    session_id: str
    path: str
    cwd: str
    title: str
    mtime: str
    matched_by: str


def discover_session_files(codex_home: Path) -> list[Path]:
    sessions = codex_home / "sessions"
    if not sessions.is_dir():
        return []
    return sorted(sessions.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)


def inspect_session(path: Path) -> tuple[str, str, str]:
    rows = read_jsonl(path)
    fallback = path.stem
    session_id = fallback
    title = ""
    cwd = ""
    for _line, obj in rows[:80]:
        if not isinstance(obj, dict):
            continue
        session_id = session_id_from_obj(obj, session_id)
        title = title or title_from_obj(obj)
        cwds = recursive_find_cwds(obj)
        if cwds and not cwd:
            cwd = cwds[0]
        if title and cwd and session_id != fallback:
            break
    return session_id, title, cwd


def audit_sessions(codex_home: Path, from_cwd: str | None, query: str | None, recent: int) -> list[Candidate]:
    candidates: list[Candidate] = []
    for path in discover_session_files(codex_home):
        session_id, title, cwd = inspect_session(path)
        matched = False
        matched_by = []
        if from_cwd and path_equal(cwd, from_cwd):
            matched = True
            matched_by.append("cwd")
        elif not from_cwd:
            matched = True
            matched_by.append("all")
        if query:
            if query.casefold() in title.casefold() or query.casefold() in session_id.casefold() or json_text_contains(path, query):
                matched = matched and True
                matched_by.append("query")
            else:
                matched = False
        if matched:
            candidates.append(
                Candidate(
                    session_id=session_id,
                    path=str(path),
                    cwd=cwd,
                    title=title,
                    mtime=datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                    matched_by="+".join(matched_by),
                )
            )
        if recent and len(candidates) >= recent:
            break
    return candidates


def match_requested(
    candidates: list[Candidate],
    requested: list[str],
    all_matching: bool,
) -> tuple[list[Candidate], list[dict[str, Any]]]:
    if all_matching:
        return candidates, []
    selected: list[Candidate] = []
    ambiguities: list[dict[str, Any]] = []
    for req in requested:
        req_fold = req.casefold()
        req_path = norm_path(req).casefold()
        exact_path_matches = [c for c in candidates if norm_path(c.path).casefold() == req_path]
        if exact_path_matches:
            matches = exact_path_matches
        else:
            matches = [
                c
                for c in candidates
                if req_fold in c.session_id.casefold()
                or req_fold in Path(c.path).name.casefold()
            ]
        if len(matches) > 1:
            ambiguities.append(
                {
                    "request": req,
                    "reason": "Matched multiple session files. Use the exact JSONL path, or use --all-matching only when intentionally moving every match.",
                    "matches": [asdict(c) for c in matches],
                }
            )
            continue
        for item in matches:
            if item not in selected:
                selected.append(item)
    return selected, ambiguities


def duplicate_session_id_groups(candidates: list[Candidate]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[Candidate]] = {}
    for candidate in candidates:
        groups.setdefault(candidate.session_id, []).append(candidate)
    return {
        session_id: [asdict(item) for item in items]
        for session_id, items in groups.items()
        if len(items) > 1
    }


def backup_files(codex_home: Path, session_paths: list[Path]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = codex_home / "backups" / "session-mover" / stamp
    backup.mkdir(parents=True, exist_ok=True)
    for rel in ("session_index.jsonl", "cap_sid"):
        src = codex_home / rel
        if src.exists():
            dst = backup / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    sessions_root = codex_home / "sessions"
    for src in session_paths:
        try:
            rel = src.relative_to(sessions_root)
        except ValueError:
            rel = Path(src.name)
        dst = backup / "sessions" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return backup


def update_session_file(path: Path, old_cwd: str, new_cwd: str) -> int:
    rows = read_jsonl(path)
    changed = 0
    for _line, obj in rows:
        if isinstance(obj, dict):
            changed += recursive_replace_cwd(obj, old_cwd, new_cwd)
    if changed:
        write_jsonl(path, rows)
    return changed


def update_index(codex_home: Path, selected: list[Candidate], old_cwd: str, new_cwd: str) -> int:
    path = codex_home / "session_index.jsonl"
    if not path.is_file():
        return 0
    ids = {c.session_id for c in selected}
    names = {Path(c.path).stem for c in selected}
    rows = read_jsonl(path)
    changed = 0
    for _line, obj in rows:
        if not isinstance(obj, dict):
            continue
        sid = session_id_from_obj(obj, "")
        text = json.dumps(obj, ensure_ascii=False)
        if sid in ids or any(name in text for name in names):
            changed += recursive_replace_cwd(obj, old_cwd, new_cwd)
    if changed:
        write_jsonl(path, rows)
    return changed


def update_cap_sid(codex_home: Path, old_cwd: str, new_cwd: str) -> int:
    path = codex_home / "cap_sid"
    if not path.is_file():
        return 0
    try:
        data = load_json(path)
    except Exception:
        return 0
    changed = 0
    if isinstance(data, dict):
        workspace = data.get("workspace_by_cwd")
        if isinstance(workspace, dict):
            old_key = next((key for key in workspace.keys() if path_equal(key, old_cwd)), None)
            new_key = new_cwd
            if old_key and new_key not in workspace:
                workspace[new_key] = workspace[old_key]
                changed += 1
        changed += recursive_replace_cwd(data, old_cwd, new_cwd)
    if changed:
        write_json(path, data)
    return changed


def command_audit(args: argparse.Namespace) -> dict[str, Any]:
    codex_home = codex_home_from_env(args.codex_home)
    candidates = audit_sessions(codex_home, args.from_cwd, args.query, args.recent)
    return {
        "ok": True,
        "status": "audit",
        "codex_home": str(codex_home),
        "from_cwd": norm_path(args.from_cwd) if args.from_cwd else "",
        "to_cwd": norm_path(args.to_cwd) if args.to_cwd else "",
        "count": len(candidates),
        "duplicate_session_ids": duplicate_session_id_groups(candidates),
        "candidates": [asdict(c) for c in candidates],
    }


def command_move(args: argparse.Namespace) -> dict[str, Any]:
    codex_home = codex_home_from_env(args.codex_home)
    old_cwd = norm_path(args.from_cwd)
    new_cwd = norm_path(args.to_cwd)
    candidates = audit_sessions(codex_home, old_cwd, args.query, args.recent)
    selected, ambiguities = match_requested(candidates, args.session or [], args.all_matching)
    if ambiguities:
        return {
            "ok": False,
            "status": "ambiguous_selection",
            "codex_home": str(codex_home),
            "from_cwd": old_cwd,
            "to_cwd": new_cwd,
            "failures": ["One or more --session values matched multiple session files."],
            "ambiguities": ambiguities,
            "candidates": [asdict(c) for c in candidates],
        }
    if not selected:
        return {
            "ok": False,
            "status": "no_selection",
            "codex_home": str(codex_home),
            "from_cwd": old_cwd,
            "to_cwd": new_cwd,
            "failures": ["No sessions selected. Use --session or --all-matching after audit."],
            "candidates": [asdict(c) for c in candidates],
        }
    if not args.apply:
        return {
            "ok": True,
            "status": "dry_run",
            "codex_home": str(codex_home),
            "from_cwd": old_cwd,
            "to_cwd": new_cwd,
            "selected": [asdict(c) for c in selected],
            "would_update": ["session files", "session_index.jsonl if matching entries exist", "cap_sid workspace mapping if present"],
        }
    session_paths = [Path(c.path) for c in selected]
    backup = backup_files(codex_home, session_paths)
    session_changes = {}
    for path in session_paths:
        session_changes[str(path)] = update_session_file(path, old_cwd, new_cwd)
    index_changes = update_index(codex_home, selected, old_cwd, new_cwd)
    cap_changes = update_cap_sid(codex_home, old_cwd, new_cwd)
    return {
        "ok": True,
        "status": "moved",
        "codex_home": str(codex_home),
        "backup": str(backup),
        "from_cwd": old_cwd,
        "to_cwd": new_cwd,
        "selected": [asdict(c) for c in selected],
        "session_file_cwd_replacements": session_changes,
        "session_index_replacements": index_changes,
        "cap_sid_replacements": cap_changes,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Relocate Codex session metadata between project directories.")
    sub = parser.add_subparsers(dest="command", required=True)

    audit = sub.add_parser("audit", help="List candidate sessions without changing files.")
    audit.add_argument("--codex-home")
    audit.add_argument("--from-cwd")
    audit.add_argument("--to-cwd")
    audit.add_argument("--query")
    audit.add_argument("--recent", type=int, default=30)
    audit.set_defaults(func=command_audit)

    move = sub.add_parser("move", help="Move selected sessions. Dry-run unless --apply is provided.")
    move.add_argument("--codex-home")
    move.add_argument("--from-cwd", required=True)
    move.add_argument("--to-cwd", required=True)
    move.add_argument("--query")
    move.add_argument("--recent", type=int, default=100)
    move.add_argument("--session", action="append", default=[])
    move.add_argument("--all-matching", action="store_true")
    move.add_argument("--apply", action="store_true")
    move.set_defaults(func=command_move)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = args.func(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
