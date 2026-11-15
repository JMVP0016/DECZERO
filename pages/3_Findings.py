# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""
Findings board, with three spaces:
  - Public board: every report, for anyone.
  - My reports:   a visitor follows their own reports with their claim codes. The
                  codes travel in the page address, so a saved link is the way back.
  - Review desk:  a reviewer signs in with the code given by the team, sees the
                  queue and signs verdicts. The sign-in lasts for the browser session.
There are no accounts: nothing personal is stored.
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

SPACES = {"board": "Public board", "mine": "My reports", "desk": "Review desk"}
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
            f'<p class="dz-rby">Reported by <b>{html.escape(str(report["alias"]))}</b> '
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
space = st.segmented_control(
    "Space", list(SPACES), format_func=SPACES.get, label_visibility="collapsed",
    default=start if start in SPACES else "board", key="space",
) or "board"

try:
    reports = hallazgos.list_reports()
except Exception as error:
    st.error(f"The board could not be loaded right now. Detail: {error}")
    st.stop()

statuses = [hallazgos.STATUS_NEW, hallazgos.STATUS_OPENED] + hallazgos.VERDICTS

# ---------------------------------------------------------------- public board

if space == "board":
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
    reviewers = hallazgos.reviewers()
    reviewer = reviewers.get(st.session_state.get("reviewer_code", ""))
    if not reviewer:
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
