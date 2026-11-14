# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""
Findings board: anyone can report something they noticed in a sequence, and a
reviewer can open the report and give a verdict.

Each report is stored as a public GitHub issue of the project repository.
GitHub sets the creation time, so the record of who reported first cannot be
changed by us or by a reviewer. Every later step (opened, verdict) is added as
a comment on the issue and is signed with the reviewer's name.

Configuration (Streamlit secrets):
    GITHUB_TOKEN = "..."          token with Issues read/write on the repository
    [REVIEWERS]                   one line per reviewer:  code = "Name, role"
    "code-1" = "Dr. Example, astronomer"
"""

import json
import os
import re
from datetime import datetime, timezone

import requests
import streamlit as st

REPO = "JMVP0016/DECZERO"
API = f"https://api.github.com/repos/{REPO}"
TITLE_PREFIX = "[Finding]"
MARK_START = "<!-- hawapacha-data"
MARK_END = "hawapacha-data -->"
MAX_REPORTS_PER_VISIT = 3

KINDS = [
    "Something moves between dates",
    "Something changes brightness",
    "Something appears or disappears",
    "Other",
]

STATUS_NEW = "Waiting for review"
STATUS_OPENED = "Opened by a reviewer"
VERDICTS = [
    "Known object",
    "Image artifact",
    "Candidate: worth a follow-up",
]


# ---------------------------------------------------------------- configuration

def _secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:  # no secrets file at all
        return default


def token():
    return _secret("GITHUB_TOKEN")


def reviewers():
    """Dictionary code -> name. Empty if no reviewer has been set up."""
    if _memory_mode():
        return {"test-code": "Test Reviewer, astronomer"}
    table = _secret("REVIEWERS", {})
    return {str(code): str(name) for code, name in dict(table).items()}


def can_write():
    return bool(token()) or _memory_mode()


def _memory_mode():
    """Used only by the tests: keeps the reports in memory instead of GitHub."""
    return os.environ.get("HAWAPACHA_BACKEND") == "memory"


@st.cache_resource
def _memory():
    return {"next": 1, "issues": {}}


# ---------------------------------------------------------------- text safety

def clean(text, limit):
    """Plain text only: no mentions, no HTML, no markdown that could break the page."""
    text = re.sub(r"[<>`@\[\]]", "", str(text))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def now_text():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ---------------------------------------------------------------- storage

def _headers():
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token():
        headers["Authorization"] = f"Bearer {token()}"
    return headers


def _body(data):
    """Issue text: a readable summary for people, plus the data for the app."""
    summary = (
        f"**Reported by:** {data['alias']}\n\n"
        f"**Position:** RA {data['ra']:.5f}, Dec {data['dec']:.5f} · detector {data['band']}\n\n"
        f"**What they noticed:** {data['kind']}\n\n"
        f"**Note:** {data['note']}\n\n"
        f"**Status:** {data['status']}\n\n"
        "_Report created from the Hawapacha app. The creation time of this issue "
        "is the record of when it was reported._\n\n"
    )
    return summary + f"{MARK_START}\n{json.dumps(data)}\n{MARK_END}"


def _parse(issue):
    """GitHub issue -> report dictionary, or None if it is not one of ours."""
    body = issue.get("body") or ""
    if MARK_START not in body or MARK_END not in body:
        return None
    try:
        raw = body.split(MARK_START, 1)[1].split(MARK_END, 1)[0]
        data = json.loads(raw)
    except Exception:
        return None
    data["number"] = issue["number"]
    data["reported"] = issue["created_at"].replace("T", " ").replace("Z", " UTC")[:16] + " UTC"
    data["url"] = issue.get("html_url", "")
    return data


@st.cache_data(ttl=30, show_spinner=False)
def _fetch():
    if _memory_mode():
        return list(_memory()["issues"].values())
    response = requests.get(
        f"{API}/issues",
        params={"state": "all", "per_page": 100, "sort": "created", "direction": "desc"},
        headers=_headers(), timeout=20,
    )
    response.raise_for_status()
    return [issue for issue in response.json() if "pull_request" not in issue]


def list_reports():
    """All reports, newest first."""
    reports = [_parse(issue) for issue in _fetch()]
    return sorted((r for r in reports if r), key=lambda r: r["number"], reverse=True)


def create_report(alias, ra, dec, band, kind, note, view, frame):
    data = {
        "alias": clean(alias, 40) or "Anonymous",
        "ra": float(ra), "dec": float(dec), "band": clean(band, 4),
        "kind": kind if kind in KINDS else "Other",
        "note": clean(note, 600),
        "view": clean(view, 40), "frame": clean(frame, 60),
        "status": STATUS_NEW, "events": [],
    }
    title = f"{TITLE_PREFIX} {data['alias']}: RA {data['ra']:.4f}, Dec {data['dec']:.4f} ({data['band']})"
    if _memory_mode():
        store = _memory()
        number = store["next"]
        store["next"] += 1
        store["issues"][number] = {
            "number": number, "body": _body(data), "html_url": "",
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    else:
        response = requests.post(
            f"{API}/issues", headers=_headers(), timeout=20,
            json={"title": title, "body": _body(data), "labels": ["finding"]},
        )
        response.raise_for_status()
        number = response.json()["number"]
    _fetch.clear()
    return number


def add_event(report, kind, reviewer, text=""):
    """Record that a reviewer opened the report or gave a verdict."""
    data = {k: v for k, v in report.items() if k not in ("number", "reported", "url")}
    event = {"type": kind, "by": reviewer, "at": now_text(), "text": clean(text, 600)}
    data["events"] = list(data.get("events", [])) + [event]
    data["status"] = kind if kind in VERDICTS else STATUS_OPENED
    number = report["number"]
    comment = f"**{kind}** — {reviewer}, {event['at']}"
    if event["text"]:
        comment += f"\n\n{event['text']}"
    if _memory_mode():
        _memory()["issues"][number]["body"] = _body(data)
    else:
        requests.post(
            f"{API}/issues/{number}/comments", headers=_headers(), timeout=20,
            json={"body": comment},
        ).raise_for_status()
        requests.patch(
            f"{API}/issues/{number}", headers=_headers(), timeout=20,
            json={"body": _body(data)},
        ).raise_for_status()
    _fetch.clear()


# ---------------------------------------------------------------- report form

def report_form(ra, dec, band, view, frame):
    """Small form shown under a sequence in the main page."""
    with st.expander("Did you notice something? Report it"):
        if not can_write():
            st.info("Reporting is not set up on this copy of the app yet.")
            return
        st.write(
            "Your report is published on the public findings board with the current "
            "time, so there is a record that you saw it first. A reviewer will then "
            "check it. Use a nickname; do not write personal data."
        )
        sent = st.session_state.get("reports_sent", 0)
        if sent >= MAX_REPORTS_PER_VISIT:
            st.warning("You have reached the limit of reports for this visit.")
            return
        with st.form("report", clear_on_submit=True):
            alias = st.text_input("Your nickname", max_chars=40)
            kind = st.selectbox("What did you notice?", KINDS)
            note = st.text_area(
                "Describe it: where in the picture, and between which dates",
                max_chars=600,
            )
            submitted = st.form_submit_button("Publish report")
        if submitted:
            if not alias.strip() or len(note.strip()) < 15:
                st.error("Please write a nickname and a description of at least 15 characters.")
                return
            try:
                number = create_report(alias, ra, dec, band, kind, note, view, frame)
            except Exception as error:
                st.error(f"The report could not be published. Please try again. Detail: {error}")
                return
            st.session_state["reports_sent"] = sent + 1
            st.success(
                f"Published as report #{number}. You can follow it on the Findings page."
            )
