# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""Findings board: public list of reports, and the review tools for reviewers."""

import streamlit as st

import hallazgos
import tema

st.set_page_config(page_title="Findings · Hawapacha", layout="wide")
tema.aplicar_tema()

st.title("Findings board")
st.write(
    "Things that visitors noticed in the SPHEREx sequences. Every report is public "
    "from the moment it is sent, with its date and time, so the person who saw it "
    "first keeps the credit. Reviewers must sign every step they take."
)
st.caption(
    "This is a prototype. A verdict here is an opinion from a reviewer of our team's "
    "choosing, not a confirmed discovery: a real confirmation needs more data and an "
    "official report to the astronomical community."
)

# ---------------------------------------------------------------- reviewer login

reviewers = hallazgos.reviewers()
reviewer = None
with st.sidebar:
    st.subheader("Reviewer access")
    code = st.text_input("Reviewer code", type="password")
    if code:
        reviewer = reviewers.get(code)
        if reviewer:
            st.success(f"Signed in as {reviewer}")
        else:
            st.error("Unknown code.")
    st.caption("Codes are given by the team to astronomers who agree to review.")

# ---------------------------------------------------------------- load and filter

try:
    reports = hallazgos.list_reports()
except Exception as error:
    st.error(f"The board could not be loaded right now. Detail: {error}")
    st.stop()

left, right = st.columns([2, 1])
statuses = [hallazgos.STATUS_NEW, hallazgos.STATUS_OPENED] + hallazgos.VERDICTS
chosen = left.multiselect("Status", statuses, default=statuses)
mine = right.text_input("Only reports by this nickname", placeholder="your nickname")

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

if not reports:
    st.info(
        "No reports yet. Open a sequence on the main page and use "
        "“Did you notice something? Report it”."
    )

with st.expander("Prove that a report is yours"):
    st.write(
        "When you publish a report you receive a claim code. Nicknames can be copied "
        "by anyone; the claim code cannot. Type it here to show which report it belongs to."
    )
    claim = st.text_input("Claim code", placeholder="XXXX-XXXX")
    if claim.strip():
        owned = hallazgos.find_by_claim(claim)
        if owned:
            st.success(
                f"This code belongs to report #{owned['number']}, published by "
                f"{owned['alias']} on {owned['reported']}."
            )
        else:
            st.error("No report was created with this code.")

# ---------------------------------------------------------------- the board

for report in visible:
    with st.container(border=True):
        head, status = st.columns([3, 1])
        head.markdown(
            f"**#{report['number']} · {report['kind']}**  \n"
            f"Reported by **{report['alias']}** on {report['reported']}"
        )
        status.markdown(f"**{report['status']}**")

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

        if reviewer:
            key = f"r{report['number']}"
            if report["status"] == hallazgos.STATUS_NEW:
                if st.button("I am opening this report to review it", key=key + "open"):
                    hallazgos.add_event(report, hallazgos.STATUS_OPENED, reviewer)
                    st.rerun()
            else:
                with st.form(key + "form"):
                    verdict = st.selectbox("Verdict", hallazgos.VERDICTS, key=key + "v")
                    reason = st.text_area(
                        "Reason (which catalogue or check supports it)",
                        key=key + "t", max_chars=600,
                    )
                    if st.form_submit_button("Sign and publish verdict"):
                        if len(reason.strip()) < 15:
                            st.error("Please give a reason of at least 15 characters.")
                        else:
                            hallazgos.add_event(report, verdict, reviewer, reason)
                            st.rerun()

tema.pie()
