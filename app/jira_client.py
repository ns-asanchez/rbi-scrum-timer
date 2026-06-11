"""Jira client — board members + issue fetching (non-blocking, thread-based).

Credentials priority:
1. ATLASSIAN_EMAIL + ATLASSIAN_API_TOKEN env vars (set via ~/.zshrc or Settings tab)
2. If not set → returns an error message telling the user to set them in Settings.
"""

import base64
import json
import os
import re
import threading
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse


# Board column map (board 14955)
BOARD_COLUMN_MAP = {
    "10945": "To Do", "1": "To Do", "10869": "To Do", "11647": "To Do", "11141": "To Do",
    "11142": "In Progress", "4": "In Progress", "3": "In Progress", "18682": "In Progress",
    "10804": "Blocked", "14478": "Blocked", "18683": "Blocked",
    "11648": "Code Review", "10958": "Code Review", "10500": "Code Review",
    "11214": "Ready to test", "18211": "Ready to test", "5": "Ready to test",
    "10200": "Ready to test", "12045": "Ready to test",
    "11496": "Closed", "6": "Closed", "10018": "Closed", "11143": "Closed",
    "11670": "Closed", "10006": "Closed", "11495": "Closed",
}

JIRA_BASE = "https://netskope.atlassian.net"
AVATAR_CACHE = Path(__file__).parent.parent / "data" / "avatars"

BOARD_FILTER = (
    'project in (Engineering, RBI, "Quality Engineering", "Core QE") '
    "AND labels in (rbi-qe, rbi-qe-core, rbi-infra, rbi-provider-linux, rbi-core, "
    "rbi-devops, forge-squad, urp-ai-automation, serenity-squad, polaris-squad)"
)


# ── Credentials ───────────────────────────────────────────────────────────────


def _get_credentials() -> tuple[str, str] | None:
    """Return (email, token) if both are set, else None."""
    email = os.environ.get("ATLASSIAN_EMAIL", "").strip()
    token = os.environ.get("ATLASSIAN_API_TOKEN", "").strip()
    return (email, token) if email and token else None


def _build_auth(email: str, token: str) -> str:
    """Build HTTP Basic auth header value."""
    return "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()


def _request(path: str, params: dict | None = None, body: dict | None = None) -> dict:
    """Make an authenticated HTTP request to Jira. Raises RuntimeError if credentials missing."""
    creds = _get_credentials()
    if not creds:
        raise RuntimeError(
            "Jira credentials not found.\n"
            "Set ATLASSIAN_EMAIL and ATLASSIAN_API_TOKEN in Settings → Tokens."
        )
    email, token = creds
    url = f"{JIRA_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"Authorization": _build_auth(email, token), "Accept": "application/json"}
    encoded_body = None
    if body:
        encoded_body = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        url, data=encoded_body, headers=headers, method="POST" if body else "GET"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _strip_order_by(jql: str) -> str:
    """Remove ORDER BY clause from JQL so it can be safely embedded in a compound query."""
    return re.sub(r"\s+ORDER\s+BY\s+.+$", "", jql, flags=re.IGNORECASE).strip()


# ── Credential test ───────────────────────────────────────────────────────────


def test_credentials(
    email: str,
    token: str,
    on_ok: Callable[[], None],
    on_error: Callable[[str], None],
) -> None:
    """Test Jira credentials asynchronously by calling /myself endpoint."""

    def _run():
        try:
            req = urllib.request.Request(
                f"{JIRA_BASE}/rest/api/3/myself",
                headers={
                    "Authorization": _build_auth(email, token),
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
            if data.get("accountId"):
                on_ok()
            else:
                on_error("Unexpected response — check credentials")
        except Exception as e:
            on_error(str(e))

    threading.Thread(target=_run, daemon=True).start()


# ── Board URL parsing ─────────────────────────────────────────────────────────


def parse_board_id(board_url: str) -> int | None:
    """Extract board ID from a URL like .../boards/14955?..."""
    m = re.search(r"/boards/(\d+)", board_url)
    return int(m.group(1)) if m else None


# ── Avatar download ───────────────────────────────────────────────────────────


def download_avatar(account_id: str, avatar_url: str) -> Path | None:
    """Download and cache Jira avatar. Returns local path or None on failure."""
    AVATAR_CACHE.mkdir(parents=True, exist_ok=True)
    dest = AVATAR_CACHE / f"{account_id}.png"
    if dest.exists():
        return dest
    try:
        req = urllib.request.Request(avatar_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
        dest.write_bytes(data)
        return dest
    except Exception:
        return None


# ── Board members ─────────────────────────────────────────────────────────────


def fetch_board_members(
    board_url: str,
    on_done: Callable[[list[dict]], None],
    on_error: Callable[[str], None],
) -> None:
    """Fetch unique assignees from the board's active sprint issues.
    Returns list of {accountId, displayName, avatarUrl, avatarPath}.
    """
    board_id = parse_board_id(board_url)
    if not board_id:
        on_error(f"Could not parse board ID from URL: {board_url}")
        return

    def _run():
        try:
            # Get board filter config + label filter from URL query string
            cfg = _request(f"/rest/agile/1.0/board/{board_id}/configuration")
            filter_id = cfg.get("filter", {}).get("id")

            # Get filter JQL
            fdata = _request(f"/rest/api/2/filter/{filter_id}")
            base_jql = _strip_order_by(fdata.get("jql", ""))

            # Extract label from board URL (e.g. ?label=polaris-squad)
            qs = parse_qs(urlparse(board_url).query)
            label = qs.get("label", [None])[0]
            label_clause = f' AND labels = "{label}"' if label else ""

            combined = f"({base_jql}){label_clause} AND sprint in openSprints()"

            # Paginate to get ALL unique assignees
            seen = {}
            next_token = None
            while True:
                body = {"jql": combined, "maxResults": 100, "fields": ["assignee"]}
                if next_token:
                    body["nextPageToken"] = next_token
                page = _request("/rest/api/3/search/jql", body=body)
                for issue in page.get("issues", []):
                    a = issue["fields"].get("assignee") or {}
                    aid = a.get("accountId")
                    if aid and aid not in seen:
                        avatar_url = a.get("avatarUrls", {}).get("48x48", "")
                        avatar_path = (
                            download_avatar(aid, avatar_url) if avatar_url else None
                        )
                        seen[aid] = {
                            "accountId": aid,
                            "displayName": a.get("displayName", ""),
                            "avatarUrl": avatar_url,
                            "avatarPath": str(avatar_path) if avatar_path else None,
                        }
                if page.get("isLast", True):
                    break
                next_token = page.get("nextPageToken")

            # Filter out service accounts
            members = [
                v
                for v in seen.values()
                if not v["displayName"].lower().startswith("rbi-")
            ]
            on_done(sorted(members, key=lambda x: x["displayName"]))
        except Exception as e:
            on_error(str(e))

    threading.Thread(target=_run, daemon=True).start()


# ── Issues for participant ─────────────────────────────────────────────────────


def fetch_closed_issues_for_participant(
    account_id: str,
    board_url: str,
    on_done: Callable[[list[dict]], None],
    on_error: Callable[[str], None],
    is_jefote: bool = False,
) -> None:
    """Fetch Done/closed issues from the current sprint (async, calls on_done or on_error)."""
    if not account_id:
        on_error("No Jira account ID")
        return

    def _run():
        try:
            if is_jefote:
                jql = (
                    f'assignee = "{account_id}" '
                    f"AND sprint in openSprints() "
                    f"AND statusCategory = Done "
                    f"ORDER BY updated DESC"
                )
            else:
                bid = parse_board_id(board_url) if board_url else None
                if bid:
                    cfg = _request(f"/rest/agile/1.0/board/{bid}/configuration")
                    fid = cfg.get("filter", {}).get("id")
                    fdata = _request(f"/rest/api/2/filter/{fid}")
                    board_jql = _strip_order_by(fdata.get("jql", BOARD_FILTER))
                else:
                    board_jql = BOARD_FILTER

                jql = (
                    f'assignee = "{account_id}" '
                    f"AND ({board_jql}) "
                    f"AND sprint in openSprints() "
                    f"AND statusCategory = Done "
                    f"ORDER BY updated DESC"
                )

            data = _request(
                "/rest/api/3/search/jql",
                body={
                    "jql": jql,
                    "maxResults": 20,
                    "fields": ["summary", "status", "customfield_10004", "customfield_10200"],
                },
            )

            issues = []
            for item in data.get("issues", []):
                f = item.get("fields", {})
                status_id = str(f.get("status", {}).get("id", ""))
                qa_field = f.get("customfield_10200") or {}
                issues.append(
                    {
                        "key":    item["key"],
                        "summary": f.get("summary", ""),
                        "status": f.get("status", {}).get("name", "?"),
                        "points": f.get("customfield_10004"),
                        "url":    f"{JIRA_BASE}/browse/{item['key']}",
                        "qa":     qa_field.get("displayName", "") if qa_field else "",
                        "column": BOARD_COLUMN_MAP.get(status_id, ""),
                    }
                )
            on_done(issues)
        except Exception as e:
            on_error(str(e))

    threading.Thread(target=_run, daemon=True).start()



def fetch_sprint_info(
    board_url: str,
    on_done: "Callable[[list[dict]], None]",
    on_error: "Callable[[str], None]",
) -> None:
    """Fetch active sprint(s) info for the board asynchronously."""
    board_id = parse_board_id(board_url) if board_url else None
    if not board_id:
        on_error("No board URL configured in Settings.")
        return

    def _run():
        try:
            data = _request(
                f"/rest/agile/1.0/board/{board_id}/sprint",
                params={"state": "active"},
            )
            import re as _re
            from datetime import datetime, timezone
            sprints = []
            for s in data.get("values", []):
                name = s.get("name", "")
                if not _re.match(r"R\d+\s*-\s*RBI Sprint", name):
                    continue
                sprint_id = s.get("id")
                # Fetch issue stats filtered by board JQL + label (polaris-squad only)
                try:
                    cfg = _request(f"/rest/agile/1.0/board/{board_id}/configuration")
                    fid = cfg.get("filter", {}).get("id")
                    fdata = _request(f"/rest/api/2/filter/{fid}")
                    board_jql = _strip_order_by(fdata.get("jql", ""))
                    qs = parse_qs(urlparse(board_url).query)
                    label = qs.get("label", [None])[0]
                    label_clause = f' AND labels = "{label}"' if label else ""
                    sprint_jql = f"sprint = {sprint_id} AND ({board_jql}){label_clause}"
                    issues_data = _request("/rest/api/3/search/jql", body={
                        "jql": sprint_jql,
                        "maxResults": 200,
                        "fields": ["status", "customfield_10004"],
                    })
                    issues = issues_data.get("issues", [])
                    total = len(issues)
                    done_issues = sum(1 for i in issues if i["fields"]["status"]["statusCategory"]["key"] == "done")
                    inprog = sum(1 for i in issues if i["fields"]["status"]["statusCategory"]["key"] == "indeterminate")
                    todo = total - done_issues - inprog
                    sp_done = int(sum(i["fields"].get("customfield_10004") or 0 for i in issues if i["fields"]["status"]["statusCategory"]["key"] == "done"))
                    sp_total = int(sum(i["fields"].get("customfield_10004") or 0 for i in issues))
                except Exception:
                    total = done_issues = inprog = todo = sp_done = sp_total = 0

                # Days remaining
                end_str = s.get("endDate", "")
                days_left = "—"
                if end_str:
                    try:
                        end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                        delta = (end_dt - datetime.now(timezone.utc)).days
                        days_left = f"{max(0, delta)} days"
                    except Exception:
                        pass

                # Sprint Report — use same filtered issues (polaris-squad only)
                # greenhopper report includes all squads, so we derive from our filtered set
                report_completed    = done_issues
                report_remaining    = inprog + todo
                report_removed      = 0  # not available via JQL
                report_sp_completed = sp_done
                report_sp_remaining = sp_total - sp_done

                sprints.append({
                    "name":              name,
                    "startDate":         s.get("startDate", "")[:10] if s.get("startDate") else "—",
                    "endDate":           s.get("endDate", "")[:10] if s.get("endDate") else "—",
                    "goal":              s.get("goal", "") or "—",
                    "daysLeft":          days_left,
                    "total":             total,
                    "done":              done_issues,
                    "inProgress":        inprog,
                    "todo":              todo,
                    "spDone":            sp_done,
                    "spTotal":           sp_total,
                    # Insights (sprint report)
                    "reportCompleted":   report_completed,
                    "reportRemaining":   report_remaining,
                    "reportRemoved":     report_removed,
                    "reportSpCompleted": report_sp_completed,
                    "reportSpRemaining": report_sp_remaining,
                })
            on_done(sprints)
        except Exception as e:
            on_error(str(e))

    threading.Thread(target=_run, daemon=True).start()

def fetch_issues_for_participant(
    account_id: str,
    board_url: str,
    on_done: Callable[[list[dict]], None],
    on_error: Callable[[str], None],
    is_jefote: bool = False,
) -> None:
    """Fetch active sprint issues for account_id.
    Attendees: board filter + openSprints.
    Jefotes: assignee + openSprints only.
    """
    if not account_id:
        on_error("No Jira account ID for this participant")
        return

    def _run():
        try:
            if is_jefote:
                jql = (
                    f'assignee = "{account_id}" '
                    f"AND sprint in openSprints() "
                    f"AND statusCategory != Done "
                    f"ORDER BY Rank ASC"
                )
            else:
                bid = parse_board_id(board_url) if board_url else None
                if bid:
                    cfg = _request(f"/rest/agile/1.0/board/{bid}/configuration")
                    fid = cfg.get("filter", {}).get("id")
                    fdata = _request(f"/rest/api/2/filter/{fid}")
                    board_jql = _strip_order_by(fdata.get("jql", BOARD_FILTER))
                else:
                    board_jql = BOARD_FILTER

                jql = (
                    f'assignee = "{account_id}" '
                    f"AND ({board_jql}) "
                    f"AND sprint in openSprints() "
                    f"AND statusCategory != Done "
                    f"ORDER BY Rank ASC"
                )

            data = _request(
                "/rest/api/3/search/jql",
                body={
                    "jql": jql,
                    "maxResults": 30,
                    "fields": ["summary", "status", "customfield_10004", "issuetype", "customfield_10200"],
                },
            )

            issues = []
            for item in data.get("issues", []):
                f = item.get("fields", {})
                status_id = str(f.get("status", {}).get("id", ""))
                qa_field = f.get("customfield_10200") or {}
                issues.append(
                    {
                        "key":    item["key"],
                        "summary": f.get("summary", ""),
                        "status": f.get("status", {}).get("name", "?"),
                        "points": f.get("customfield_10004"),
                        "url":    f"{JIRA_BASE}/browse/{item['key']}",
                        "qa":     qa_field.get("displayName", "") if qa_field else "",
                        "column": BOARD_COLUMN_MAP.get(status_id, ""),
                    }
                )
            on_done(issues)
        except Exception as e:
            on_error(str(e))

    threading.Thread(target=_run, daemon=True).start()
