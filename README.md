# RBI Scrum Timer

Desktop standup timer for the RBI team at Netskope. Manages per-participant speaking time, integrates with Jira to show active sprint tasks, and persists session history with charts.

---

## Requirements

- **macOS** (tested on macOS 13+)
- **Python 3.10+** (3.14 recommended — the project ships a `.venv` created with the system Python)
- **Atlassian account** with API token (for Jira integration — optional at runtime)

---

## Installation

### 1. Clone the repository

```bash
git clone <repo-url>
cd rbi-scrum-time
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Dependencies:

| Package | Purpose |
|---|---|
| `customtkinter>=5.2.2` | Modern UI framework (dark mode, macOS native feel) |
| `matplotlib>=3.9.0` | Session history charts in the Stats tab |
| `mplcursors>=0.5` | Interactive tooltips on charts |
| `Pillow>=10.0.0` | Circular avatar rendering from Jira profile pictures |

### 4. Run

```bash
source .venv/bin/activate
python main.py
```

The database (`data/scrum.db`) is created automatically on first launch — no manual setup needed.

---

## Jira Integration (optional)

The app works without Jira credentials, but the meeting tab will show a "No Jira account ID" message instead of sprint tasks.

To enable Jira:

1. Generate an API token at [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Open the **Settings** tab in the app
3. Enter your **Atlassian Email** and **API Token** → click **Save** for each
4. Paste your **Board Filter URL** (e.g. `https://netskope.atlassian.net/jira/software/c/projects/ENG/boards/14955?label=polaris-squad`) → click **Save**
5. Click **Test connection** to verify
6. Click **Refresh Users** to sync team members from the board

Alternatively, set credentials via shell environment (takes precedence over stored values):

```bash
export ATLASSIAN_EMAIL="your@email.com"
export ATLASSIAN_API_TOKEN="ATATT3x…"
export JIRA_BOARD_URL="https://netskope.atlassian.net/jira/software/c/projects/ENG/boards/14955?label=polaris-squad"
```

---

## First-time setup (no existing participants)

1. Launch the app
2. Go to **Settings** → configure Atlassian credentials + Board Filter URL
3. Click **Refresh Users** → tick the members you want to add → click **Save Selected**
4. Alternatively, go to **Participants** → click **+ New** to add participants manually (name, Jira Account ID, avatar URL)
5. Go to **Participants** → select people from "All Participants" and move them to "In Today's Meeting" using `→` or `»`
6. Go to **Meeting** → click **▶ Start**

---

## Features

### Meeting tab
- Randomly ordered participant queue (non-managers first, then Managers & +)
- Per-participant timer with color-coded status dot (green → yellow → red)
- Bell alert in the last 10 seconds of each turn
- Current speaker shown with Jira avatar (if synced) or food icon
- **Open Tasks** column: active sprint issues for the current speaker
- **Closed Tasks** column: issues completed this sprint

### Participants tab
- Manage the permanent participant list (add, edit, delete)
- Configure meeting name, duration, bell settings
- Select attendees for today's meeting

### Stats tab
- Meeting duration history chart (planned vs actual)
- Per-session per-participant time breakdown
- Delete individual sessions

### Settings tab
- Atlassian credentials management (masked, stored locally in DB)
- Board Filter URL for team sync
- Refresh Users: fetches team members from the board's active sprint with avatars
- Add/mark as Manager before saving

---

## Data storage

All data is stored locally in `data/scrum.db` (SQLite). The database is created automatically on first launch.

- **Participants** — name, Jira account ID, avatar path, manager flag
- **Meeting config** — name, duration, bell settings
- **Sessions** — date, planned/actual duration, per-participant times
- **Tokens** — Atlassian credentials (stored locally, never sent anywhere except the Jira API)
- **Avatars** — cached in `data/avatars/<account_id>.png`

> **Note:** `data/scrum.db` is excluded from git (see `.gitignore`). Never commit it — it may contain API tokens and personal data.

---

## Project structure

```
rbi-scrum-time/
├── main.py                  # Entry point — loads env, launches app
├── requirements.txt         # Python dependencies
├── app/
│   ├── db.py                # SQLite CRUD (auto-creates DB + tables on first run)
│   ├── meeting.py           # MeetingTimer state machine
│   ├── models.py            # Dataclasses: Participant, MeetingConfig, etc.
│   ├── bell.py              # Bell chime generator (stdlib only, afplay)
│   ├── jira_client.py       # Jira API: board members, sprint issues (async threads)
│   └── ui/
│       ├── app_window.py    # Root window, tab layout
│       ├── meeting_tab.py   # 4-column meeting view
│       ├── participants_tab.py
│       ├── stats_tab.py
│       ├── settings_tab.py
│       ├── help_tab.py
│       ├── dialogs.py       # Custom CTk popups (replaces tkinter.messagebox)
│       └── scroll_fix.py    # Trackpad scroll fix for macOS Tk9
├── data/                    # Created automatically on first run
│   ├── scrum.db             # SQLite database (gitignored)
│   └── avatars/             # Cached Jira profile pictures
└── assets/
    └── AppIcon.icns         # macOS app icon
```

---

## Troubleshooting

**App doesn't start / import errors**
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

**Jira tasks not loading**
- Check credentials in Settings → Test connection
- Verify the Board Filter URL includes a `?label=` param
- Make sure participants have a Jira Account ID set (Settings → Refresh Users, or Participants → Edit)

**Avatars not showing**
- Avatars are downloaded when you do Settings → Refresh Users
- They are cached in `data/avatars/` — delete the folder to re-download

**Database issues**
- Delete `data/scrum.db` to start fresh — it will be recreated automatically
