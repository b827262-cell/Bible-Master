---
name: herdr-freebuff-dispatch
metadata:
  version: "2.0.0"
  requires:
    bins: ["herdr-core", "herdr-app", "python3"]
description: >-
  Dispatch a prompt to a Freebuff CLI session running inside a Herdr terminal, then verify
  completion from Freebuff's own chat store. Use when asked to send work to Freebuff, to check
  whether Freebuff finished, or when Freebuff appears to ignore Enter. Covers dynamic terminal
  discovery, tab selection before pane focus, automatic submission via `herdr-core send`,
  session-scoped completion verification, duplicate/concurrency guards, and acceptance rules.
  Triggers: freebuff, Herdr dispatch, t7 integration, "Freebuff did not respond", "Enter does
  nothing in Freebuff".
---

# Freebuff dispatch over Herdr

## 1. Purpose

Freebuff is an interactive TUI coding agent. It has no headless mode and no Agent Client
Protocol support, so it can only be driven through its terminal. This skill defines the only
supported way to hand it work and to decide whether that work is done.

The verified properties of the transport are:

| Fact | Consequence |
| --- | --- |
| `Enter` submits the prompt | A plain carriage return is the send key |
| `Ctrl+J` and `Opt+Enter` insert a newline | Never use them as "send" |
| `herdr-core send` pastes text and presses Enter | One call submits; do not press Enter again |
| Herdr does not register Freebuff as an agent | `turn` is always 0 and `status` is always null |
| Freebuff writes its own chat store | Completion must be read from that store, not from Herdr |
| Focusing a terminal in a non-active tab reverts | Select the tab first, then focus the pane |

## 2. Prerequisites

- `herdr-core` and `herdr-app` are on `PATH` and share the same running Herdr session.
- A Freebuff CLI is already running inside a Herdr terminal. This skill never starts Freebuff.
- The dispatching user can read `~/.config/manicode/` (Freebuff config and chat store).
- Freebuff quota is time-based. Assume every dispatch costs something.

## 3. Environment discovery

Record these before dispatching, because none of them may be assumed:

```bash
hostname
pwd
herdr-core --version
herdr-app --version
freebuff --version
herdr-core ls --json          # live terminals and their agent names
herdr-core get <terminal> --json   # foreground.argv, cwd, labels
herdr-app ls                  # tabs and panes as the window sees them
```

Identify Freebuff by the **basename** of the foreground argv (for example
`["node", ".../freebuff"]`). Do not match a substring of the whole command line: a terminal
running `tail freebuff.log` would otherwise be mistaken for an agent.

## 4. Dynamic terminal identification

Rules, in order:

1. If `--terminal` is given, verify its foreground process is Freebuff. Reject it otherwise.
2. Otherwise scan all live terminals and collect every Freebuff match.
3. Zero matches: fail with a precondition error. Never start a new instance to "fix" this.
4. More than one match: fail as ambiguous and list them. Do not pick one.

A requested target terminal (for example `t7`) is a **hint only**. Terminal addresses are
allocated by Herdr and are not stable across restarts or machines. When the requested terminal
does not exist or is not Freebuff, report `expected_terminal` and `detected_terminal`
separately and mark the run as a mismatch instead of silently proceeding as if it matched.

## 5. Integration procedure

The repository tool `bible-site/tools/freebuff_dispatch.py` implements all of the following.
Reproduce it manually only when the tool is unavailable.

```bash
# 0. Dry run: resolves terminal, tab, pane, chat store, and idle state. Sends nothing.
python3 bible-site/tools/freebuff_dispatch.py --dry-run

# 1. Dispatch (single call, no extra Enter)
python3 bible-site/tools/freebuff_dispatch.py \
  --terminal t7 \
  --text "Reply exactly FREEBUFF_T7_OK" \
  --timeout 60 \
  --json
```

Manual equivalent:

```bash
TAB_ID=$(herdr-app ls | jq -r '.spaces[].tabs[] | select(.terminals[].terminal=="<t>") | .id')
PANE_ID=$(herdr-app ls | jq -r '.spaces[].tabs[] | select(.terminals[].terminal=="<t>") | .terminals[].pane')

herdr-app do tab.select --id "$TAB_ID"
herdr-app do pane.focus --terminal "<t>"
herdr-app status                      # focused_pane must equal PANE_ID
herdr-core read --lines 0 "<t>"       # input box must show the placeholder, no busy text
herdr-core send "<t>" "your prompt"   # this submits; do not press Enter afterwards
```

## 6. Tab selection and pane focus

- Always `tab.select` **before** `pane.focus`. Focusing a pane whose tab is not selected is
  reverted within about a second, after which every keystroke is silently dropped.
- Confirm focus through `herdr-app status`, not through the cursor glyph. The block cursor
  blinks, so its absence proves nothing.
- Read screens only with `herdr-core read --lines 0`. Scrolling changes the rendered viewport
  and makes state harder to compare.

## 7. Automatic submission

`herdr-core send` is paste plus Enter. It is the only submission step. Two cautions:

- Its exit code proves the command ran, not that the prompt was submitted. It reports
  `"status": null, "turn": 0` for Freebuff.
- Do not add a second Enter. An empty submit can create a blank turn and consume quota.

## 8. Completion verification from the chat store

Freebuff writes `~/.config/manicode/projects/<project>/chats/<session>/chat-messages.json`.

Resolve the store for the session, never by "newest file on disk":

1. Read the terminal's `cwd` from `herdr-core get`.
2. Use `projects/<basename of cwd>/chats/*/chat-messages.json`, newest session first.
3. If that project directory does not exist, accept a single recent session (last 24 h) with a
   warning; if more than one candidate exists, fail instead of guessing.

Accept a run only when all of the following hold:

- a `variant == "user"` message whose normalised text equals the prompt just sent;
- an `variant == "ai"` message that appears **after** that user message in the list;
- that assistant message has `isComplete == true` (when the field exists);
- both timestamps are later than the dispatch start time. Message ids embed epoch
  milliseconds (`user-<ms>`, `ai-<ms>-<hash>`), which is the most precise clock available.

Anything else is `unverified`. A reply that predates the dispatch is a stale reply and must
never be reported as this run's result.

## 9. Timeout, duplicates, concurrency

- **Timeout**: on expiry report `unverified` and stop. Do not retry automatically: the original
  prompt may already have been submitted, and a retry would double-charge the quota.
- **Duplicate**: keep a hash of the last prompt per terminal and refuse an identical prompt
  within a short window (default 300 s) unless explicitly forced.
- **Concurrency**: take an exclusive lock file before focusing. If the holder is alive, refuse;
  if the holder is dead or the lock is older than its TTL, take it over.

## 10. Known limitations

- No headless mode and no ACP: the TUI must exist and stay open.
- `hc wait`, `turn`, and `status` are meaningless for Freebuff and must not gate completion.
- The chat store format is Freebuff's internal file; a Freebuff upgrade may change it. Verify
  the parser after any version bump.
- Reply quality is uneven: in one measured review, one of three findings was wrong and another
  cited a wrong line number. Treat output as advice, never as acceptance evidence.
- The free tier is time-limited and its model may be switched by the operator mid-session.
- `hc keys` cannot type `_`; use `send` (paste) when the prompt contains underscores.

## 11. Troubleshooting

| Symptom | Cause | Action |
| --- | --- | --- |
| Keystrokes have no effect | Pane focused without selecting its tab | `tab.select` then `pane.focus`, re-check `status` |
| `send` returns 0 but nothing appears | Input box not focused, or a modal/help overlay is open | Re-focus, `Esc` to close overlays, verify placeholder |
| Cursor glyph missing | Normal blinking | Ignore; use `focused_pane` |
| Reply never arrives | Session finished, quota exhausted, or wrong chat store | Check the store path and its mtime; do not retry blindly |
| Two Freebuff terminals found | Duplicate instance | Stop; decide manually which one is the integration target |
| Prompt text contains `_` | `hc keys` limitation | Use `send`, which pastes verbatim |

## 12. Smoke test and acceptance

Smoke test (run once per integration, never repeatedly):

```bash
python3 bible-site/tools/freebuff_dispatch.py --text "Reply exactly <TOKEN>" --timeout 60 --json
```

Acceptance requires:

1. `verified: true`, `submitted: "confirmed"`, and `reply` equal to `<TOKEN>`;
2. the input box empty again (`herdr-core read --lines 0` shows the placeholder);
3. `git status --short` unchanged, proving the agent modified no files when the task was
   read-only.

Transport success, confirmed submission, completed response, and human acceptance are four
different things. The tool only reports the first three. Human or reviewer acceptance is
always required and is never inferred from exit code 0.

## 13. Adapting to another Linux machine

1. Re-run the discovery block in section 3 and record the versions; do not copy them.
2. Do not copy terminal addresses, tab ids, pane ids, pids, or session directory names. The
   tool derives all of them at runtime.
3. Confirm the chat store root still lives under `~/.config/manicode/projects`. If Freebuff is
   configured elsewhere, point `FREEBUFF_DISPATCH_CHAT_ROOT` at it.
4. Confirm that `Enter` submits and that `Ctrl+J` / `Opt+Enter` insert newlines on the installed
   version. If that changes, stop and re-derive the send key before dispatching.
5. Run the mocked checks first, then one real smoke test:
   `python3 bible-site/tests/freebuff_dispatch_checks.py`.
6. Update `roles.yml` (`freebuff.dispatch.terminal`) with the machine's expected terminal, and
   keep `manual: true` until the integration is reviewed independently.
