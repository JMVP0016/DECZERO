# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""
Findings board, with four spaces:
  - Candidates:   only the reports that a reviewer marked as a candidate worth a
                  follow-up, and the observers with most candidates. For anyone.
  - All reports:  every report and its status, for anyone.
  - My reports:   a visitor follows their own reports with their claim codes. The
                  codes travel in the page address, so a saved link is the way back.
  - Review desk:  a reviewer signs in with the code given by the team, sees the
                  queue and signs verdicts. The sign-in lasts for the browser session.
With sign-in set up (see hallazgos.py), "My reports" lists the reports of the
signed-in account and the review desk opens for the accounts on the reviewers
list. No e-mail or name is stored: only the nickname the visitor chooses.
"""

import html
import re

import streamlit as st

import fresco

fresco.actualizar()   # after an upload, do not mix new pages with old modules in memory

import hallazgos
import tema

st.set_page_config(page_title="HAWAPACHA — Findings board", page_icon=tema.ICON, layout="wide")
tema.aplicar_tema()
tema.navegacion()
tema.portada(compacta=True)

SPACES = {"mine": "My reports", "desk": "Review desk", "top": "Candidates", "board": "All reports"}
TRACK = ["Reported", "Opened by a reviewer", "Verdict signed"]


def progress(report):
    """How many of the three steps this report has passed."""
    if report["status"] in hallazgos.VERDICTS:
        return 3
    return 2 if report["status"] == hallazgos.STATUS_OPENED else 1


def card(report, reviewer=None, track=False):
    """One report. With a reviewer, it also shows the action that reviewer can take."""
    with st.container(border=True, key=f"rep_{report['number']}"):
        head, status = st.columns([3, 1])
        head.markdown(
            f'<span class="dz-rnum">#{int(report["number"])}</span>'
            f'<span class="dz-rkind">{html.escape(str(report["kind"]))}</span>'
            f'<p class="dz-rby">Reported by <b>{html.escape(str(report["alias"]))}</b>'
            f'{" (account)" if report.get("owner") else ""} '
            f'on {html.escape(str(report["reported"]))}</p>',
            unsafe_allow_html=True,
        )
        status.markdown(tema.estado(report["status"], report["status"] in hallazgos.VERDICTS),
                        unsafe_allow_html=True)
        if track:
            st.markdown(tema.seguimiento(progress(report), TRACK), unsafe_allow_html=True)

        st.write(report["note"])
        link = f"/?ra={report['ra']:.5f}&dec={report['dec']:.5f}&band={report['band']}"
        st.markdown(
            f"RA {report['ra']:.5f}°, Dec {report['dec']:.5f}° · detector {report['band']} · "
            f"seen in “{report['view']}”, frame {report['frame']} · "
            f"[Open these coordinates in the viewer]({link})"
            + (f" · [Public record]({report['url']})" if report["url"] else "")
        )
        for event in report.get("events", []):
            line = f"{event['at']} — **{event['type']}** by {event['by']}"
            if event.get("text"):
                line += f": {event['text']}"
            st.caption(line)

        if not reviewer:
            return
        key = f"r{report['number']}"
        if report["status"] == hallazgos.STATUS_NEW:
            if st.button("I am opening this report to review it", key=key + "open"):
                hallazgos.add_event(report, hallazgos.STATUS_OPENED, reviewer)
                st.rerun()
        elif report["status"] == hallazgos.STATUS_OPENED:   # one verdict per report
            with st.form(key + "form"):
                verdict = st.selectbox("Verdict", hallazgos.VERDICTS, key=key + "v")
                reason = st.text_area(
                    "Reason (which catalogue or check supports it)", key=key + "t", max_chars=600,
                )
                if st.form_submit_button("Sign and publish verdict"):
                    if len(reason.strip()) < 15:
                        st.error("Please give a reason of at least 15 characters.")
                    else:
                        hallazgos.add_event(report, verdict, reviewer, reason)
                        st.rerun()


# ---------------------------------------------------------------- which space

params = st.query_params
start = params.get("space", "mine" if "claim" in params else "board")
tema.seccion(1, "Findings")
if st.session_state.get("space") not in SPACES:      # first time here in this visit
    st.session_state["space"] = start if start in SPACES else "board"
space = st.segmented_control(
    "Space", list(SPACES), format_func=SPACES.get, label_visibility="collapsed", key="space",
    on_change=lambda: st.session_state.setdefault("role", "tab"),
) or "board"

try:
    reports = hallazgos.list_reports()
except Exception as error:
    st.error(f"The board could not be loaded right now. Detail: {error}")
    st.stop()

# ---------------------------------------------------------------- account and role

account = None
if hallazgos.accounts_enabled():
    account = hallazgos.account_box(key="top_account", back=f"findings:{space}")


def choose(role, where):
    st.session_state["role"] = role
    st.session_state["space"] = where


if account and not st.session_state.get("role"):
    # Right after signing in: one question, then straight to the right space.
    tema.seccion(2, "How do you want to take part?")
    amateur, expert = st.columns(2, gap="large")
    with amateur.container(border=True, key="role_amateur"):
        st.markdown(
            '<div class="dz-role"><i>01</i><b>I am an amateur</b>'
            "<p>Look at the sequences, report what you notice and follow your reports "
            "until a reviewer signs a verdict.</p></div>", unsafe_allow_html=True)
        st.button("Go to my reports", key="role_a", type="primary", use_container_width=True,
                  on_click=choose, args=("amateur", "mine"))
    with expert.container(border=True, key="role_expert"):
        st.markdown(
            '<div class="dz-role"><i>02</i><b>I am an astronomer or expert</b>'
            "<p>Open the reports waiting in the queue, check them against catalogues and "
            "sign a verdict with your name. The desk opens for the accounts on the team's "
            "reviewers list.</p></div>", unsafe_allow_html=True)
        st.button("Go to the review desk", key="role_e", type="primary", use_container_width=True,
                  on_click=choose, args=("expert", "desk"))
    st.caption("You can change at any time with the tabs above. To report, open a sequence in the Viewer.")
    tema.pie()
    st.stop()

statuses = [hallazgos.STATUS_NEW, hallazgos.STATUS_OPENED] + hallazgos.VERDICTS

# ---------------------------------------------------------------- public board

if space == "top":
    candidate = hallazgos.VERDICTS[2]
    winners = [r for r in reports if r["status"] == candidate]
    st.write(
        "Reports that a reviewer checked and marked as a **candidate worth a follow-up**. "
        "This list only holds what passed a review; everything else is in “All reports”."
    )
    st.caption(
        "A candidate is not a discovery: it means a reviewer found no known object or image "
        "artifact that explains it, so it deserves more data."
    )
    reviewed = sum(r["status"] in hallazgos.VERDICTS for r in reports)
    columns = st.columns(3)
    columns[0].metric("Candidates", len(winners))
    columns[1].metric("Reports reviewed", reviewed)
    columns[2].metric("Observers with a candidate", len({r["alias"] for r in winners}))
    if not winners:
        st.info("No candidates yet. When a reviewer marks a report as a candidate, it appears here.")
    else:
        tema.seccion(2, "Observers with most candidates")
        ranking = {}
        for report in winners:
            ranking[report["alias"]] = ranking.get(report["alias"], 0) + 1
        rows = "".join(
            f'<li><i>{place:02d}</i><b>{html.escape(str(name))}</b><span>{count} candidate{"s" if count != 1 else ""}</span></li>'
            for place, (name, count) in enumerate(sorted(ranking.items(), key=lambda item: (-item[1], item[0].lower()))[:10], start=1)
        )
        st.markdown(f'<ol class="dz-rank">{rows}</ol>', unsafe_allow_html=True)
        tema.seccion(3, "Candidates")
        with st.container(key="board"):
            for report in winners:
                card(report)

elif space == "board":
    st.write(
        "Things that visitors noticed in the SPHEREx sequences. Every report is public "
        "from the moment it is sent, with a public date and time that shows when it was "
        "reported. Reviewers must sign every step they take."
    )
    st.caption(
        "This is a prototype. A verdict here is an opinion from a reviewer of our team's "
        "choosing, not a confirmed discovery: a real confirmation needs more data and an "
        "official report to the astronomical community."
    )
    tema.pasos(hallazgos.REPORT_FLOW)

    tema.seccion(2, "Reports")
    left, right = st.columns([2, 1])
    chosen = left.multiselect("Status", statuses, default=statuses)
    mine = right.text_input("Only reports by this nickname", placeholder="a nickname")
    visible = [
        r for r in reports
        if r["status"] in chosen and (not mine.strip() or r["alias"].lower() == mine.strip().lower())
    ]
    counts = {status: sum(r["status"] == status for r in reports) for status in statuses}
    columns = st.columns(4)
    columns[0].metric("Reports", len(reports))
    columns[1].metric("Waiting for review", counts[hallazgos.STATUS_NEW])
    columns[2].metric("Reviewed", sum(counts[v] for v in hallazgos.VERDICTS))
    columns[3].metric("Candidates", counts[hallazgos.VERDICTS[2]])
    if reports and not visible:
        st.info("No reports match these filters.")
    if not reports:
        st.info("No reports yet. Open a sequence on the main page and use the “Report a finding” button.")
    with st.container(key="board"):
        for report in visible:
            card(report)

# ---------------------------------------------------------------- my reports

elif space == "mine" and hallazgos.accounts_enabled():
    st.write(
        "Follow the reports you sent. Your account has one nickname, which nobody else can "
        "use, and every report you publish is signed with it."
    )
    if account:
        found = hallazgos.reports_of(account)
        waiting = sum(r["status"] == hallazgos.STATUS_NEW for r in found)
        opened = sum(r["status"] == hallazgos.STATUS_OPENED for r in found)
        columns = st.columns(3)
        columns[0].metric("My reports", len(found))
        columns[1].metric("Waiting or in review", waiting + opened)
        columns[2].metric("With a verdict", len(found) - waiting - opened)
        if not found:
            st.info("You have not sent any report yet. Open a sequence in the viewer and use “Report a finding”.")
        with st.container(key="board"):
            for report in found:
                card(report, track=True)
                if report["status"] == hallazgos.STATUS_NEW:
                    st.caption("Nobody has opened this report yet. Reviewers are volunteers; come back later.")
                elif report["status"] == hallazgos.STATUS_OPENED:
                    st.caption("A reviewer is looking at this report. The verdict will appear here, signed.")

elif space == "mine":
    st.write(
        "Follow the reports you sent. There are no accounts here: the **claim code** you "
        "received when you published a report is your key. Nicknames can be copied by "
        "anyone; a claim code cannot."
    )
    typed = st.text_input(
        "Your claim code (several codes: separate them with a space)",
        value=params.get("claim", ""), placeholder="XXXX-XXXX",
    )
    codes = [c for c in re.split(r"[\s,;]+", typed.strip()) if c]
    if codes:
        # keep the codes in the page address, so a saved link brings the visitor back here
        st.query_params.update({"space": "mine", "claim": " ".join(codes)})
        st.caption(
            "Save this page as a bookmark: its address now holds your code and brings you "
            "straight back here. Do not share that link, it proves the report is yours."
        )
    else:
        st.info("Type the claim code of a report to see how far it has gone.")

    found, missing = [], []
    for code in codes[:10]:
        owned = hallazgos.find_by_claim(code)
        if owned and owned["number"] not in [r["number"] for r in found]:
            found.append(owned)
        elif not owned:
            missing.append(code)
    if missing:
        st.error("No report was created with: " + ", ".join(html.escape(c) for c in missing))
    if found:
        waiting = sum(r["status"] == hallazgos.STATUS_NEW for r in found)
        opened = sum(r["status"] == hallazgos.STATUS_OPENED for r in found)
        columns = st.columns(3)
        columns[0].metric("My reports", len(found))
        columns[1].metric("Waiting or in review", waiting + opened)
        columns[2].metric("With a verdict", len(found) - waiting - opened)
        with st.container(key="board"):
            for report in found:
                card(report, track=True)
                if report["status"] == hallazgos.STATUS_NEW:
                    st.caption("Nobody has opened this report yet. Reviewers are volunteers; come back later.")
                elif report["status"] == hallazgos.STATUS_OPENED:
                    st.caption("A reviewer is looking at this report. The verdict will appear here, signed.")

# ---------------------------------------------------------------- review desk

else:
    by_account = hallazgos.accounts_enabled()
    if by_account:
        st.write(
            "For the astronomers who review the reports. The desk opens for the accounts that "
            "the team has put on its reviewers list; every step is published with the reviewer's name."
        )
        reviewer = hallazgos.reviewer_name(account)
        if account and not reviewer:
            st.info(
                "This account is not on the reviewers list. If you are an astronomer and want "
                "to review reports, write to the team."
            )
    else:
        reviewers = hallazgos.reviewers()
        reviewer = reviewers.get(st.session_state.get("reviewer_code", ""))
    if by_account and not reviewer:
        pass
    elif not reviewer:
        st.write(
            "For the astronomers who review the reports. The team gives each reviewer a "
            "personal code; every step you take is published with your name."
        )
        with st.form("signin"):
            code = st.text_input("Reviewer code", type="password")
            if st.form_submit_button("Sign in", type="primary"):
                if code in reviewers:
                    st.session_state["reviewer_code"] = code
                    st.rerun()
                else:
                    st.error("Unknown code.")
        st.caption(
            "You stay signed in while this browser tab is open, also if you go to the viewer "
            "and come back. Nothing is stored on your device. If you are an astronomer and "
            "want to review, write to the team."
        )
    else:
        if not by_account:
            who, out = st.columns([4, 1], vertical_alignment="center")
            who.markdown(f'<div class="dz-who"><span>Signed in as</span>{html.escape(reviewer)}</div>',
                         unsafe_allow_html=True)
            if out.button("Sign out", use_container_width=True):
                st.session_state.pop("reviewer_code", None)
                st.rerun()

        def by_me(report, kinds):
            return any(e["by"] == reviewer and e["type"] in kinds for e in report.get("events", []))

        queue = sorted((r for r in reports if r["status"] == hallazgos.STATUS_NEW), key=lambda r: r["number"])
        in_progress = [r for r in reports if r["status"] == hallazgos.STATUS_OPENED]
        mine_open = [r for r in in_progress if by_me(r, [hallazgos.STATUS_OPENED])]
        others_open = [r for r in in_progress if r not in mine_open]
        signed = [r for r in reports if r["status"] in hallazgos.VERDICTS and by_me(r, hallazgos.VERDICTS)]
        columns = st.columns(3)
        columns[0].metric("Waiting for a reviewer", len(queue))
        columns[1].metric("Opened by me", len(mine_open))
        columns[2].metric("Verdicts I signed", len(signed))

        with st.container(key="board"):
            tema.seccion(2, "Opened by me: verdict pending")
            if not mine_open:
                st.caption("Nothing here. Open a report from the queue below.")
            for report in mine_open:
                card(report, reviewer)
            tema.seccion(3, "Queue: oldest first")
            if not queue:
                st.caption("The queue is empty.")
            for report in queue:
                card(report, reviewer)
            if others_open:
                with st.expander(f"Opened by other reviewers ({len(others_open)})"):
                    for report in others_open:
                        card(report, reviewer)
            if signed:
                with st.expander(f"Verdicts I signed ({len(signed)})"):
                    for report in signed:
                        card(report)

tema.pie()
