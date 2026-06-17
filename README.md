<div align="center">

## Codex Session Mover

Move Codex Desktop / CLI conversation history from one local project directory to another.

<sub>Audit -> Backup -> Move -> Verify</sub>

<br>

<p>
  <img src="https://img.shields.io/badge/Codex-Skill-2563eb?style=flat" />
  <img src="https://img.shields.io/badge/Version-v1.1.0-14b8a6?style=flat" />
  <img src="https://img.shields.io/badge/Focus-Session%20Migration-7c3aed?style=flat" />
</p>

</div>

`codex-session-mover` helps maintain local Codex conversation ownership. It audits candidate sessions, backs up local state, updates session metadata, and documents the extra Codex Desktop state layers that may affect sidebar grouping.

## What It Helps With

- Find Codex conversations that belong to an old project directory.
- Move a specific conversation to a new project directory.
- Update session JSONL `cwd` metadata.
- Update `session_index.jsonl` and `cap_sid` when matching entries exist.
- Diagnose Codex Desktop sidebar mismatches involving `.codex-global-state.json` and `state_*.sqlite`.
- Avoid path corruption on Windows when project names contain Chinese characters or symbols such as `©`.

## Safety Model

- Audit before applying.
- Prefer exact session JSONL paths over fuzzy ids.
- Back up before writing.
- Treat duplicate or inconsistent ids as risky.
- Verify both file state and app-visible `cwd` when possible.
- If Codex Desktop is running and sidebar state keeps reverting, repair after the app fully exits.

## Layout

```text
SKILL.md
scripts/session_mover.py
agents/
.foundation/
```

## Notes

This skill edits local Codex state, not project source code. Use it carefully, especially when moving active conversations or conversations between renamed projects.
