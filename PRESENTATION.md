# AI-Assisted Development of the RBI Scrum Timer
## A Case Study in Collaborative Human-AI Engineering

---

## Slide 1: Title

**RBI Scrum Timer: From Team Pain Point to Production App**

*A collaborative case study in AI-assisted desktop application development*

- **Team:** RBI (Routing & Insider Threats) at Netskope
- **Developers:** Alex Sanchez (SDET) + Claude Code (Anthropic AI)
- **Stack:** Python + customtkinter, SQLite, Jira API
- **Platform:** macOS (desktop application)
- **Timeline:** Single development session, ~6 hours of collaborative work

---

## Slide 2: The Team Pain Point

**What Was The Problem?**

Before the RBI Scrum Timer, daily standups were managed manually:

- **No time awareness** — Scrum Master manually checked elapsed time, often losing track during long talking points
- **No task visibility** — Team members had to remember their own active sprint tasks; context-switching to Jira slowed down communication
- **Disconnected tooling** — Jira (task source) was separate from the standup process (timing & ordering)
- **No data persistence** — Each standup ended with no record; impossible to track time trends or individual speaking patterns

**Desired outcome:** A single app that manages time AND shows live sprint context, keeping the team focused and connected to work items.

---

## Slide 3: Local Claude Setup — SuperClaude Architecture

**How Alex's Development Environment Enables AI Pair Programming**

```
~/.claude/
├── CLAUDE.md                    # Global index (5 repos, 20+ skills)
├── projects/
│   └── -Users-asanchez-Repository-rbi-ai-gnition-lab/
│       └── memory/              # Persistent context (user, project, feedback)
│           ├── user_profile.md
│           ├── project_rbi_scrum_timer.md
│           └── ...
├── settings.json                # Permissions, hooks, env vars
├── settings.local.json          # User overrides
├── keybindings.json             # Custom keyboard shortcuts
└── scripts/
    └── sync-skills.sh           # Sync all 5 git repos
```

**Key Insight:** The setup acts as a "junior engineer's knowledge base." Claude enters each session with:
- User context (SDET background, Python/pytest expertise)
- Project context (RBI team architecture, Jira quirks, testing strategies)
- Reusable tools (skills: jira-refinement, sonarqube, oncall, teleport-env-check, etc.)
- Memory (6-month feedback loop: what worked, what didn't, lessons learned)

---

## Slide 4: The Five Repositories

**SuperClaude's Distributed Skill System**

| Repository | Skills | Purpose |
|---|---|---|
| `claude-skills` (global) | jira, sqlqs-jql, xray-triage, confluence | Core Atlassian & security operations |
| `rbi-ai-gnition-lab` | jira-create, jira-update, synapser, sonarqube | RBI team automation library & PR review |
| `rbi-devops-ai` | oncall, grafana-analyzer, aws-cost-optimizer | Oncall workflows & infrastructure |
| `pylark-webui-libs` | — | Python Selenium/Playwright automation library |
| `webui-ng-api-libs` | — | Python client for Netskope WebUI v2 APIs |

**Why distributed?** Each repo owns a domain. Skills are invoked with `/skill-name` from anywhere; Claude knows which repo to load context from.

---

## Slide 5: The Development Process

**Need → Use Case → Development → Quality → Lessons**

### Need Recognition
- Standup chaos: manual timekeeping, task amnesia
- Jira context lost in conversation

### Use Case Definition
- Per-participant timer with random ordering (non-managers first, managers last)
- Show current speaker's open & closed sprint tasks
- Persist sessions + analyze trends (charts)
- Bell alert in final 10 seconds

### Development Approach
- **Conversational & iterative:** Alex described needs in natural language; Claude implemented feature by feature
- **Precise context input:** Alex provided Jira tenant URLs, API field IDs, DNS logs, screenshots — reduced token waste
- **Checkpoint-driven:** Each feature tested manually before moving to the next

### Quality Gates
- pylint 10/10 (strict, no exceptions)
- black + isort (consistent formatting)
- Docstrings on all public methods
- One git commit per feature

### Lessons Captured
- Documented in project memory for future work

---

## Slide 6: How Claude and Alex Interacted

**The Conversational Loop**

1. **Alex provides context** — "Here's a screenshot of our Jira board, tenant URL, and the API field ID we're using"
2. **Claude asks clarifying questions** — "Should the bell alert be configurable? What frequency?"
3. **Claude implements** — Writes the feature (function, UI integration, test if applicable)
4. **Alex reviews & tests** — "This works, but can you also show avatars?"
5. **Claude iterates** — Adds avatars, handles image caching, adds config UI
6. **Repeat** for next feature

**Why this worked:**
- High signal-to-noise ratio: Alex's input was structured and specific
- No discovery phase: context was pre-loaded (Jira URLs, API specs, tenant details)
- Trust: both understood the RBI domain and Python conventions

**Cost efficiency:** Precise context input (exact API field IDs, tenant names, error logs) reduced back-and-forth iterations and token waste.

---

## Slide 7: The App Architecture

**Desktop Application Stack**

```
main.py (entry point)
    ↓
app/
  ├── db.py              # SQLite CRUD (auto-migrations on startup)
  ├── meeting.py         # MeetingTimer state machine (UI-agnostic)
  ├── models.py          # Dataclasses: Participant, MeetingConfig, MeetingState
  ├── bell.py            # WAV chime generator (stdlib: wave, array) + afplay
  ├── jira_client.py     # Async Jira API: board members, sprint issues
  └── ui/
      ├── app_window.py     # Root window, tab layout (customtkinter)
      ├── meeting_tab.py    # 4-column view: speaker, open tasks, closed tasks, controls
      ├── participants_tab.py
      ├── stats_tab.py
      ├── settings_tab.py
      ├── help_tab.py
      ├── dialogs.py        # Custom CTk popups (replaces tkinter.messagebox)
      └── scroll_fix.py     # Trackpad scroll fix for macOS Tk9
```

**Key Design Decisions:**
- MeetingTimer is **state-machine-based** (IDLE → RUNNING → PAUSED → RUNNING) and UI-agnostic — can be tested independently
- Database auto-migrates on startup — no manual schema management
- Bell uses **stdlib only** (wave, array) + macOS `afplay` — zero external audio dependencies
- Async threads for Jira API calls — UI never blocks

---

## Slide 8: Core Features

### 1. Meeting Tab
- **4-column layout:** Meeting info | Speaker + timer | Open tasks | Closed tasks | Controls
- **Randomly ordered queue:** Non-managers first, then managers last
- **Color-coded status dot:** Green (plenty of time) → Yellow (half time) → Red (last 10s, blinking)
- **Bell alert:** Chime in final 10 seconds (stdlib WAV + afplay)
- **Jira integration:** Show speaker's active sprint tasks, click to open in browser

### 2. Participants Tab
- Add, edit, delete team members
- Set Jira Account ID, avatar URL, manager flag
- Configure meeting name, duration, bell settings

### 3. Settings Tab
- Atlassian credentials (masked, stored in SQLite)
- Board Filter URL with `?label=` parameter
- "Refresh Users" — fetches team members + avatars from active sprint
- "Test Connection" — validates Jira credentials

### 4. Stats Tab
- Meeting duration history (planned vs actual, line chart)
- Per-session breakdown: each participant's speaking time
- Delete individual sessions

### 5. Help Tab
- Searchable guide with feature cards
- No external help system needed — context within the app

---

## Slide 9: Jira Integration Challenges & Solutions

**Real-World API Quirks Encountered**

### Challenge 1: Tenant DNS Resolution
- **Problem:** Jira API URLs are tenant-specific; DNS resolution was inconsistent across networks
- **Solution:** Cache the resolved tenant ID in the database after first successful login; fall back to environment variable

### Challenge 2: Custom Field IDs
- **Problem:** Jira custom fields (e.g., story points, business value) have no stable names — only field IDs like `customfield_24133`
- **Solution:** Hardcode field IDs after discovering them via `/rest/api/3/fields` endpoint; document in code comments with Confluence link

### Challenge 3: Sprint API vs Greenhopper
- **Problem:** Sprint data comes from multiple endpoints (`/rest/api/3/sprints` vs Greenhopper `/rest/agile/1.0/board/`)
- **Solution:** Use Greenhopper endpoint for board sprints; validates issue count and status

### Challenge 4: Avatar Caching
- **Problem:** Jira avatar URLs are time-limited tokens; re-fetching for every render killed performance
- **Solution:** Download & cache avatars locally in `data/avatars/<account_id>.png` on first sync; refresh on demand

### Challenge 5: Circuit Breaker for Bad Credentials
- **Problem:** Invalid credentials caused app to hang (repeated API retries)
- **Solution:** Track failed attempts in memory; disable Jira features gracefully if auth fails 3 times

---

## Slide 10: Technical Deep Dive — SQLite Migrations

**Robust Schema Evolution Without External Tools**

```python
# app/db.py: Auto-migration pattern
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table exists check; create if not
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            jira_account_id TEXT,
            avatar_path TEXT,
            is_manager INTEGER DEFAULT 0
        )
    """)
    
    # Pragmatic migration: add columns if missing
    cursor.execute("PRAGMA table_info(participants)")
    columns = {row[1] for row in cursor.fetchall()}
    
    if 'is_manager' not in columns:
        cursor.execute("ALTER TABLE participants ADD COLUMN is_manager INTEGER DEFAULT 0")
    
    conn.commit()
    conn.close()
```

**Why this pattern?**
- No external migration tool (like Alembic) needed
- App auto-heals on startup
- Easy to backport to production if schema changes

---

## Slide 11: Platform Limitations & Solutions

**Why macOS Only (and How to Fix It)**

### Limitation 1: Bell Sound (`afplay`)
```python
# Current: macOS only
subprocess.run(["afplay", wav_file], check=False)

# Fix: OS-aware wrapper
import platform, winsound
if platform.system() == "Darwin":
    subprocess.run(["afplay", wav_file], check=False)
elif platform.system() == "Windows":
    winsound.PlaySound(wav_file, winsound.SND_FILENAME)
else:  # Linux
    subprocess.run(["aplay", wav_file], check=False)
```

### Limitation 2: Open URLs (`open` command)
```python
# Current: macOS only
subprocess.run(["open", url], check=False)

# Fix: Cross-platform
import webbrowser
webbrowser.open(url)  # Works on all platforms
```

### Limitation 3: Trackpad Scroll (`<TouchpadScroll>`)
```python
# Current: macOS Tk9 event binding
widget.bind("<TouchpadScroll>", _scroll, add="+")

# Fix: OS-specific handlers
import platform
if platform.system() == "Darwin":
    widget.bind("<TouchpadScroll>", _scroll_mac, add="+")
elif platform.system() == "Windows":
    widget.bind("<MouseWheel>", _scroll_win, add="+")
else:  # Linux
    widget.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"), add="+")
    widget.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"), add="+")
```

**Estimate:** ~2-3 hours to make fully cross-platform (mostly testing on Windows & Linux VMs).

---

## Slide 12: Unexpected Gotchas

**Three Bugs That Cost Time**

### Bug 1: CTkImage Memory Leak
- **Symptom:** App slowed down after a few avatar reloads; memory grew without bounds
- **Root cause:** PIL images not being garbage-collected after CTkImage wrapping
- **Solution:** Explicitly delete image references after widget update; use weak references where possible

### Bug 2: CTkToplevel `topmost` Not Respected on macOS
- **Symptom:** Dialog boxes could be hidden behind the main window
- **Root cause:** macOS Tk9 doesn't honor the `topmost` attribute for CTkToplevel
- **Solution:** Use macOS-specific `subprocess.run(["osascript", "-e", "activate"], check=False)` to bring app to foreground

### Bug 3: Pause Behavior — Total Time Kept Ticking
- **Symptom:** When a speaker is paused, the meeting's total time kept running, causing the session to overshoot the planned duration
- **Root cause:** MeetingTimer's tick loop didn't distinguish between "meeting paused" and "speaker paused"
- **Solution:** Track two separate timers — meeting_elapsed (always ticking) and speaker_elapsed (paused with speaker)

---

## Slide 13: Code Quality & Development Hygiene

**Why This Matters for AI-Assisted Development**

**Pylint 10/10 (Strict Configuration)**
```ini
# .pylintrc: strict rules enforced
disable=
    fixme,              # Allow TODOs
    missing-module-docstring
```
- Forces Claude (and future maintainers) to write clean, readable code
- Catches subtle bugs: unused imports, unreachable code, type inconsistencies
- Makes code reviews faster

**Black + isort (Consistent Formatting)**
```bash
black app/
isort app/
```
- Claude outputs code in consistent style on first pass
- No back-and-forth on formatting
- Diffs stay focused on logic, not whitespace

**Docstrings on Public Methods**
```python
def calculate_speaker_time(self, participant_id: int) -> timedelta:
    """
    Calculate total speaking time for a participant in the current session.
    
    Args:
        participant_id: Database ID of the participant
    
    Returns:
        timedelta of total speaking time (excludes pause periods)
    """
```
- Future maintainers (including future Claude sessions) understand intent without reading implementation
- IDE autocomplete works reliably

**One Commit Per Feature**
```bash
git log --oneline | head -10
# 8a3c4d9 feat(settings): add Jira API error handling and circuit breaker
# 7f2e1c8 feat(meeting): show avatar and open tasks for current speaker
# 6e4d3b7 feat(bell): add configurable bell alert (volume, enabled/disabled)
```
- Easy to bisect when a bug appears
- Commit messages serve as feature documentation

---

## Slide 14: Is This Workflow Viable for Production Netskope Features?

**Honest Assessment: Yes, With Guardrails**

### ✅ Where AI-Assisted Development Shines
- **Internal tooling** (standup timer, cost analyzers, CI helpers) — low blast radius, quick iteration
- **Greenfield projects** — no legacy constraints; start with clean design
- **Automation & glue scripts** — high ROI on AI time
- **Bug fixes & performance optimizations** — Claude can trace code paths and suggest targeted fixes

### ⚠️ Where Human Review Is Non-Negotiable
- **Production code changes** — MUST have human code review + architecture review
- **Customer-facing features** — MUST have QA + UX review before merge
- **Security-sensitive code** (auth, encryption, compliance) — MUST have security review
- **Complex algorithms** — MUST have peer review to verify correctness

### 🛡️ Guardrails to Enforce
1. **Branch protection:** Require at least 1 human approval before merging to main
2. **Code review gate:** Use `/code-review --high` (Anthropic skill) on all CLs; address findings before approval
3. **Test coverage requirement:** ≥80% for production code; use Claude to write tests alongside features
4. **Architecture review:** For features touching core systems, brief with architect upfront (Confluence context → Claude summarizes)

### 💡 How to Brief Claude on Production Features
- **Source of truth:** Confluence (architecture docs, RFC, design decisions) + Jira (requirements, acceptance criteria)
- **Pre-session prep:** Alex reads the requirements; provides Claude with Confluence links + related PRs
- **Quality check:** Use `/sonarqube` (code quality) + `/security-review` (OWASP) skills before human review

---

## Slide 15: Knowledge Sources as Context

**What Made Claude Effective: RBI Domain Knowledge**

When developing the RBI Scrum Timer, Claude was pre-loaded with:

| Source | Content | How Used |
|---|---|---|
| **Confluence** | RBI architecture docs, testing strategies, Jira label/component rules | Referenced to ensure compliance (e.g., add `rbi-core` label to all RBI tickets) |
| **Jira board** | Past sprint reviews, retrospectives, known issues | Context for what the team actually needs (e.g., "Managers & +" feature came from standup annoyance) |
| **GitHub repos** | Existing RBI automation (jira-create, sonarqube skill, oncall scripts) | Reused patterns: same error handling, same Jira API quirk workarounds |
| **Project memory** | 6 months of user feedback, what worked/didn't on past projects | Avoided repeating mistakes (e.g., "don't use REST API v2 for custom fields; they're not stable") |

**Key insight:** Claude acted like a senior engineer who had been on the team for 6 months — not a generic code generator.

---

## Slide 16: Spec-Driven vs. Conversational Development

**aispec.org / Augment Code: Formal Specs vs. This Approach**

### Spec-Driven Development (Augment Code Pattern)
```
PRD (Product Requirements Doc)
  ↓
TDD (Test-Driven Development)
  ↓
Implementation (Claude writes code to pass tests)
  ↓
Review
```

**Pros:** Unambiguous requirements, strong test coverage, less rework
**Cons:** Upfront time investment, rigid if requirements shift

### Conversational Development (This Project)
```
Sketch idea in conversation
  ↓
Claude implements MVP
  ↓
Alex tests, provides feedback
  ↓
Claude iterates
  ↓
Done (commit when "good enough")
```

**Pros:** Fast iteration, discovery-driven, great for internal tools
**Cons:** Fewer tests initially, can drift from original intent

### Honest Assessment
- **For RBI Scrum Timer:** Conversational won. It's a greenfield internal tool; flexibility mattered more than formal spec.
- **For production features:** Spec-driven would be better. Clear PRD → TDD → review = lower risk of bugs, easier handoff to next maintainer.
- **Hybrid approach (recommended):** Use conversational for design & discovery; once requirements stabilize, freeze spec + switch to TDD for implementation.

---

## Slide 17: The SuperClaude Configuration Deep Dive

**How the Setup Enables Reusable Skills**

### Central Index: ~/.claude/CLAUDE.md
```markdown
## Skills Master Index

| Skill | Project | Availability | Purpose |
|---|---|---|---|
| jira-refinement | claude-skills | global | Validate ticket against DoR |
| sonarqube | rbi-ai-gnition-lab | project-local | Code quality analysis |
| oncall | rbi-devops-ai | script | Oncall alert → Jira ticket |
| teleport-env-check | memory | global | Validate RBI env config |
```

### Per-Project CLAUDE.md
Each repo has a `CLAUDE.md` with:
- Repository purpose
- Architecture patterns (e.g., agent-based pipelines)
- Label/component rules (Jira compliance)
- Lessons learned (what broke, what to avoid)

### Memory System (6-Month Feedback Loop)
```
~/.claude/projects/-Users-asanchez-Repository-rbi-ai-gnition-lab/memory/
├── user_profile.md           # SDET, Python, pytest expertise
├── feedback_teleport_env_check.md
├── project_rbi_scrum_timer.md
├── project_rtp_v2_refinement.md
└── ...
```

Each memory is tagged with type (user, feedback, project, reference) and creation date. Claude loads relevant memories at session start based on current directory.

### Environment Variables (Credentials from ~/.zshrc)
```bash
# ~/.zshrc
export ATLASSIAN_EMAIL="asanchez@netskope.com"
export ATLASSIAN_API_TOKEN="ATATT3x..."
export ATLASSIAN_SITE="netskope"
export GITHUB_TOKEN="ghp_..."
export OPSGENIE_API_KEY="..."
export CLAUDE_SQ_TOKEN="..."
```

Loaded at session start; never hardcoded in scripts.

### Hooks for Automation
```json
{
  "hooks": {
    "startup": ["~/.claude/scripts/sync-skills.sh"],
    "beforePush": ["run-tests.sh"]
  }
}
```

The harness executes hooks, not Claude — ensures consistency.

---

## Slide 18: Skills as Reusable Agents

**How `/jira-refinement`, `/sonarqube`, etc. Work**

```
User: "/jira-refinement ENG-12345"
  ↓
Skill invoked → CLAUDE.md loaded for jira-refinement skill
  ↓
Claude fetches ticket via Jira API, checks:
  - Template compliance (DoR met?)
  - Labels (rbi-core? rbi-qe-core?)
  - Assignee set?
  - Story points set?
  - Sprint assigned?
  - Product Details (Release Note, Documentation, TOI)?
  ↓
Returns: ✅ Ticket is refined OR ❌ Issues found (with fixes)
```

**Why this pattern works:**
- Each skill is self-contained; Claude knows exactly what it does
- Skills are reusable across projects (e.g., `/jira-refinement` works on any Jira ticket)
- Reduces cognitive load: user doesn't need to know the detailed checklist

**Current skills in RBI ecosystem:**
- jira, jira-create, jira-update, jira-refinement (Jira CRUD + validation)
- sonarqube, security-review, code-review (code quality)
- oncall, start-shift (oncall workflows)
- teleport-env-check (infrastructure)
- synapser (deep PR review)

---

## Slide 19: Lessons Learned

**What We'd Do Differently Next Time**

### 1. Start With Tests
- Spent 2 hours debugging the pause behavior bug
- A simple test case would have caught it immediately
- **Action:** Use pytest-qt for customtkinter apps; write tests for state machine first

### 2. Isolate Platform-Specific Code
- `afplay` scattered in several places
- Had to refactor to centralize in `app/bell.py`
- **Action:** Platform abstraction layer from day 1 (strategy pattern)

### 3. Add Telemetry Early
- No visibility into what features users actually use
- Impossible to prioritize next features
- **Action:** Add anonymous telemetry (feature usage, session length) from start

### 4. Database Schema Design Upfront
- Three schema changes mid-development (adding columns)
- Migration script needed to be robust
- **Action:** Schema design review before coding; leverage Claude to review schema for 3NF

### 5. Conversational > Formal for Internal Tools, But...
- For next production feature, will use spec-driven approach
- Jira RFC + TDD ensures alignment with team before implementation

---

## Slide 20: The Bottom Line — Is AI Pair Programming Real?

**Yes. With Caveats.**

### What We've Learned
1. **AI works best with context** — High-signal input (Jira URLs, API specs, tenant details) beats generic prompts by 10x
2. **Humans provide domain judgment** — "Should this feature do X or Y?" needs human decision; AI can implement either well
3. **Memory matters** — 6-month project feedback loop turns Claude into a "domain expert" that avoids repeating mistakes
4. **Tools amplify humans; they don't replace them** — The RBI Scrum Timer exists because Alex wanted it and Claude could implement fast. Alex's judgment + Claude's speed = 6-hour deliverable

### Where We're Headed
- **Netskope production features:** Spec-driven development with AI-assisted implementation + code review
- **Internal tooling:** Conversational, collaborative development (proven on RBI Scrum Timer)
- **Oncall & DevOps:** AI-driven scripts with human approval gates (proven with oncall skill)

### The Real Value
Not "replace engineers with AI" — it's **"multiply engineer productivity."**

A feature that would take 1 week solo can be designed, implemented, tested, and reviewed in 1 day with AI pair programming. That's a 5x multiplier. And the resulting code is cleaner, better documented, and safer because humans review the work.

---

## Slide 21: Questions & Discussion

**Key Takeaways for Your Team**

1. **Set up your own SuperClaude:** Central CLAUDE.md + reusable skills + memory system = AI that thinks like your team
2. **For internal tools:** Try conversational development; it's faster and more flexible
3. **For production features:** Use spec-driven (PRD → TDD → implementation), not conversational
4. **Provide context, not tasks:** "Build a timer" fails; "Here's the Jira URL, API field IDs, and mockups" succeeds
5. **Humans stay in charge:** AI suggests, architects decide, engineers review, managers approve

**For Netskope:**
- Current state: RBI team using AI for automation + code quality (proven)
- Next frontier: Apply to product feature development with guardrails (spec-driven, code review gates)
- Longer term: AI-assisted incident response (oncall automation), infrastructure optimization (AWS cost analyzer)

---

## Appendix A: File Inventory

**Project Structure — RBI Scrum Timer Repository**

```
rbi-scrum-time/
├── main.py                          # Entry point
├── requirements.txt                 # Dependencies
├── README.md                        # User documentation
├── app/
│   ├── __init__.py
│   ├── db.py                        # ~400 lines: SQLite CRUD + auto-migrations
│   ├── meeting.py                   # ~200 lines: MeetingTimer state machine
│   ├── models.py                    # ~50 lines: Dataclasses
│   ├── bell.py                      # ~80 lines: WAV chime generator + afplay
│   ├── jira_client.py               # ~600 lines: Jira API (board, sprints, avatars)
│   └── ui/
│       ├── app_window.py            # ~150 lines: Root window + tab layout
│       ├── meeting_tab.py           # ~600 lines: 4-column meeting view
│       ├── participants_tab.py      # ~400 lines: Participant CRUD + config
│       ├── stats_tab.py             # ~300 lines: Session history charts
│       ├── settings_tab.py          # ~350 lines: Jira credentials + team sync
│       ├── help_tab.py              # ~200 lines: Searchable help cards
│       ├── dialogs.py               # ~150 lines: Custom CTk popups
│       └── scroll_fix.py            # ~50 lines: macOS Tk9 trackpad scroll fix
├── data/ (gitignored)
│   ├── scrum.db                     # SQLite database
│   └── avatars/                     # Cached Jira profile pictures
└── assets/
    └── AppIcon.icns                 # macOS app icon
```

**Total lines of code:** ~4,000 lines of Python + SQL migrations

---

## Appendix B: Jira API Field IDs Reference

**Used in RBI Scrum Timer (and Other RBI Automations)**

```python
# customfield_24133: Release Note
# allowedValues: ["For Customer", "For Internal Use", "Not Required"]

# customfield_24136: Documentation Required
# allowedValues: ["Yes", "No"]

# customfield_16173: TOI Required
# allowedValues: ["Y", "N"]

# For Epics, Stories, Tasks, Bugs (NOT Subtasks)
# These are "Product Details" in Jira UI
```

**How to discover new field IDs:**
```bash
curl -u "$ATLASSIAN_EMAIL:$ATLASSIAN_API_TOKEN" \
  "https://netskope.atlassian.net/rest/api/3/fields" | jq '.[] | select(.name == "My Field") | .id'
```

---

## Appendix C: Future Enhancements (Not in MVP)

**Roadmap Discussed But Not Implemented**

1. **Export standup transcript** — Save meeting audio + session summary to markdown
2. **Slack integration** — Post standup summary to #scrum channel
3. **Per-person standup history** — Chart of individual speaking times over 8-week sprint
4. **Offline mode** — Timer works without Jira (cached data only)
5. **Multi-team support** — Switch between teams' configurations
6. **Web dashboard** — Read-only view of sprint metrics for stakeholders

**Why not included:** Scope creep risk. MVP is solid; these can be prioritized based on team feedback.

---

## Appendix D: For Claude Code Users — How to Replicate This

**If You Want to Build Your Own AI-Assisted Project**

### Step 1: Set Up SuperClaude
```bash
# Create global CLAUDE.md
mkdir -p ~/.claude
cat > ~/.claude/CLAUDE.md << 'EOF'
# My SuperClaude Setup

## Projects
- rbi-scrum-time: Desktop timer with Jira integration
- ...
EOF
```

### Step 2: Add Project-Local CLAUDE.md
```bash
# In your project root
cat > CLAUDE.md << 'EOF'
# rbi-scrum-time

## Purpose
Desktop standup timer for RBI team at Netskope.

## Architecture
- app/db.py: SQLite CRUD
- app/meeting.py: State machine (IDLE → RUNNING → PAUSED)
- app/ui/: customtkinter UI

## Lessons
- Platform abstraction layer needed from day 1 (afplay vs winsound vs aplay)
- CTkImage has memory leak; use weak refs
- macOS Tk9 CTkToplevel topmost issue
EOF
```

### Step 3: Create Memory Files
```bash
mkdir -p ~/.claude/projects/-Users-you-Repository-your-project/memory

cat > memory/user_profile.md << 'EOF'
# User Profile
- Python + pytest (API testing)
- SDET background
- Familiar with Jira API
EOF

cat > memory/project_your_project.md << 'EOF'
# Project: Your Project
- Stack: Python + customtkinter
- Challenges: ...
- Lessons: ...
EOF
```

### Step 4: Configure settings.json
```bash
cat > ~/.claude/settings.json << 'EOF'
{
  "model": "claude-haiku-4.5",
  "permissions": {
    "bash": ["read", "write"],
    "files": ["read", "write"]
  },
  "env": {
    "ATLASSIAN_EMAIL": "",
    "ATLASSIAN_API_TOKEN": ""
  },
  "hooks": {
    "startup": ["~/.claude/scripts/sync-skills.sh"]
  }
}
EOF
```

### Step 5: Start Claude Code in Your Project
```bash
cd rbi-scrum-time
claude code
```

Claude will automatically load your CLAUDE.md, memory files, and environment — and ask clarifying questions before implementing features.

---

## Appendix E: References & Further Reading

**Internal (Netskope RBI Team)**
- Confluence: [AI Adoption Success Stories](https://netskope.atlassian.net/wiki/spaces/DataScience/pages/6917849193/AI+Adoption+Success+Stories)
- Jira: RBI board (polaris-squad label)
- GitHub: [rbi-ai-gnition-lab](https://github.com/netskope/rbi-ai-gnition-lab) — automation library
- GitHub: [claude-skills](https://github.com/netskope/claude-skills) — reusable global skills

**External**
- [customtkinter documentation](https://github.com/TomSchimansky/CustomTkinter)
- [Jira Cloud REST API v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Python sqlite3 module](https://docs.python.org/3/library/sqlite3.html)
- [aispec.org](https://aispec.org/) — Spec-driven development framework
- [Augment Code](https://www.augmentcode.com/) — AI-assisted TDD

---

**Presentation prepared for:** Netskope RBI Team  
**Presented by:** Alex Sanchez (SDET)  
**Date:** June 11, 2026  
**Duration:** 45 minutes (20 slides + Q&A)
