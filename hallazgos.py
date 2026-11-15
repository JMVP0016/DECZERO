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

import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timezone

import requests
import streamlit as st

REPO = "JMVP0016/DECZERO"
API = f"https://api.github.com/repos/{REPO}"
TITLE_PREFIX = "[Finding]"
MARK_START = "<!-- hawapacha-data"
MARK_END = "hawapacha-data -->"
MAX_REPORTS_PER_VISIT = 3
MAX_REPORTS_PER_HOUR = 15      # for the whole app: a simple brake against spam
# Only issues written by the app's own account count as reports. The repository
# is public, so anyone could open an issue that imitates a report or a verdict.
TRUSTED_AUTHORS = {REPO.split("/")[0]}

KINDS = [
    "Possible movement",
    "Possible change in brightness",
    "Something appears or disappears",
    "Not sure",
]
PLACES = ["Inside the amber ring", "Centre", "Top left", "Top right", "Bottom left", "Bottom right"]

STATUS_NEW = "Waiting for review"
STATUS_OPENED = "Opened by a reviewer"
VERDICTS = [
    "Known object",
    "Image artifact",
    "Candidate: worth a follow-up",
    "Inconclusive",
]

# What happens with a report, shown next to the form and at the top of the board.
REPORT_FLOW = [
    ("You report", "It is published at once, with a public date and time that nobody can change."),
    ("Reviewer opens it", "The reviewer signs with a name and checks catalogues and the images."),
    ("Signed verdict", "Known object, image artifact, inconclusive, or candidate worth a follow-up."),
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


def _check(response):
    """Raise an error that includes GitHub's own explanation, to make setup problems clear."""
    if response.status_code < 400:
        return
    try:
        reason = response.json().get("message", "")
    except Exception:
        reason = response.text[:200]
    hint = ""
    if response.status_code in (401, 403):
        hint = " (check that the token is valid and has Issues: Read and write on this repository)"
    raise RuntimeError(f"GitHub answered {response.status_code}: {reason}{hint}")


def _body(data):
    """Issue text: a readable summary for people, plus the data for the app."""
    summary = (
        f"**Reported by:** {data['alias']}\n\n"
        f"**Position:** RA {data['ra']:.5f}, Dec {data['dec']:.5f} · detector {data['band']}\n\n"
        f"**What they noticed:** {data['kind']}\n\n"
        f"**Note:** {data['note']}\n\n"
        f"**Status:** {data['status']}\n\n"
        "_Report created from the HAWAPACHA app. The creation time of this issue "
        "is the record of when it was reported._\n\n"
    )
    return summary + f"{MARK_START}\n{json.dumps(data)}\n{MARK_END}"


def _parse(issue):
    """GitHub issue -> report dictionary, or None if it is not one of ours."""
    body = issue.get("body") or ""
    if MARK_START not in body or MARK_END not in body:
        return None
    author = (issue.get("user") or {}).get("login")
    if author is not None and author not in TRUSTED_AUTHORS:
        return None  # an imitation written by someone else
    try:
        raw = body.split(MARK_START, 1)[1].split(MARK_END, 1)[0]
        data = json.loads(raw)
    except Exception:
        return None
    data["number"] = issue["number"]
    data["created_at"] = issue["created_at"]
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
    _check(response)
    return [issue for issue in response.json() if "pull_request" not in issue]


def list_reports():
    """All reports, newest first."""
    reports = [_parse(issue) for issue in _fetch()]
    return sorted((r for r in reports if r), key=lambda r: r["number"], reverse=True)


def claim_hash(code):
    """What we store of the claim code: its SHA-256, never the code itself."""
    normal = re.sub(r"[^0-9A-Za-z]", "", str(code)).upper()
    return hashlib.sha256(normal.encode()).hexdigest()


def new_claim_code():
    raw = secrets.token_hex(4).upper()
    return f"{raw[:4]}-{raw[4:]}"


def find_by_claim(code):
    """The report that was created with this claim code, or None."""
    wanted = claim_hash(code)
    for report in list_reports():
        if report.get("claim") == wanted:
            return report
    return None


def reports_last_hour():
    limit = datetime.now(timezone.utc).timestamp() - 3600
    count = 0
    for report in list_reports():
        try:
            created = datetime.strptime(report["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            if created.replace(tzinfo=timezone.utc).timestamp() >= limit:
                count += 1
        except Exception:
            continue
    return count


def create_report(alias, ra, dec, band, kind, note, view, frame):
    """Publish a report. Returns (number, claim code); the code is shown only once."""
    code = new_claim_code()
    data = {
        "claim": claim_hash(code),
        "alias": clean(alias, 40) or "Anonymous",
        "ra": float(ra), "dec": float(dec), "band": clean(band, 4),
        "kind": kind if kind in KINDS else "Not sure",
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
            json={"title": title, "body": _body(data)},
        )
        _check(response)
        number = response.json()["number"]
    _fetch.clear()
    return number, code


def add_event(report, kind, reviewer, text=""):
    """Record that a reviewer opened the report or gave a verdict."""
    data = {k: v for k, v in report.items() if k not in ("number", "reported", "url", "created_at")}
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
        _check(requests.post(
            f"{API}/issues/{number}/comments", headers=_headers(), timeout=20,
            json={"body": comment},
        ))
        _check(requests.patch(
            f"{API}/issues/{number}", headers=_headers(), timeout=20,
            json={"body": _body(data)},
        ))
    _fetch.clear()


# ---------------------------------------------------------------- report form

def _claim_box(number, code):
    with st.container(border=True, key="claim"):
        st.success(f"Published as report #{number}. You can follow it on the Findings board.")
        st.markdown('<p class="dz-claim-label">Your claim code</p>', unsafe_allow_html=True)
        st.code(code, language=None)
        st.warning(
            "Write down this claim code now: it is shown only once, and it is the "
            "only way to prove later that this report is yours."
        )


@st.dialog("Report a finding", width="large")
def _report_dialog(ra, dec, band, view, frame, picture):
    """The report form, in a window over the page. It shows the frame being reported."""
    if st.session_state.get("claim_in_dialog"):
        _claim_box(*st.session_state["claim_in_dialog"])
        if st.button("Done", type="primary"):
            st.rerun()
        return
    st.caption(
        "Your report is published at once on the public Findings board, with a date and time "
        "that nobody can change. A reviewer then opens it and signs a verdict."
    )
    seen, form_column = st.columns([2, 3], gap="medium")
    if picture is not None:
        seen.image(picture, use_container_width=True)
    seen.markdown(
        '<div class="dz-context"><span>You are reporting</span>'
        f"<b>RA {ra:.5f}°, Dec {dec:.5f}°</b>"
        f"<em>Detector {clean(band, 4)} · {clean(view, 40).split(' (')[0]} view · frame: {clean(frame, 60)}</em></div>",
        unsafe_allow_html=True,
    )
    with form_column.form("report"):
        first, second = st.columns(2)
        alias = first.text_input("Your nickname", max_chars=40, placeholder="No personal data")
        kind = second.selectbox("What did you notice?", KINDS)
        place = st.selectbox("Where in the picture?", PLACES)
        note = st.text_area(
            "Describe it: what changes, and between which dates",
            max_chars=600, height=110,
        )
        submitted = st.form_submit_button("Publish report", type="primary")
    if not submitted:
        return
    if not alias.strip() or len(note.strip()) < 15 or len(note.split()) < 4:
        form_column.error(
            "Please write a nickname and a description of at least four words "
            "(15 characters), so a reviewer can find what you saw."
        )
        return
    try:
        if reports_last_hour() >= MAX_REPORTS_PER_HOUR:
            form_column.error("Too many reports were sent in the last hour. Please try again later.")
            return
        same = [
            r for r in list_reports()
            if r["alias"] == clean(alias, 40) and r["note"] == clean(f"{place}: {note}", 600)
        ]
        if same:
            form_column.error(f"This report was already published as #{same[0]['number']}.")
            return
        number, code = create_report(alias, ra, dec, band, kind, f"{place}: {note}", view, frame)
    except Exception as error:
        form_column.error(f"The report could not be published. Please try again. Detail: {error}")
        return
    st.session_state["reports_sent"] = st.session_state.get("reports_sent", 0) + 1
    st.session_state["last_claim"] = (number, code)
    st.session_state["claim_in_dialog"] = (number, code)
    st.rerun(scope="fragment")   # redraw only this window, now with the claim code


def can_report():
    """True if this visitor can still send a report."""
    return can_write() and st.session_state.get("reports_sent", 0) < MAX_REPORTS_PER_VISIT


def report_button(ra, dec, band, view, frame, picture=None, open_now=False):
    """
    A band under the pictures with one button; the form opens in a window.
    open_now=True opens the window too (used by the second button above the pictures).
    """
    clicked = False
    with st.container(key="cta"):
        text, action = st.columns([3, 1], vertical_alignment="center")
        text.markdown(
            '<p class="dz-cta-title">Noticed something in these images?</p>'
            '<p class="dz-cta-line">Report it. It goes on the public Findings board with the '
            "time you reported it, and a reviewer checks it.</p>",
            unsafe_allow_html=True,
        )
        if not can_write():
            action.caption("Reporting is not set up on this copy of the app yet.")
        elif st.session_state.get("reports_sent", 0) >= MAX_REPORTS_PER_VISIT:
            action.caption("You have reached the limit of reports for this visit.")
        else:
            clicked = action.button("Report a finding", type="primary", key="report_open", use_container_width=True)
    if clicked or (open_now and can_report()):
        st.session_state.pop("claim_in_dialog", None)
        _report_dialog(ra, dec, band, view, frame, picture)
    if st.session_state.get("last_claim"):
        _claim_box(*st.session_state["last_claim"])
