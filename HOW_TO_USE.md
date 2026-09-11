# How to use this template

## Starting a new project from it
1. Copy this whole `system_workflow_template` folder into your new project folder (or copy its contents into an existing project's root). Keep the `.claude/agents/goal-evaluator.md` path exactly as-is — that path is how Claude Code finds it.
2. Run `scripts/setup-venv.ps1` right away, before any implementation work starts — this creates an empty, isolated `.venv` for the project immediately, not only once some task happens to need an external tool. See CLAUDE.md's Environment section for why this has to happen upfront rather than reactively.
3. Rename/fill in AGENT_LOG.md's first task line, if you want to start with one already known.
4. Optionally add `ARCHITECTURE.md` and `CONTRACTS.md` next to CLAUDE.md if the project needs enforced structure (Pattern B from your original notes). Skip them for small projects (Pattern A).
5. `CODE_MAP.md` starts empty (just its header/format). Leave it as-is until the project has real code — the lead agent fills it in as non-obvious implementation details show up, per CLAUDE.md's zero-comments rule.

## Starting the session (desktop app or VS Code, no terminal needed)
Open the project folder, start a chat, and say something like:

> "Read CLAUDE.md and AGENT_LOG.md. Propose an architecture and task plan for [describe the project], then stop and wait for my approval."

## Running something "until it's actually done"
State the condition, then ask for the loop:

> "/loop — keep going until pytest exits 0 and there are no lint errors."

Because CLAUDE.md's Completion Loop rule is loaded, the lead agent will call `goal-evaluator` itself before ever telling you it's finished — you don't need to invoke the evaluator by name.

## The rest of `.claude/`
- `settings.json` — permission defaults: read-only tools allowed freely, edits/writes/shell ask first, a few destructive git/shell patterns denied outright even if you say yes by accident.
- `skills/` — empty on purpose; add a skill folder only once you notice yourself repeating the same instructions across sessions for this project.
- `workflows/dimension-review.js` — a ready-made template for "check this content against several independent concerns, verify each finding, keep only the real ones." Ask the lead agent to run it by name when a task fits that shape (e.g. "run dimension-review on this draft for tone, factual accuracy, and length"). Copy it as a starting point for other fixed multi-step sequences.

## Code comments and CODE_MAP.md
This template carries a hard rule (CLAUDE.md) against any comments in source code once the project has real implementation files. Anything genuinely non-obvious that would otherwise justify a comment goes into `CODE_MAP.md` instead, in its Location / Why-invariant-gotcha / Spec cross-reference format; an actual product/business decision found along the way gets promoted into ARCHITECTURE.md's decision log (or wherever this project tracks decisions), not left in CODE_MAP.md. This exists because a prior project let the same explanations live in both its spec `.md` files and its inline code comments, driving comment density to roughly a third of that codebase before anyone noticed — CODE_MAP.md is the single place that content belongs instead.

## `.venv` and external tools
`scripts/setup-venv.ps1` creates an empty, isolated `.venv` for the project. Run it immediately when starting a new project (step 2 above), not only once a task turns out to need something. Never install a package/tool system-wide on this device — everything a task needs (a Python package, a headless browser, an isolated Node.js via `nodeenv`) goes into that `.venv` instead, installed only as each task actually needs it.

## What you never have to do
- Never write a Workflow script by hand for a new shape of task — the AI can create and save one here itself when a task has independent sub-pieces.
- Never install anything system-wide, and never manually remember to create a venv — the lead agent creates and uses the project's own `.venv` per CLAUDE.md's Environment section.
