# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SSH Remote — a desktop SSH client (Tkinter/ttkbootstrap), similar to PuTTY: a saved-session manager
in a side panel plus a tabbed terminal area, each tab holding one live SSH connection. Everything is
local/offline; there is no backend service.

## Commands

```bash
# setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# run the app
python run.py

# bulk-import sessions from scripts/import_sessions.py's hardcoded ENTRIES list
python scripts/import_sessions.py
```

There is no test suite, linter, or build step configured in this repo.

## Architecture

Single-package app under `ssh_remote/`, run via `run.py` -> `ssh_remote.app.main()`.

- **`app.py`** — the entire UI: `MainWindow` (the `ttk.Window` root) and `SessionDialog` (create/edit
  form). `MainWindow` owns a `ttk.Treeview` on the left (categories as parent nodes, sessions as
  children, node ids prefixed `cat:`/`sess:`) and a `ttk.Notebook` on the right where each tab wraps
  one `SSHTerminalFrame`. Session-tree drag-and-drop (multi-select, drag onto a category to
  reassign) is hand-rolled on top of raw `ButtonPress-1`/`B1-Motion`/`ButtonRelease-1` bindings
  because Treeview's default press handler collapses multi-selection immediately — see the comments
  around `_on_drag_start` before touching selection/drag behavior.
- **`session_manager.py`** — `Session` dataclass + `SessionManager` CRUD, persisted as JSON to
  `~/.ssh_remote/sessions.json`. `Session.password`/`key_passphrase` are properties that
  transparently encrypt/decrypt through `crypto.py`; only the `*_enc` fields are ever serialized.
- **`category_manager.py`** — same CRUD pattern for `Category`, persisted to
  `~/.ssh_remote/categories.json`. Sessions reference a category by `category_id`; `""` means
  uncategorized (rendered as the "Sem categoria" tree root in `app.py`).
- **`crypto.py`** — Fernet symmetric encryption for saved passwords/passphrases. Generates/loads
  `~/.ssh_remote/secret.key` (chmod 600) on first use; `~/.ssh_remote/` itself is chmod 700. This key
  file must travel with `sessions.json` when copying config to another machine, or saved credentials
  become undecryptable.
- **`terminal.py`** — `SSHTerminalFrame`: owns a `paramiko.SSHClient`, connects on a background
  thread (`_connect_and_read`), and streams the shell channel into a `tk.Text` widget after stripping
  ANSI escape codes via `ANSI_ESCAPE_RE`. This is a simple line-oriented emulation, not a full VT100 —
  fullscreen/cursor-heavy programs (`top`, `vim`, `htop`) won't render correctly, but standard shell
  commands work fine. Keystrokes are mapped through `SPECIAL_KEYS` and sent directly over the
  channel; there's no local echo/line-editing. All UI mutation from the background thread goes
  through `self.after(0, ...)` (see `_append`).
- **`dialogs.py`** — custom `ttk.Toplevel`-based info/confirm/prompt dialogs, deliberately *not*
  using `ttkbootstrap.dialogs` (`Messagebox`/`Querybox`): those render empty/content-less under this
  project's KDE/KWin environment because of an iconify/withdraw/deiconify cycle KWin doesn't honor.
  Keep new dialogs on the plain `ttk.Toplevel` pattern used here and in `SessionDialog`.
- **`preferences.py`** — small JSON-backed key/value store (`~/.ssh_remote/preferences.json`),
  currently just `dark_mode`.
- **`scripts/import_sessions.py`** — standalone batch importer that seeds sessions in bulk; matches
  existing sessions by `(host, username)` to avoid duplicates. Reads username/password/port/entries
  from `scripts/import_sessions_data.json`, which holds real credentials/IPs and is gitignored — only
  `scripts/import_sessions_data.example.json` (a template with placeholder values) is committed. When
  adding new bulk-import data, put it in the gitignored JSON, never back in the script.

## Data layout

All persistent state lives under `~/.ssh_remote/` (not in the repo):
- `sessions.json`, `categories.json`, `preferences.json` — plain JSON, restricted to the owning user.
- `secret.key` — the Fernet key used to encrypt/decrypt saved passwords and key passphrases.
