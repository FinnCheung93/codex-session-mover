---
name: codex-session-mover
description: Relocate Codex desktop/CLI conversation history between project directories by auditing and safely updating local Codex session metadata, session_index.jsonl, workspace mappings, and when needed Codex Desktop UI state.
metadata:
  short-description: Move Codex conversations between project folders
  version: v1.1.0
  updated: 2026-06-11
---

# Codex Session Mover

Use this skill when the user wants Codex conversation history to appear under a different local project directory.

This skill edits Codex local state, not project source code. Treat it as careful maintenance.

## What It Moves

Codex conversations may be represented in several local layers:

```text
~/.codex/
  sessions/**/*.jsonl
  session_index.jsonl
  cap_sid
  .codex-global-state.json
  state_*.sqlite
```

The bundled script handles the core session files:

1. Find candidate session JSONL files.
2. Back up session files and indexes.
3. Update session metadata `cwd`.
4. Update `session_index.jsonl` when matching entries exist.
5. Update `cap_sid` workspace mappings when present.

Codex Desktop UI grouping can also depend on `.codex-global-state.json` and `state_*.sqlite`. If the session file is correct but the sidebar still shows the conversation in the old project or projectless list, inspect and repair those layers too.

## Safety Rules

- Never bulk-migrate all sessions unless the user explicitly asks.
- Prefer `audit` first, then `move --apply`.
- If unsure which sessions are intended, show the audit result and ask the user.
- Treat duplicate or inconsistent ids as high risk. A JSONL file can contain an internal `session_id` that differs from the visible thread id in its filename or Codex app list.
- When moving one visible conversation, prefer the exact JSONL `path` from audit, not a partial id.
- Do not use a session id or substring for `--session` when audit shows ambiguity.
- Always create a backup before applying changes.
- Do not delete unrelated old mappings unless the user explicitly asks.
- Do not edit project source files while moving sessions.
- For Windows paths containing Chinese characters, `©`, or other non-ASCII characters, force UTF-8 output or use escaped strings. Avoid raw non-ASCII path text through GBK-sensitive PowerShell/Python/Node pipes.
- If Codex Desktop is running, it may write stale sidebar state back to disk when it exits. For `.codex-global-state.json` or SQLite UI repairs, prefer an after-exit watcher or ask the user to fully quit Codex before final edits.

## Standard Workflow

1. Confirm the source project directory and target project directory.
2. Confirm whether the target shown in the Codex sidebar is a display label or the actual filesystem path.
3. Run `audit`.
4. If exactly one candidate is intended, run `move` once without `--apply`.
5. Apply with the exact JSONL file path.
6. Verify the script output:
   - backup folder
   - selected JSONL path
   - old cwd and new cwd
   - session file replacement count
   - whether `session_index.jsonl` or `cap_sid` changed
7. Use Codex app thread tools when available to verify the moved thread reports the target `cwd`.
8. If the Codex Desktop sidebar still shows the old grouping, run the Desktop UI state checks below.

## Commands

Use the bundled script:

```text
python scripts/session_mover.py audit --from-cwd <old-project> --to-cwd <new-project>
python scripts/session_mover.py move --from-cwd <old-project> --to-cwd <new-project> --session <jsonl-path> --apply
```

Useful options:

```text
--codex-home <path>     Override Codex home. Defaults to %CODEX_HOME% or ~/.codex.
--query <text>          Filter candidate sessions by thread/title/text.
--recent <N>            Limit audit output to recent sessions.
--session <id-or-path>  Move one session by exact JSONL path or unique id/name substring.
--all-matching          Move every audited session matching from-cwd/query.
--apply                 Actually write changes.
```

`move` is a dry run by default. Omit `--apply` to preview changes.

On Windows, set UTF-8 for Python output when paths may contain non-ASCII characters:

```powershell
$env:PYTHONIOENCODING = "utf-8"
python scripts/session_mover.py audit --from-cwd "<old>" --to-cwd "<new>"
```

## Desktop UI State Checks

Use this section only when session files are moved but Codex Desktop sidebar grouping is still wrong.

Check the app-level thread list when tools are available:

```text
list_threads(query=<thread title>)
```

If the app-level `cwd` is correct but the sidebar remains wrong, inspect `.codex-global-state.json` for the thread id:

```text
projectless-thread-ids
thread-workspace-root-hints
thread-projectless-output-directories
electron-saved-workspace-roots
project-order
electron-workspace-root-labels
```

For a project-scoped conversation, stale entries in these places can keep the thread under the projectless "Chats" section. A correct project conversation usually should not have projectless-thread or projectless-output entries.

Also inspect `state_*.sqlite`, table `threads`, column `cwd`. Existing project conversations often use Windows extended path format:

```text
\\?\F:\path\to\project
```

If you repair SQLite manually:

- Back up the SQLite file first.
- Update only the intended `threads.id`.
- Clear repo-specific git fields if moving to a non-repo skill folder and those fields came from the old project.
- Re-read the row and verify the exact Unicode path survived.

## Running Codex Caveat

If Codex is currently open, direct edits to `.codex-global-state.json` can appear successful and then revert after restart because the running app writes its in-memory state on exit.

Reliable options:

- Ask the user to fully quit Codex, then edit the state files.
- Or start a small after-exit repair process that waits for Codex processes to exit, then applies the backed-up state repair.

Use this only for the specific thread being moved. Do not run broad state rewrites.

## Reporting

After a successful move, report:

- source cwd
- target cwd
- moved JSONL file
- backup folder
- whether session JSONL, `session_index.jsonl`, `cap_sid`, `.codex-global-state.json`, or `state_*.sqlite` were touched
- whether a restart or after-exit repair is still required

## Examples

Audit a project:

```text
python scripts/session_mover.py audit ^
  --from-cwd "C:\Users\Administrator\Documents\Codex\2026-06-10\new-chat" ^
  --to-cwd "F:\cursor project\project-name"
```

Move one audited session by exact JSONL path:

```text
python scripts/session_mover.py move ^
  --from-cwd "C:\Users\Administrator\Documents\Codex\2026-06-10\new-chat" ^
  --to-cwd "F:\cursor project\project-name" ^
  --session "C:\Users\Administrator\.codex\sessions\2026\06\10\rollout-2026-06-10T15-58-10-019eb089-f0ad-7a53-9ae8-38c59d06fba4.jsonl" ^
  --apply
```

Move by id only after audit proves the id uniquely identifies one file:

```text
python scripts/session_mover.py move ^
  --from-cwd "<old-project>" ^
  --to-cwd "<new-project>" ^
  --session 019e3a27 ^
  --apply
```
