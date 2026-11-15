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
tema.portada()

SPACES = {"mine": "My reports", "desk": "Review desk", "top": "Candidates", "board": "All reports"}
TRACK = ["Reported", "Opened by a reviewer", "Verdict signed"]


def community_board(items):
    """Build and draw the two-column Community contributions leaderboard."""
    citizens, experts = {}, {}
    for rep in items:
        alias = str(rep.get("alias", "")).strip()
        if alias:
            citizens[alias] = citizens.get(alias, 0) + 1
        for event in rep.get("events", []):
            if event.get("type") in hallazgos.VERDICTS:
                who = str(event.get("by", "")).split(",")[0].strip()
                if who:
                    experts[who] = experts.get(who, 0) + 1
    c_rows = sorted(citizens.items(), key=lambda x: (-x[1], x[0].lower()))[:5]
    e_rows = sorted(experts.items(), key=lambda x: (-x[1], x[0].lower()))[:5]
    sample_used = False
    if len(c_rows) < 3:
        sample_used = True
        seen = {name.lower() for name, _ in c_rows}
        for name, count in tema.SAMPLE_CITIZENS:
            if name.lower() not in seen and len(c_rows) < 3:
                c_rows.append((name, count))
        c_rows.sort(key=lambda x: (-x[1], x[0].lower()))
    if len(e_rows) < 3:
        sample_used = True
        seen = {name.lower() for name, _ in e_rows}
        for name, count in tema.SAMPLE_EXPERTS:
            if name.lower() not in seen and len(e_rows) < 3:
                e_rows.append((name, count))
        e_rows.sort(key=lambda x: (-x[1], x[0].lower()))
    tema.contribuciones(c_rows, e_rows, usar_ejemplo=sample_used)


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

        if not reviewer:
            return
        key = f"r{report['number']}"
        if report["status"] == hallazgos.STATUS_NEW:
            if st.button("I am opening this report to review it", key=key + "open"):
                try:
                    hallazgos.add_event(report, hallazgos.STATUS_OPENED, reviewer)
                except Exception as error:
                    st.error(f"The review step could not be saved. Detail: {error}")
                else:
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
                        try:
                            hallazgos.add_event(report, verdict, reviewer, reason)
                        except Exception as error:
                            st.error(f"The verdict could not be published. Detail: {error}")
                        else:
                            st.rerun()


# ---------------------------------------------------------------- which space

params = st.query_params
start = params.get("space", "mine" if "claim" in params else "board")
tema.seccion(1, "Findings")
if st.session_state.get("space") not in SPACES:      # first time here in this visit
    st.session_state["space"] = start if start in SPACES else "board"
space = st.segmented_control(
    "Space", list(SPACES), format_func=SPACES.get, label_visibility="collapsed", key="space",
    on_change=lambda: st.session_state.setdefault("role", "tab")
    if hallazgos.nickname_of(hallazgos.current_user()) else None,
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
            "sign a verdict with your name. The desk opens for the team's reviewers list "
            "or after accreditation.</p></div>", unsafe_allow_html=True)
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
    community_board(reports)
    tema.seccion(2, "Confirmed candidates")
    if not winners:
        st.info("No candidates yet. When a reviewer marks a report as a candidate, it appears here.")
    else:
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
    community_board(reports)

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
    tema.pasos(hallazgos.AMATEUR_FLOW)
    if account:
        found = hallazgos.reports_of(account)
        rep = hallazgos.reputation_of(account, found)
        wait_seconds = hallazgos.cooldown_seconds_left(account, found)
        cd_text = f"Next report in {hallazgos.format_countdown(wait_seconds)}" if wait_seconds > 0 else None
        tema.tarjeta_reputacion(account["nick"], rep, cooldown_text=cd_text)
        if wait_seconds > 0 and hallazgos.is_team_reviewer(account):
            if st.button("Reset 24h cooldown (team demo)", key="reset_cd_mine"):
                st.session_state["skip_cooldown"] = True
                st.rerun()
        waiting = sum(r["status"] == hallazgos.STATUS_NEW for r in found)
        opened = sum(r["status"] == hallazgos.STATUS_OPENED for r in found)
        candidates = sum(r["status"] == hallazgos.VERDICTS[2] for r in found)
        columns = st.columns(4)
        columns[0].metric("My reports", len(found))
        columns[1].metric("Waiting or in review", waiting + opened)
        columns[2].metric("With a verdict", len(found) - waiting - opened)
        columns[3].metric("Candidates", candidates)
        with st.container(key="mine_cta"):
            left, right = st.columns([3, 1.3], vertical_alignment="center")
            left.markdown(
                '<p class="dz-cta-title">Ready to inspect a SPHEREx sequence?</p>'
                '<p class="dz-cta-line">Open one of the five challenge targets or enter any sky '
                'coordinate in the Viewer, compare epochs and publish what you find.</p>',
                unsafe_allow_html=True,
            )
            if right.button("Open the Viewer", key="go_viewer_mine", type="primary", use_container_width=True):
                st.switch_page("app.py")
        tema.seccion(2, "My submitted reports")
        if not found:
            st.info("You have not sent any report yet. Use “Open the Viewer” above and click “Report a finding” under a sequence.")
        with st.container(key="board"):
            for report in found:
                card(report, track=True)
                if report["status"] == hallazgos.STATUS_NEW:
                    st.caption("Nobody has opened this report yet. Reviewers are volunteers; come back later.")
                elif report["status"] == hallazgos.STATUS_OPENED:
                    st.caption("A reviewer is looking at this report. The verdict will appear here, signed.")
    else:
        st.info("Sign in with Google above to follow the reports you have sent and to publish new ones with your nickname.")

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
    reviewers = hallazgos.reviewers()
    by_email = hallazgos.reviewer_name(account) if by_account else None
    reviewer = by_email or reviewers.get(st.session_state.get("reviewer_code", ""))
    if by_account:
        st.write(
            "For the astronomers and domain experts who vet the reports. Every step is signed "
            "with the reviewer's public name, institution and ORCID iD or team credential."
        )
        tema.pasos(hallazgos.EXPERT_FLOW)
        if account and not reviewer:
            application = hallazgos.accreditation_of(account)
            ACCRED_TRACK = [
                "Application sent",
                "Manual verification by the team",
                "Accredited on Review Desk",
            ]
            tema.seccion(2, "Reviewer accreditation")
            if application and not st.session_state.get("edit_accreditation"):
                status_text = (
                    "Not approved" if application.get("status") == "rejected"
                    else "Pending manual verification"
                )
                with st.container(border=True, key="accred_status"):
                    head, badge = st.columns([3, 1])
                    head.markdown(
                        f'<span class="dz-rkind">{html.escape(application["signature"])}</span>'
                        f'<p class="dz-rby">{html.escape(application["institution"])} · '
                        f'Account nickname: <b>{html.escape(str(application.get("nick", account["nick"])))}</b> · '
                        f'Submitted {html.escape(application["at"])}</p>',
                        unsafe_allow_html=True,
                    )
                    badge.markdown(tema.estado(status_text, False), unsafe_allow_html=True)
                    step = 1 if application.get("status") == "rejected" else 2
                    st.markdown(tema.seguimiento(step, ACCRED_TRACK), unsafe_allow_html=True)
                    orcid_url = f"https://orcid.org/{html.escape(application['orcid'])}"
                    st.markdown(
                        f"**ORCID iD:** [{html.escape(application['orcid'])}]({orcid_url}) · "
                        f"**Reference publication (DOI / ADS):** `{html.escape(application['publication'])}` · "
                        f"**Specialty:** {html.escape(application['specialty'])}"
                    )
                    st.caption(f"Vetting protocol & catalogues declared: {application['note']}")
                    st.info(
                        "Your accreditation request is queued for manual verification by the team. "
                        "Once approved, this account opens the Review Desk automatically and your "
                        "public signature above will appear on every verdict you sign."
                    )
                    if st.button("Update application details", key="edit_accred_btn"):
                        st.session_state["edit_accreditation"] = True
                        st.rerun()
            else:
                with st.container(border=True, key="accred_form_box"):
                    st.markdown(
                        '<p class="dz-cta-title">Apply for reviewer accreditation (manual verification)</p>'
                        '<p class="dz-cta-line">Following the citizen-science vetting model of '
                        '<i>Backyard Worlds: Planet 9</i> (Kuchner et al. 2017, <i>ApJ Letters</i>, 840, L23) '
                        'and SIMBAD cross-identification practices (Ochsenbein et al. 2000, <i>A&amp;AS</i>, 143, 23), '
                        'candidate detections in infrared sky surveys require traceable expert cross-matching '
                        'against astrometric and photometric catalogues before follow-up. Complete the fields '
                        'below so that, once verified by the team, your expert signature is ready on the web '
                        'with no missing credentials.</p>',
                        unsafe_allow_html=True,
                    )
                    defaults = application or {}
                    with st.form("accreditation_form", border=False):
                        col1, col2 = st.columns(2)
                        signature = col1.text_input(
                            "Public signature (name and title as shown on verdicts)",
                            value=defaults.get("signature", ""),
                            max_chars=80,
                            placeholder="Dr. Elena Vega, Infrared Astronomer",
                        )
                        institution = col2.text_input(
                            "Institution, observatory or society",
                            value=defaults.get("institution", ""),
                            max_chars=100,
                            placeholder="Observatorio Astronómico de Quito — EPN",
                        )
                        col3, col4 = st.columns(2)
                        orcid = col3.text_input(
                            "ORCID iD (16-digit researcher identifier)",
                            value=defaults.get("orcid", ""),
                            max_chars=19,
                            placeholder="0000-0002-1825-0097",
                        )
                        publication = col4.text_input(
                            "Reference publication or catalogue entry (DOI or NASA ADS bibcode)",
                            value=defaults.get("publication", ""),
                            max_chars=140,
                            placeholder="10.3847/2041-8213/aa7200 or 2017ApJ...840L..23K",
                        )
                        specialty = st.selectbox(
                            "Primary vetting specialty",
                            hallazgos.SPECIALTIES,
                            index=hallazgos.SPECIALTIES.index(defaults["specialty"])
                            if defaults.get("specialty") in hallazgos.SPECIALTIES else 0,
                        )
                        note = st.text_area(
                            "Catalogues and checks you use to vet candidates (e.g. SIMBAD, Gaia DR3, AllWISE, artifact flags)",
                            value=defaults.get("note", ""),
                            max_chars=400,
                            height=90,
                            placeholder="Cross-matching astrometry in Gaia DR3 and SIMBAD within 2 arcmin, plus checking AllWISE/2MASS colours and bad-pixel masks.",
                        )
                        sent = st.form_submit_button("Submit accreditation request", type="primary")
                    if sent:
                        try:
                            problem = hallazgos.submit_accreditation(
                                account, signature, institution, orcid, publication, specialty, note
                            )
                        except Exception as error:
                            problem = f"The accreditation request could not be saved. Detail: {error}"
                        if problem:
                            st.error(problem)
                        else:
                            st.session_state.pop("edit_accreditation", None)
                            st.rerun()
            if reviewers:
                with st.expander("Already have a reviewer code from the team?"):
                    with st.form("signin_code"):
                        code = st.text_input("Reviewer code", type="password")
                        if st.form_submit_button("Open review desk", type="primary"):
                            if code in reviewers:
                                st.session_state["reviewer_code"] = code
                                st.rerun()
                            else:
                                st.error("Unknown code.")
        elif not account and not reviewer:
            st.info("Sign in with Google above to open the Review Desk or to apply for reviewer accreditation.")
            if reviewers:
                with st.expander("Already have a reviewer code from the team?"):
                    with st.form("signin_code_anon"):
                        code = st.text_input("Reviewer code", type="password")
                        if st.form_submit_button("Open review desk", type="primary"):
                            if code in reviewers:
                                st.session_state["reviewer_code"] = code
                                st.rerun()
                            else:
                                st.error("Unknown code.")
    if by_account and not reviewer:
        pass
    elif not reviewer:
        st.write(
            "For the astronomers who review the reports. The team gives each reviewer a "
            "personal code; every step you take is published with your name."
        )
        tema.pasos(hallazgos.EXPERT_FLOW)
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
        if not by_email:
            who, out = st.columns([4, 1], vertical_alignment="center")
            who.markdown(f'<div class="dz-who"><span>Signed in as</span>{html.escape(reviewer)}</div>',
                         unsafe_allow_html=True)
            if out.button("Leave review desk" if by_account else "Sign out", use_container_width=True):
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

        # Team reviewers can verify and approve pending accreditation requests right here
        if hallazgos.is_team_reviewer(account) or st.session_state.get("reviewer_code") in reviewers:
            pending_apps = [a for a in hallazgos.list_accreditations() if a.get("status") == "pending"]
            if pending_apps:
                with st.expander(f"Reviewer accreditation requests waiting for manual verification ({len(pending_apps)})", expanded=True):
                    for app in pending_apps:
                        with st.container(border=True, key=f"app_{app['id'][:10]}"):
                            st.markdown(
                                f"**{html.escape(app['signature'])}** — {html.escape(app['institution'])} "
                                f"(nickname `{html.escape(str(app.get('nick', '')))}`, {html.escape(app['at'])})"
                            )
                            st.markdown(
                                f"ORCID: [{html.escape(app['orcid'])}](https://orcid.org/{html.escape(app['orcid'])}) · "
                                f"Publication (DOI / ADS): `{html.escape(app['publication'])}` · "
                                f"Specialty: {html.escape(app['specialty'])}"
                            )
                            st.caption(f"Catalogues & checks: {app['note']}")
                            b_ok, b_no, _ = st.columns([1.8, 1.2, 2.6])
                            if b_ok.button("Approve as reviewer", key=f"ok_{app['id'][:10]}", type="primary", use_container_width=True):
                                try:
                                    hallazgos.decide_accreditation(app["id"], "approved", reviewer)
                                except Exception as error:
                                    st.error(f"Could not approve accreditation. Detail: {error}")
                                else:
                                    st.rerun()
                            if b_no.button("Dismiss", key=f"no_{app['id'][:10]}", use_container_width=True):
                                try:
                                    hallazgos.decide_accreditation(app["id"], "rejected", reviewer)
                                except Exception as error:
                                    st.error(f"Could not update accreditation. Detail: {error}")
                                else:
                                    st.rerun()

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
