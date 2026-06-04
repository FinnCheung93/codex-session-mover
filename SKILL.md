---
name: codex-session-mover
description: Relocate Codex desktop/CLI conversation history between project directories by auditing and safely updating local Codex session metadata, session_index.jsonl, and workspace mappings. Use when the user asks to move, migrate, relocate, reassign, or transfer Codex conversations/sessions/history from one project folder to another.
metadata:
  short-description: Move Codex conversations between project folders
  version: v1.0.0
  updated: 2026-06-04
---

# Codex Session Mover

Use this skill when the user wants Codex conversation history to appear under a different local project directory.

This skill edits Codex local state, not project code. Treat it as a careful maintenance operation.

## What It Does

Codex conversations are stored under the local Codex home, usually:

```text
~/.codex/
  sessions/
  session_index.jsonl
  cap_sid
```

Moving a conversation usually means:

1. Finding the relevant session JSONL files.
2. Backing up the session files and indexes.
3. Updating the session metadata `cwd` from the old project folder to the new project folder.
4. Updating the session index where it records the workspace/project path.
5. Updating workspace mapping state when present.

## Safety Rules

- Never bulk-migrate all sessions unless the user explicitly asks.
- Prefer `audit` first, then `move --apply`.
- If unsure which sessions are intended, show the audit result and ask the user.
- Treat duplicate `session_id` values as high risk: Codex may store multiple JSONL files with the same session id. When moving one visible conversation, use the exact JSONL `path` from audit, not the shared id.
- Do not use a session id or substring for `--session` when audit shows more than one matching file. The script will reject ambiguous selections; resolve them by using the exact path.
- Always create a backup before applying changes.
- Do not delete old mappings unless the user explicitly asks.
- Do not edit project source files; this skill only changes local Codex state.
- If the Codex UI does not refresh immediately, suggest switching projects or restarting the app after confirming files were updated.

## Commands

Use the bundled script:

```text
python scripts/session_mover.py audit --from-cwd <old-project> --to-cwd <new-project>
python scripts/session_mover.py move --from-cwd <old-project> --to-cwd <new-project> --session <id-or-path> --apply
```

Useful options:

```text
--codex-home <path>     Override Codex home. Defaults to %CODEX_HOME% or ~/.codex.
--query <text>          Filter candidate sessions by thread/title/text.
--recent <N>            Limit audit output to recent sessions.
--session <id-or-path>  Move one session by exact JSONL path or unique id/name substring. Prefer exact path.
--all-matching          Move every audited session matching from-cwd/query.
--apply                 Actually write changes.
```

`move` is a dry-run by default. The script intentionally does not accept `--dry-run`; omit `--apply` to preview changes.

## Recommended Workflow

1. Confirm the old and new project directories.
2. Run `audit`.
3. Check that the listed sessions are truly the ones the user wants. If multiple candidates share the same `session_id`, identify the intended visible conversation by JSONL `path`, date, mtime, or query hits.
4. Run `move` with an exact JSONL path in `--session` when moving one conversation. Use a session id only if audit shows it uniquely identifies one file.
5. Use `--all-matching` only when the user explicitly asked to move every audited candidate.
6. Run the move once without `--apply` and verify the `selected` list has exactly the intended file(s).
7. Run the same command with `--apply`.
8. Report:
   - backup folder
   - moved session ids/files
   - old cwd
   - new cwd
   - whether `session_index.jsonl` and `cap_sid` were updated

## Examples

Audit a project:

```text
python scripts/session_mover.py audit ^
  --from-cwd "F:\Skills\©Finn\finn-protopilot-html" ^
  --to-cwd "F:\Skills\©Finn\finn-protopilot"
```

Move one audited session:

```text
python scripts/session_mover.py move ^
  --from-cwd "F:\Skills\©Finn\finn-protopilot-html" ^
  --to-cwd "F:\Skills\©Finn\finn-protopilot" ^
  --session "C:\Users\Administrator\.codex\sessions\2026\05\28\rollout-2026-05-28T16-53-04-019e6dc9-8940-7d32-8d4a-cb4396db9400.jsonl" ^
  --apply
```

Move by id only after audit proves the id is unique:

```text
python scripts/session_mover.py move ^
  --from-cwd "F:\Skills\©Finn\finn-protopilot-html" ^
  --to-cwd "F:\Skills\©Finn\finn-protopilot" ^
  --session 019e3a27 ^
  --apply
```

Move all matching sessions after explicit user confirmation:

```text
python scripts/session_mover.py move ^
  --from-cwd "F:\Skills\©Finn\finn-protopilot-html" ^
  --to-cwd "F:\Skills\©Finn\finn-protopilot" ^
  --all-matching ^
  --apply
```

## Output

The script prints JSON so the agent can summarize it clearly for the user.

If `status` is `dry_run`, no files were changed.

If `status` is `moved`, changes were applied and backed up.
