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

Accounts (optional). If the secrets have an [auth] table (Google sign-in of
Streamlit, st.login), visitors sign in, choose one nickname that nobody else can
take, and their reports are tied to that account. Reviewers are the accounts
whose e-mail is listed in [REVIEWER_EMAILS]. No e-mail is ever stored or shown:
reports and the nickname list keep only a salted hash of it. Without [auth] the
app works as before, with free nicknames, claim codes and reviewer codes.

Configuration (Streamlit secrets):
    GITHUB_TOKEN = "..."          token with Issues read/write on the repository
    [REVIEWERS]                   one line per reviewer:  code = "Name, role"
    "code-1" = "Dr. Example, astronomer"
    [auth]                        Google sign-in: redirect_uri, cookie_secret,
                                  client_id, client_secret, server_metadata_url
    [REVIEWER_EMAILS]             one line per reviewer:  "e-mail" = "Name, role"
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
REPORT_COOLDOWN_SECONDS = 24 * 3600   # 1 report per 24h per account to prevent spam/trolls
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
    ("You report", "It is published at once, with a public date and time set by GitHub, not by us."),
    ("Reviewer opens it", "The reviewer signs with a name and checks catalogues and the images."),
    ("Signed verdict", "Known object, image artifact, inconclusive, or candidate worth a follow-up."),
]
AMATEUR_FLOW = [
    ("Inspect a sequence", "Open one of the five targets or any sky position in the Viewer and compare periods."),
    ("Publish your report", "Mark where you saw movement or brightness change; GitHub sets the public UTC time."),
    ("Follow the verdict", "An astronomer checks catalogues and signs a verdict; candidates enter the ranking."),
]
EXPERT_FLOW = [
    ("Open from queue", "Claim the oldest waiting report so other reviewers see it is being checked."),
    ("Cross-check catalogues", "Inspect the SPHEREx sequence in the Viewer and check SIMBAD (2′) for known objects."),
    ("Sign a verdict", "Cite the catalogue or artifact check, or mark it as a candidate worth a follow-up."),
]
ORCID_RULE = re.compile(r"\d{4}-\d{4}-\d{4}-\d{3}[0-9Xx]")
SPECIALTIES = [
    "Astrometry & proper motion (brown dwarfs, solar neighbourhood, KBOs)",
    "Infrared photometry & spectral energy distributions (SPHEREx, WISE, 2MASS)",
    "Variable stars, young stellar objects & transients",
    "Detector artifacts, WCS calibration & image reduction",
]


# ---------------------------------------------------------------- configuration

def _secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:  # no secrets file at all
        return default


def token():
    found = _secret("GITHUB_TOKEN")
    if found:
        return str(found).strip()
    try:
        for value in st.secrets.values():
            if hasattr(value, "get") and value.get("GITHUB_TOKEN"):
                return str(value.get("GITHUB_TOKEN")).strip()
    except Exception:
        pass
    return None


TEAM_DECZERO_CODE = "DECZERO-2026"
TEAM_DECZERO_NAME = "Team DecZero — Core Verification & Review"


def reviewers():
    """Dictionary code -> name, including the Team DecZero special access code."""
    base = {
        TEAM_DECZERO_CODE: TEAM_DECZERO_NAME,
        "DECZERO-TEAM-2026": TEAM_DECZERO_NAME,
    }
    if _memory_mode():
        base["test-code"] = "Test Reviewer, astronomer"
        return base
    custom_team = _secret("DECZERO_CODE")
    if custom_team:
        base[str(custom_team).strip()] = TEAM_DECZERO_NAME
    table = _secret("REVIEWERS", {})
    for code, name in dict(table).items():
        base[str(code).strip()] = str(name)
    return base


def check_reviewer_code(raw_code):
    """Return the canonical code if raw_code matches a reviewer or Team DecZero code, else None."""
    cleaned = str(raw_code or "").strip()
    if not cleaned:
        return None
    rev = reviewers()
    if cleaned in rev:
        return cleaned
    for k in rev:
        if k.upper() == cleaned.upper():
            return k
    return None


def is_deczero_team(user=None, code=None):
    """True if signed in with a Team DecZero email or with the Team DecZero special access code."""
    if is_team_reviewer(user):
        return True
    active_code = str(code if code is not None else st.session_state.get("reviewer_code", "")).strip()
    if not active_code:
        return False
    canonical = check_reviewer_code(active_code)
    return bool(canonical and canonical in reviewers())


def can_write():
    return bool(token()) or _memory_mode()


def _memory_mode():
    """Used only by the tests: keeps the reports in memory instead of GitHub."""
    return os.environ.get("HAWAPACHA_BACKEND") == "memory"


@st.cache_resource
def _memory():
    return {"next": 1, "issues": {}}


# ---------------------------------------------------------------- accounts

ACCOUNTS_TITLE = "[Accounts] HAWAPACHA nicknames"
ACCOUNTS_START = "<!-- hawapacha-accounts"
ACCOUNTS_END = "hawapacha-accounts -->"
NICKNAME_RULE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{2,19}")


def accounts_enabled():
    """True if this copy of the app has sign-in set up."""
    if _memory_mode():
        return os.environ.get("HAWAPACHA_ACCOUNTS") == "1"
    try:
        return "auth" in st.secrets
    except Exception:
        return False


def _user_id(email):
    """What we keep of an account: a salted hash of its e-mail, never the e-mail."""
    salt = "test" if _memory_mode() else str(dict(_secret("auth", {})).get("cookie_secret", ""))
    return hashlib.sha256(f"{salt}:{email.strip().lower()}".encode()).hexdigest()[:24]


def current_user():
    """The signed-in account as {"id", "email"}, or None."""
    if not accounts_enabled():
        return None
    if _memory_mode():
        email = st.session_state.get("test_user", "")
    else:
        try:
            email = st.user.email if st.user.is_logged_in else ""
        except Exception:
            email = ""
    if not email:
        return None
    return {"id": _user_id(email), "email": email}


def sign_in():
    if _memory_mode():
        st.session_state["test_user"] = os.environ.get("HAWAPACHA_TEST_USER", "visitor@example.org")
        st.rerun()
    st.login()


def sign_out():
    for key in (
        "test_user", "role", "returned", "return_cleared", "reviewer_code",
        "skip_cooldown", "reports_sent", "last_claim", "claim_in_dialog",
        "space", "public_space", "review_space", "edit_accreditation",
    ):
        st.session_state.pop(key, None)
    if _memory_mode():
        st.rerun()
    st.logout()


def is_team_reviewer(user):
    """Name and role if this account is on the team's [REVIEWER_EMAILS] list."""
    if not user:
        return None
    if _memory_mode():
        table = {"astro@example.org": "Test Reviewer, astronomer"}
    else:
        table = dict(_secret("REVIEWER_EMAILS", {}))
    table = {str(k).strip().lower(): str(v) for k, v in table.items()}
    return table.get(user["email"].strip().lower())


def reviewer_name(user):
    """Name and role if this account is an accredited reviewer (team list or approved application)."""
    if not user:
        return None
    team = is_team_reviewer(user)
    if team:
        return team
    try:
        app = accreditation_of(user)
    except Exception:
        app = None
    if app and app.get("status") == "approved":
        return f"{app['signature']}, {app['institution']} (ORCID {app['orcid']})"
    return None


def _accounts_issue():
    """(issue number or None, {account id: nickname, '_applications': {...}})."""
    if _memory_mode():
        return None, dict(_memory().setdefault("accounts", {}))
    number, merged, apps = None, {}, {}
    for issue in reversed(_fetch()):
        author = (issue.get("user") or {}).get("login")
        if issue.get("title") == ACCOUNTS_TITLE and author in TRUSTED_AUTHORS:
            number = issue["number"]
            body = issue.get("body") or ""
            try:
                raw = body.split(ACCOUNTS_START, 1)[1].split(ACCOUNTS_END, 1)[0]
                loaded = dict(json.loads(raw))
                if isinstance(loaded.get("_applications"), dict):
                    apps.update(loaded.pop("_applications"))
                merged.update(loaded)
            except Exception:
                pass
    if apps:
        merged["_applications"] = apps
    return number, merged


def _save_accounts(number, table, comment=None):
    if _memory_mode():
        _memory()["accounts"] = table
    else:
        apps = table.get("_applications", {}) if isinstance(table.get("_applications"), dict) else {}
        summary_lines = [
            "Nicknames and reviewer accreditations of the HAWAPACHA app. Each entry is "
            "an anonymous account identifier; no e-mail is stored.\n"
        ]
        if apps:
            summary_lines.append("### Manual Reviewer Accreditation Applications\n")
            summary_lines.append("| Nickname | Signature | Institution | ORCID iD | Publication (DOI/ADS) | Status |")
            summary_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for item in apps.values():
                if isinstance(item, dict):
                    s_nick = str(item.get("nick", "")).replace("|", "/")
                    s_sig = str(item.get("signature", "")).replace("|", "/")
                    s_inst = str(item.get("institution", "")).replace("|", "/")
                    s_orcid = str(item.get("orcid", "")).replace("|", "/")
                    s_pub = str(item.get("publication", "")).replace("|", "/")
                    s_stat = str(item.get("status", "pending")).upper().replace("|", "/")
                    summary_lines.append(
                        f"| `{s_nick}` | **{s_sig}** | {s_inst} | "
                        f"[{s_orcid}](https://orcid.org/{s_orcid}) | `{s_pub}` | **{s_stat}** |"
                    )
            summary_lines.append("\n")
        body = "\n".join(summary_lines) + f"{ACCOUNTS_START}\n{json.dumps(table)}\n{ACCOUNTS_END}"
        if number is None:
            resp = requests.post(f"{API}/issues", headers=_headers(), timeout=20,
                                 json={"title": ACCOUNTS_TITLE, "body": body})
            _check(resp)
            number = resp.json().get("number")
        else:
            _check(requests.patch(f"{API}/issues/{number}", headers=_headers(), timeout=20,
                                  json={"body": body}))
        if comment and number is not None:
            try:
                requests.post(f"{API}/issues/{number}/comments", headers=_headers(), timeout=20,
                              json={"body": comment})
            except Exception:
                pass
    _fetch.clear()


def nickname_of(user):
    if not user:
        return None
    value = _accounts_issue()[1].get(user["id"])
    return value if isinstance(value, str) else None


def register_nickname(user, nickname):
    """Give this account its nickname. Returns an error text, or None if it worked."""
    nickname = nickname.strip()
    if not NICKNAME_RULE.fullmatch(nickname):
        return "Use 3 to 20 letters, numbers, hyphens or underscores, starting with a letter or number."
    _fetch.clear()                       # read the latest list before deciding
    number, table = _accounts_issue()
    if isinstance(table.get(user["id"]), str):
        return f"This account already has the nickname {table[user['id']]}."
    taken = {str(name).lower() for k, name in table.items() if not str(k).startswith("_") and isinstance(name, str)}
    if nickname.lower() in taken:
        return "That nickname is taken. Please choose another one."
    table[user["id"]] = nickname
    _save_accounts(number, table)
    return None


def accreditation_of(user):
    """The reviewer accreditation application of this account, or None."""
    if not user:
        return None
    apps = _accounts_issue()[1].get("_applications", {})
    return apps.get(user["id"]) if isinstance(apps, dict) else None


def list_accreditations():
    """All reviewer accreditation applications, newest first."""
    apps = _accounts_issue()[1].get("_applications", {})
    if not isinstance(apps, dict):
        return []
    return list(reversed(list(apps.values())))


def submit_accreditation(user, signature, institution, orcid, publication, specialty, note):
    """Submit a request for manual reviewer accreditation. Returns an error text, or None."""
    if not user or not user.get("id"):
        return "Please sign in with Google first."
    signature = clean(signature, 80)
    institution = clean(institution, 100)
    orcid = re.sub(r"^https?://(?:www\.)?orcid\.org/", "", str(orcid).strip(), flags=re.IGNORECASE).strip().upper()
    publication = clean(publication, 140)
    note = clean(note, 400)
    if len(signature) < 5 or len(institution) < 3:
        return "Please write your public name and role (for example 'Dr. Ana Perez, astronomer') and your institution."
    if not ORCID_RULE.fullmatch(orcid):
        return "Please enter a valid 16-digit ORCID iD in the format 0000-0002-1825-0097."
    if len(publication) < 6:
        return "Please cite at least one reference publication or catalogue entry (DOI or NASA/SAO ADS bibcode)."
    if len(note) < 15:
        return "Please describe briefly which catalogues or checks you use when vetting candidates (at least 15 characters)."
    _fetch.clear()
    number, table = _accounts_issue()
    apps = dict(table.get("_applications") or {})
    apps[user["id"]] = {
        "id": user["id"],
        "nick": user.get("nick") or table.get(user["id"], ""),
        "signature": signature,
        "institution": institution,
        "orcid": orcid,
        "publication": publication,
        "specialty": specialty if specialty in SPECIALTIES else SPECIALTIES[0],
        "note": note,
        "status": "pending",
        "at": now_text(),
    }
    table["_applications"] = apps
    notice = (
        f"**[Accreditation request — PENDING]** {signature} ({institution}) · "
        f"nickname `{apps[user['id']]['nick']}` · ORCID [{orcid}](https://orcid.org/{orcid}) · "
        f"Publication `{publication}` · Specialty: {apps[user['id']]['specialty']}\n\n"
        f"> {note}"
    )
    _save_accounts(number, table, comment=notice)
    return None


def decide_accreditation(applicant_id, status, reviewer):
    """Approve or dismiss a reviewer accreditation request."""
    _fetch.clear()
    number, table = _accounts_issue()
    apps = dict(table.get("_applications") or {})
    if applicant_id not in apps:
        return
    apps[applicant_id]["status"] = status
    apps[applicant_id]["verified_by"] = clean(reviewer, 80)
    apps[applicant_id]["verified_at"] = now_text()
    table["_applications"] = apps
    app = apps[applicant_id]
    notice = (
        f"**[Accreditation decision — {str(status).upper()}]** for **{app.get('signature', '')}** "
        f"(`{app.get('nick', '')}`) by {apps[applicant_id]['verified_by']} at {apps[applicant_id]['verified_at']}"
    )
    _save_accounts(number, table, comment=notice)


RETURN_COOKIE = "hawapacha_return"


def _cookie_script(value):
    """Set (or, with an empty value, remove) the small cookie that says where to go back to."""
    try:
        import streamlit.components.v1 as components
        age = 900 if value else 0
        components.html(
            "<script>try { window.parent.document.cookie = "
            f"'{RETURN_COOKIE}={value}; path=/; max-age={age}; SameSite=Lax'; }} catch (e) {{}}</script>",
            height=0,
        )
    except Exception:
        pass   # a convenience only


def back_after_sign_in():
    """
    Google sends the visitor back to the first page of the app. If they started the
    sign-in somewhere else, take them there. Call it at the top of app.py.
    Returns ("viewer", ra, dec, band) when the viewer should open that position.
    """
    if not accounts_enabled() or st.session_state.get("returned") or not current_user():
        return None
    st.session_state["returned"] = True          # only once per visit
    try:
        target = str(st.context.cookies.get(RETURN_COOKIE, ""))
    except Exception:
        target = ""
    parts = target.split(":")
    if parts[0] == "findings":
        where = parts[1] if len(parts) > 1 and parts[1] in ("board", "mine", "desk", "top") else "mine"
        st.session_state["space"] = where
        if where in ("mine", "desk"):
            st.session_state["review_space"] = where
            st.session_state["role"] = "expert" if where == "desk" else "amateur"
            st.switch_page("pages/4_Review.py")
        st.session_state["public_space"] = where
        st.switch_page("pages/3_Findings.py")
    if parts[0] == "viewer" and len(parts) == 4:
        try:
            return "viewer", float(parts[1]), float(parts[2]), clean(parts[3], 2)
        except ValueError:
            return None
    return None


def account_box(place=None, key="account", back=""):
    """
    back says where the visitor is ("findings:mine", "viewer:ra:dec:band"), so that
    the sign-in can bring them back to the same place.

    Sign-in strip. Returns {"id", "email", "nick"} when the visitor is signed in and
    has a nickname; otherwise draws what is missing (sign-in button or nickname form)
    and returns None.
    """
    place = place or st
    user = current_user()
    if not user:
        left, right = place.columns([3, 1.3], vertical_alignment="center")
        left.caption(
            "Sign in with a Google account to report and to follow your reports. We keep no "
            "e-mail and no name: only the nickname you choose."
        )
        if back and re.fullmatch(r"[A-Za-z0-9:._-]{1,80}", back):
            _cookie_script(back)                 # ready before the button is pressed
        if right.button("Sign in with Google", key=key + "_in", type="primary", use_container_width=True):
            sign_in()
        return None
    if not st.session_state.get("return_cleared"):
        st.session_state["return_cleared"] = True
        _cookie_script("")                       # signed in: the way back is no longer needed
    try:
        nick = nickname_of(user)
    except Exception as error:
        place.error(f"Your account could not be read right now. Detail: {error}")
        return None
    if not nick:
        with place.form(key + "_nick"):
            st.markdown("**Choose your nickname**")
            st.caption("It is public, it is yours alone and it cannot be changed later. Do not use your real name.")
            wanted = st.text_input("Nickname", max_chars=20, placeholder="for example sky_watcher")
            if st.form_submit_button("Keep this nickname", type="primary"):
                try:
                    problem = register_nickname(user, wanted)
                except Exception as error:
                    problem = f"The nickname could not be saved. Detail: {error}"
                if problem:
                    st.error(problem)
                else:
                    st.rerun()
        if place.button("Sign out", key=key + "_out0"):
            sign_out()
        return None
    left, right = place.columns([4, 1], vertical_alignment="center")
    role = reviewer_name(user)
    try:
        import tema
        rep = reputation_of({**user, "nick": nick})
        c_title = tema.nombramiento_estrella(rep["sides"], kind="citizen")
        star = f'{tema.estrella_svg(rep["sides"], 24, kind="citizen")} '
        star_label = f' <em class="dz-nom-pill">{c_title} · {rep["sides"]}/5</em>'
        if role:
            erep = expert_reputation_of(role)
            e_title = tema.nombramiento_estrella(erep["sides"], kind="expert")
            expert_part = (
                f' · {tema.estrella_svg(erep["sides"], 24, kind="expert")} '
                f'<em class="dz-nom-pill expert">{e_title} · {erep["sides"]}/5</em> '
                f'({clean(role, 70)})'
            )
        else:
            expert_part = ""
    except Exception:
        star = ""
        star_label = ""
        expert_part = f" · reviewer: {clean(role, 80)}" if role else ""
    wait_sec = cooldown_seconds_left(user)
    if wait_sec > 0:
        cd_strip = (
            f'<div class="dz-user-cd"><i></i><span>Cooldown</span>'
            f'<b>· {format_countdown(wait_sec)}</b>'
            '<em>(1 / 24h)</em></div>'
        )
    else:
        cd_strip = (
            '<div class="dz-user-cd"><i></i><span>Report ready</span>'
            '<b>· 00h 00m</b>'
            '<em>(1 / 24h)</em></div>'
        )
    left.markdown(
        '<div class="dz-who"><span>Signed in as</span><b>'
        + clean(nick, 20) + "</b> " + star + star_label + expert_part + "</div>" + cd_strip,
        unsafe_allow_html=True,
    )
    if right.button("Sign out", key=key + "_out", use_container_width=True):
        sign_out()
    return {**user, "nick": nick}


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
    if not token():
        hint = ' (GITHUB_TOKEN is missing in Streamlit Secrets; add GITHUB_TOKEN = "..." at the top of Settings → Secrets)'
    elif response.status_code in (401, 403, 404):
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
    if str(data.get("alias", "")).strip().lower() in ("ljeqoefjpoqwjepgof2w", "prueba deczero"):
        data["alias"] = "Team DecZero"
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
        params={"state": "open", "per_page": 100,   # closing an issue on GitHub hides it here
                "sort": "created", "direction": "desc"},
        headers=_headers(), timeout=20,
    )
    _check(response)
    return [issue for issue in response.json() if "pull_request" not in issue]


def list_reports():
    """All reports, newest first."""
    reports = [_parse(issue) for issue in _fetch()]
    return sorted((r for r in reports if r), key=lambda r: r["number"], reverse=True)


def reports_of(user):
    """Reports published from this account."""
    return [r for r in list_reports() if user and r.get("owner") == user["id"]]


def cooldown_seconds_left(user, items=None):
    """
    Seconds left in the 24-hour per-account report cooldown, or 0 if ready.
    Prevents infinite or troll reports from one account.
    """
    if not user or st.session_state.get("skip_cooldown"):
        return 0
    owned = (
        [r for r in items if r.get("owner") == user["id"]]
        if items is not None else reports_of(user)
    )
    if not owned:
        return 0
    now_ts = datetime.now(timezone.utc).timestamp()
    newest = 0.0
    for r in owned:
        try:
            ts = datetime.strptime(r["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
            if ts > newest:
                newest = ts
        except Exception:
            continue
    if newest <= 0:
        return 0
    left = int(REPORT_COOLDOWN_SECONDS - (now_ts - newest))
    return max(0, left)


def format_countdown(seconds):
    """Format remaining seconds as HHh MMm SSs."""
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}h {minutes:02d}m {secs:02d}s"


def reputation_of(user_or_alias, items=None):
    """
    Observer reputation & 5-sided star progress:
      - Every observer starts with 1 side illuminated (1/5).
      - Each additional side illuminates for every 5 expert-validated reports
        (verdict signed by an expert and not 'Image artifact'), up to 5/5 (full star glow).
      - Reputation tier rises by +1 for every 10 total reports submitted.
    """
    all_reports = items if items is not None else list_reports()
    if isinstance(user_or_alias, dict):
        uid = user_or_alias.get("id")
        nick = str(user_or_alias.get("nick", "")).strip().lower()
        owned = [
            r for r in all_reports
            if (uid and r.get("owner") == uid)
            or (not r.get("owner") and nick and str(r.get("alias", "")).strip().lower() == nick)
        ]
    else:
        nick = str(user_or_alias or "").strip().lower()
        owned = [r for r in all_reports if str(r.get("alias", "")).strip().lower() == nick]
    total = len(owned)
    valid_verdicts = {VERDICTS[0], VERDICTS[2], VERDICTS[3]}
    validated = sum(1 for r in owned if r.get("status") in valid_verdicts)
    sides = min(5, 1 + (validated // 5))
    next_side_in = 0 if sides >= 5 else 5 - (validated % 5)
    behavior_level = 1 + (total // 10)
    next_rep_in = 10 - (total % 10)
    return {
        "total": total,
        "validated": validated,
        "points": validated * 10,
        "sides": sides,
        "next_side_in": next_side_in,
        "behavior_level": behavior_level,
        "next_rep_in": next_rep_in,
    }


def expert_reputation_of(reviewer, items=None):
    """
    Astronomer / expert reputation & 5-sided violet star progress:
      - Every accredited reviewer starts with 1 side illuminated (1/5, Accredited Vetter).
      - Each additional side illuminates for every 5 signed verdicts, up to 5/5 (Principal Investigator).
      - Consistency tier rises by +1 for every 10 signed verdicts.
    """
    all_reports = items if items is not None else list_reports()
    full_name = str(reviewer or "").strip().lower()
    short_name = full_name.split(",")[0].strip()
    signed = 0
    opened = 0
    for r in all_reports:
        for ev in r.get("events", []):
            by = str(ev.get("by", "")).strip().lower()
            by_short = by.split(",")[0].strip()
            if full_name and (by == full_name or (short_name and by_short == short_name)):
                if ev.get("type") in VERDICTS:
                    signed += 1
                elif ev.get("type") == STATUS_OPENED:
                    opened += 1
    sides = min(5, 1 + (signed // 5))
    next_side_in = 0 if sides >= 5 else 5 - (signed % 5)
    behavior_level = 1 + (signed // 10)
    next_rep_in = 10 - (signed % 10)
    return {
        "signed": signed,
        "opened": opened,
        "points": signed * 10,
        "sides": sides,
        "next_side_in": next_side_in,
        "behavior_level": behavior_level,
        "next_rep_in": next_rep_in,
    }


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


def create_report(alias, ra, dec, band, kind, note, view, frame, owner=None):
    """
    Publish a report. Returns (number, claim code); the code is shown only once.
    owner is the account identifier when the visitor is signed in.
    """
    if owner:
        wait = cooldown_seconds_left(owner)
        if wait > 0:
            raise ValueError(f"24h report cooldown active ({format_countdown(wait)} remaining).")
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
    if owner:
        data["owner"] = str(owner)
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


create = create_report


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
        st.success(f"Observation saved as report #{number}. You can follow it on the Findings board.")
        st.markdown('<p class="dz-claim-label">Your claim code</p>', unsafe_allow_html=True)
        st.code(code, language=None)
        st.markdown(
            '<div class="dz-context"><span>Write it down now</span>'
            "<em>This code is not stored anywhere: once you leave this page it cannot be "
            "recovered, and it is the only way to prove later that this report is yours.</em></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"[Follow this report in “My reports”](/Review?space=mine&claim={code}) · "
            "save that link: it is your way back, without an account."
        )


@st.dialog("Report a finding", width="large")
def _report_dialog(ra, dec, band, view, frame, picture, account=None):
    """The report form, in a window over the page. It shows the frame being reported."""
    if not account and accounts_enabled():
        user = current_user()
        if user:
            try:
                nick = nickname_of(user)
                if nick:
                    account = {**user, "nick": nick}
            except Exception:
                pass
    if st.session_state.get("claim_in_dialog"):
        if account:
            st.success(
                f"Observation saved as report #{st.session_state['claim_in_dialog'][0]}, "
                f"signed with your nickname {account['nick']}."
            )
            c1, c2 = st.columns(2)
            if c1.button("Follow it in My reports", type="primary", use_container_width=True):
                st.session_state.pop("claim_in_dialog", None)
                st.session_state["role"] = "amateur"
                st.session_state["space"] = "mine"
                st.session_state["review_space"] = "mine"
                st.switch_page("pages/4_Review.py")
            if c2.button("Stay in the Viewer", use_container_width=True):
                st.session_state.pop("claim_in_dialog", None)
                st.rerun()
            return
        else:
            _claim_box(*st.session_state["claim_in_dialog"])
        if st.button("Done", type="primary"):
            st.session_state.pop("claim_in_dialog", None)
            st.rerun()
        return
    st.caption(
        "Your report is published at once on the public Findings board, with a date and time "
        "set by GitHub, not by us. A reviewer then opens it and signs a verdict."
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
        if account and account.get("nick"):
            alias = account["nick"]
            st.markdown(
                f'<div class="dz-who" style="margin-bottom:0.4rem;"><span>Reporting as</span>'
                f'<b>{clean(alias, 40)}</b></div>',
                unsafe_allow_html=True,
            )
            first, second = st.columns(2)
            kind = first.selectbox("What did you notice?", KINDS)
            place = second.selectbox("Where in the picture?", PLACES)
        else:
            first, second = st.columns(2)
            alias = first.text_input("Your nickname", max_chars=40, placeholder="No personal data")
            kind = second.selectbox("What did you notice?", KINDS)
            place = st.selectbox("Where in the picture?", PLACES)
        note = st.text_area(
            "Describe it: what changes, and between which dates",
            max_chars=600, height=110,
            placeholder="For example: Faint dot moves from bottom-left to top-right between 2025-08 and 2026-02.",
        )
        submitted = st.form_submit_button("Publish report", type="primary")
    if not submitted:
        return
    if not alias.strip():
        form_column.error("Please enter a nickname before publishing.")
        return
    if len(note.strip()) < 5:
        form_column.error(
            "Please write a short description of what changes in the image (at least 5 characters) "
            "so a reviewer knows where to look."
        )
        return
    try:
        if account:
            wait = cooldown_seconds_left(account)
            if wait > 0:
                form_column.error(
                    f"24-hour cooldown active: next report available in {format_countdown(wait)} "
                    "(1 report per 24 hours per account to prevent spam)."
                )
                return
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
        number, code = create_report(alias, ra, dec, band, kind, f"{place}: {note}", view, frame,
                                     owner=account["id"] if account else None)
    except Exception as error:
        form_column.error(f"The report could not be published. Please try again. Detail: {error}")
        return
    st.session_state["reports_sent"] = st.session_state.get("reports_sent", 0) + 1
    st.session_state.pop("skip_cooldown", None)
    if not account:
        st.session_state["last_claim"] = (number, code)
    st.session_state["claim_in_dialog"] = (number, code)
    st.rerun(scope="fragment")   # redraw only this window, now with the claim code


def can_report():
    """True if this visitor can still send a report."""
    if not can_write() or st.session_state.get("reports_sent", 0) >= MAX_REPORTS_PER_VISIT:
        return False
    if accounts_enabled():
        user = current_user()
        if user and cooldown_seconds_left(user) > 0:
            return False
    return True


def report_button(ra, dec, band, view, frame, picture=None, open_now=False):
    """
    A band under the pictures with one button; the form opens in a window.
    open_now=True opens the window too (used by the second button above the pictures).
    """
    clicked = False
    account = None
    wait_seconds = 0
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
        elif accounts_enabled():
            account = account_box(key="cta_account",     # sign-in or nickname first
                                  back=f"viewer:{float(ra):.5f}:{float(dec):.5f}:{clean(band, 2)}")
            if account:
                wait_seconds = cooldown_seconds_left(account)
                if wait_seconds > 0:
                    st.markdown(
                        '<div class="dz-cooldown-box wait">'
                        '<span>24h anti-spam cooldown active</span>'
                        f'<b>Next report in {format_countdown(wait_seconds)}</b>'
                        '<em>Each account can publish 1 report every 24 hours to prevent spam and keep the review queue clean.</em>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                    if is_team_reviewer(account):
                        if st.button("Reset 24h cooldown (team demo)", key="reset_cd_cta"):
                            st.session_state["skip_cooldown"] = True
                            st.session_state.pop("reports_sent", None)
                            st.rerun()
                else:
                    clicked = action.button("Report a finding", type="primary", key="report_open", use_container_width=True)
        else:
            clicked = action.button("Report a finding", type="primary", key="report_open", use_container_width=True)
    ready = (account is not None and wait_seconds == 0) or not accounts_enabled()
    if open_now and not ready:
        if account and wait_seconds > 0:
            st.warning(f"24-hour cooldown active: next report available in {format_countdown(wait_seconds)}.")
        else:
            st.info("Sign in first, in the band “Noticed something in these images?” below the pictures.")
    if (clicked or open_now) and ready and can_report():
        st.session_state.pop("claim_in_dialog", None)
        _report_dialog(ra, dec, band, view, frame, picture, account)
    if st.session_state.get("last_claim"):
        _claim_box(*st.session_state["last_claim"])
