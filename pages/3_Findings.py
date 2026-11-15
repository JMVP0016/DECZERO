# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""
Public Findings board (Tab 2):
  - All reports:           every public report and its review status, plus the
                           Community contributions dual ranking (Citizen science &
                           Professional astronomy with 5-sided stars).
  - Confirmed candidates:  only the reports that an accredited reviewer marked as a
                           candidate worth a follow-up.
Personal report tracking ("My reports") and the astronomer "Review desk" live in the
separate third tab: pages/4_Review.py ("My reports & Review").
"""

import html

import streamlit as st

import fresco

fresco.actualizar()   # after an upload, do not mix new pages with old modules in memory

import hallazgos
import tema

st.set_page_config(page_title="HAWAPACHA — Findings board", page_icon=tema.ICON, layout="wide")

params = st.query_params
legacy_space = params.get("space") or params.get("view")
if legacy_space in ("mine", "desk") or "claim" in params:
    target_space = "desk" if legacy_space == "desk" else "mine"
    st.session_state["review_space"] = target_space
    st.session_state["space"] = target_space
    if "claim" in params:
        st.session_state["claim_param"] = params.get("claim", "")
    st.switch_page("pages/4_Review.py")

tema.aplicar_tema()
tema.navegacion()
tema.portada()

PUBLIC_SPACES = {"board": "All reports", "top": "Confirmed candidates"}


def community_board(items):
    """Build and draw the two-column Community contributions leaderboard."""
    c_counts, c_names, e_counts, e_names = {}, {}, {}, {}
    for rep in items:
        alias = str(rep.get("alias", "")).strip()
        if alias:
            key = alias.lower()
            c_names.setdefault(key, alias)
            c_counts[key] = c_counts.get(key, 0) + 1
        for event in rep.get("events", []):
            if event.get("type") in hallazgos.VERDICTS:
                who = str(event.get("by", "")).split(",")[0].strip()
                if who:
                    ekey = who.lower()
                    e_names.setdefault(ekey, who)
                    e_counts[ekey] = e_counts.get(ekey, 0) + 1
    c_rows = [
        (c_names[k], count, hallazgos.reputation_of(c_names[k], items)["sides"])
        for k, count in sorted(c_counts.items(), key=lambda x: (-x[1], x[0]))[:5]
    ]
    e_rows = [
        (e_names[k], count, min(5, 1 + count // 5))
        for k, count in sorted(e_counts.items(), key=lambda x: (-x[1], x[0]))[:5]
    ]
    sample_used = False
    if len(c_rows) < 3:
        sample_used = True
        seen = {row[0].lower() for row in c_rows}
        for name, count in tema.SAMPLE_CITIZENS:
            if name.lower() not in seen and len(c_rows) < 3:
                c_rows.append((name, count, min(5, 1 + count // 5)))
        c_rows.sort(key=lambda x: -x[1])
    if len(e_rows) < 3:
        sample_used = True
        seen = {row[0].lower() for row in e_rows}
        for name, count in tema.SAMPLE_EXPERTS:
            if name.lower() not in seen and len(e_rows) < 3:
                e_rows.append((name, count, min(5, 1 + count // 5)))
        e_rows.sort(key=lambda x: -x[1])
    tema.contribuciones(c_rows, e_rows, usar_ejemplo=sample_used)


def card(report):
    """One public report card."""
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
        st.write(report["note"])
        link = f"/?ra={report['ra']:.5f}&dec={report['dec']:.5f}&band={report['band']}"
        coord = f"{report['ra']:.5f}%20{report['dec']:+.5f}".replace("+", "%2B")
        simbad = f"https://simbad.cds.unistra.fr/simbad/sim-coo?Coord={coord}&Radius=2&Radius.unit=arcmin"
        st.markdown(
            f"RA {report['ra']:.5f}°, Dec {report['dec']:.5f}° · detector {report['band']} · "
            f"seen in “{report['view']}”, frame {report['frame']} · "
            f"[Open these coordinates in the viewer]({link}) · "
            f"[Check in SIMBAD (2′)]({simbad})"
            + (f" · [Public record]({report['url']})" if report["url"] else "")
        )
        for event in report.get("events", []):
            line = f"{event['at']} — **{event['type']}** by {event['by']}"
            if event.get("text"):
                line += f": {event['text']}"
            st.caption(line)


# ---------------------------------------------------------------- public board

try:
    reports = hallazgos.list_reports()
except Exception as error:
    st.error(f"The board could not be loaded right now. Detail: {error}")
    st.stop()

# 1) First: Community contributions dual board (Citizen science & Professional astronomy)
community_board(reports)

# 2) Second: All reports / Confirmed candidates
if params.get("space") in PUBLIC_SPACES and st.session_state.get("_last_pub_param") != params.get("space"):
    st.session_state["_last_pub_param"] = params.get("space")
    st.session_state["public_space"] = params.get("space")
elif st.session_state.get("public_space") not in PUBLIC_SPACES:
    st.session_state["public_space"] = "board"

tema.seccion(1, "All reports")
space = st.segmented_control(
    "Public board view", list(PUBLIC_SPACES), format_func=PUBLIC_SPACES.get,
    label_visibility="collapsed", key="public_space",
) or "board"

statuses = [hallazgos.STATUS_NEW, hallazgos.STATUS_OPENED] + hallazgos.VERDICTS

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
        with st.container(key="board"):
            for report in winners:
                card(report)

else:
    st.write(
        "Public observations reported in the SPHEREx infrared sky sequences, with their "
        "timestamp, coordinates, SIMBAD cross-check link and signed expert verdicts."
    )
    counts = {status: sum(r["status"] == status for r in reports) for status in statuses}
    columns = st.columns(4)
    columns[0].metric("Reports", len(reports))
    columns[1].metric("Waiting for review", counts[hallazgos.STATUS_NEW])
    columns[2].metric("Reviewed", sum(counts[v] for v in hallazgos.VERDICTS))
    columns[3].metric("Candidates", counts[hallazgos.VERDICTS[2]])
    left, right = st.columns([2, 1])
    chosen = left.multiselect("Status", statuses, default=statuses)
    mine = right.text_input("Only reports by this nickname", placeholder="a nickname")
    visible = [
        r for r in reports
        if r["status"] in chosen and (not mine.strip() or r["alias"].lower() == mine.strip().lower())
    ]
    if reports and not visible:
        st.info("No reports match these filters.")
    if not reports:
        st.info("No reports yet. Open a sequence on the main page and use the “Report a finding” button.")
    with st.container(key="board"):
        for report in visible:
            card(report)

tema.pie()
