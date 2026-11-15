# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""
My reports & Review desk (Tab 3):
  - My reports:   an amateur observer follows the reports they submitted, checks their
                  24-hour anti-spam cooldown, and sees their Turquoise 5-sided Star &
                  nomination rank (or follows reports with a claim code).
  - Review desk:  an astronomer or domain expert opens waiting reports from the queue,
                  cross-checks SIMBAD (2′), signs verdicts, sees their Spectral Violet
                  5-sided Star & nomination rank, or applies for manual reviewer accreditation.
"""

import html
from pathlib import Path
import re

import streamlit as st

import fresco

fresco.actualizar()

import hallazgos
import tema

st.set_page_config(page_title="HAWAPACHA — My reports & Review", page_icon=tema.ICON, layout="wide")

SPACES = {"mine": "My reports (Amateur)", "desk": "Review desk (Astronomer)"}
TRACK = ["Reported", "Opened by a reviewer", "Verdict signed"]

params = st.query_params
raw_space = params.get("space") or params.get("view")
if "claim" in params or raw_space in SPACES:
    param_target = "desk" if raw_space == "desk" else "mine"
    if st.session_state.get("_last_rev_param") != (raw_space, params.get("claim")):
        st.session_state["_last_rev_param"] = (raw_space, params.get("claim"))
        st.session_state["review_space"] = param_target
        st.session_state["space"] = param_target
        st.session_state["role"] = "expert" if param_target == "desk" else "amateur"
elif st.session_state.get("space") in SPACES and st.session_state.get("review_space") not in SPACES:
    st.session_state["review_space"] = st.session_state["space"]
elif st.session_state.get("review_space") not in SPACES:
    st.session_state["review_space"] = "mine"

tema.aplicar_tema()
tema.navegacion()
tema.portada()


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


# ---------------------------------------------------------------- which workspace

space = "desk" if tema._es_modo_experto() else "mine"
st.session_state["space"] = space
st.session_state["review_space"] = space

tema.seccion(1, "Review" if space == "desk" else "My reports")

try:
    reports = hallazgos.list_reports()
except Exception as error:
    st.error(f"The reports could not be loaded right now. Detail: {error}")
    st.stop()

# ---------------------------------------------------------------- account and role

account = None
if hallazgos.accounts_enabled():
    account = hallazgos.account_box(key="top_account", back=f"findings:{space}")


def choose(role, where):
    st.session_state["role"] = role
    st.session_state["space"] = where
    st.session_state["review_space"] = where


if not st.session_state.get("role") and not st.session_state.get("reviewer_code") and "claim" not in params and raw_space not in SPACES:
    tema.seccion(2, "How do you want to take part?")
    amateur, expert = st.columns(2, gap="large")
    with amateur.container(border=True, key="role_amateur"):
        st.markdown(
            '<div class="dz-role"><i>01</i><b>I am an amateur</b>'
            "<p>Look at the sequences, report what you notice, earn your Turquoise 5-sided "
            "Observer Star and follow your reports until a reviewer signs a verdict.</p></div>",
            unsafe_allow_html=True,
        )
        st.button("Go to my reports", key="role_a", type="primary", use_container_width=True,
                  on_click=choose, args=("amateur", "mine"))
    with expert.container(border=True, key="role_expert"):
        st.markdown(
            '<div class="dz-role"><i>02</i><b>I am an astronomer or expert</b>'
            "<p>Open the reports waiting in the queue, check them against catalogues, sign "
            "verdicts with your name and earn your Spectral Violet 5-sided Astronomer Star.</p></div>",
            unsafe_allow_html=True,
        )
        st.button("Go to the review desk", key="role_e", type="primary", use_container_width=True,
                  on_click=choose, args=("expert", "desk"))
    st.caption("You can switch role at any time from your profile badge in the top-right corner.")
    tema.pie()
    st.stop()

# ---------------------------------------------------------------- my reports (amateur)

if space == "mine" and hallazgos.accounts_enabled():
    st.write(
        "Follow the reports you sent. Your account has one nickname, which nobody else can "
        "use, and every report you publish is signed with it."
    )
    tema.pasos(hallazgos.AMATEUR_FLOW)
    if account:
        found = hallazgos.reports_of(account)
        rep = hallazgos.reputation_of(account, reports)
        wait_seconds = hallazgos.cooldown_seconds_left(account, found)
        cd_text = f"Next report in {hallazgos.format_countdown(wait_seconds)}" if wait_seconds > 0 else None
        tema.tarjeta_reputacion(account["nick"], rep, cooldown_text=cd_text)
        if wait_seconds > 0 and hallazgos.is_team_reviewer(account):
            if st.button("Reset 24h cooldown (team demo)", key="reset_cd_mine"):
                st.session_state["skip_cooldown"] = True
                st.session_state.pop("reports_sent", None)
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
        st.info("Sign in with Google above to follow the reports you have sent, see your 5-sided Observer Star and publish new reports.")

elif space == "mine":
    st.write(
        "Follow the reports you sent. The **claim code** you received when you published "
        "a report is your key. Nicknames can be copied by anyone; a claim code cannot."
    )
    initial_claim = params.get("claim", "") or st.session_state.pop("claim_param", "")
    typed = st.text_input(
        "Your claim code (several codes: separate them with a space)",
        value=initial_claim, placeholder="XXXX-XXXX",
    )
    codes = [c for c in re.split(r"[\s,;]+", typed.strip()) if c]
    if codes:
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

# ---------------------------------------------------------------- review desk (astronomer)

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
                            max_chars=45,
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
            with st.expander("Team DecZero & Reviewer special access code", expanded=False):
                st.caption(
                    "Members of Team DecZero or invited guest reviewers can enter their special "
                    "access code here to unlock the manual accreditation verification panel and the Review Desk."
                )
                with st.form("signin_code"):
                    code = st.text_input("Special access / Reviewer code", type="password", placeholder="DECZERO-2026")
                    if st.form_submit_button("Unlock Team DecZero / Review Desk", type="primary"):
                        canonical = hallazgos.check_reviewer_code(code)
                        if canonical:
                            st.session_state["reviewer_code"] = canonical
                            st.rerun()
                        else:
                            st.error("Unknown access code.")
        elif not account and not reviewer:
            st.info("Sign in with Google above to open the Review Desk or to apply for reviewer accreditation, or use a Team DecZero special access code below.")
            with st.expander("Team DecZero & Reviewer special access code", expanded=True):
                st.caption(
                    "Members of Team DecZero or invited guest reviewers can enter their special "
                    "access code here to unlock the manual accreditation verification panel and the Review Desk."
                )
                with st.form("signin_code_anon"):
                    code = st.text_input("Special access / Reviewer code", type="password", placeholder="DECZERO-2026")
                    if st.form_submit_button("Unlock Team DecZero / Review Desk", type="primary"):
                        canonical = hallazgos.check_reviewer_code(code)
                        if canonical:
                            st.session_state["reviewer_code"] = canonical
                            st.rerun()
                        else:
                            st.error("Unknown access code.")
    if by_account and not reviewer:
        pass
    elif not reviewer:
        st.write(
            "For the astronomers and Team DecZero members who review the reports. Enter your "
            "special access code below; every step you take is published with your credential."
        )
        tema.pasos(hallazgos.EXPERT_FLOW)
        with st.form("signin"):
            code = st.text_input("Special access / Reviewer code", type="password", placeholder="DECZERO-2026")
            if st.form_submit_button("Unlock Review Desk", type="primary"):
                canonical = hallazgos.check_reviewer_code(code)
                if canonical:
                    st.session_state["reviewer_code"] = canonical
                    st.rerun()
                else:
                    st.error("Unknown access code.")
        st.caption(
            "You stay signed in while this browser tab is open, also if you go to the viewer "
            "and come back. Nothing is stored on your device. If you are an astronomer and "
            "want to review, write to the team."
        )
    else:
        erep = hallazgos.expert_reputation_of(reviewer, reports)
        is_team_admin = hallazgos.is_deczero_team(account)
        if not by_email:
            who, out = st.columns([4, 1], vertical_alignment="center")
            e_title = tema.nombramiento_estrella(erep["sides"], kind="expert")
            admin_pill = ' <em class="dz-nom-pill">TEAM DECZERO ADMIN</em>' if is_team_admin else ""
            who.markdown(
                f'<div class="dz-who"><span>Signed in as</span>'
                f'<b>{html.escape(reviewer)}</b> '
                f'{tema.estrella_svg(erep["sides"], 24, kind="expert")} '
                f'<em class="dz-nom-pill expert">{e_title} · {erep["sides"]}/5</em>{admin_pill}</div>',
                unsafe_allow_html=True,
            )
            if out.button("Leave review desk" if by_account else "Sign out", use_container_width=True):
                st.session_state.pop("reviewer_code", None)
                st.rerun()
        tema.tarjeta_reputacion_experto(reviewer, erep)

        # Team DecZero Manual Accreditation Verification Panel
        if is_team_admin:
            all_apps = hallazgos.list_accreditations()
            pending_apps = [a for a in all_apps if a.get("status") == "pending"]
            approved_apps = [a for a in all_apps if a.get("status") == "approved"]
            decided_apps = [a for a in all_apps if a.get("status") != "pending"]

            tema.seccion(2, "Team DecZero: manual accreditation verification")
            st.write(
                "Special access panel for **Team DecZero**. Verify astronomer accreditation "
                "requests by checking their **ORCID iD** and **DOI / NASA ADS publication**, "
                "then approve or dismiss them with one click."
            )
            ac_cols = st.columns(3)
            ac_cols[0].metric("Pending verification", len(pending_apps))
            ac_cols[1].metric("Approved astronomers", len(approved_apps))
            ac_cols[2].metric("Total applications", len(all_apps))

            def _render_app_card(app, section_prefix="pend"):
                pub_raw = str(app.get("publication", "")).strip()
                if pub_raw.startswith("10."):
                    pub_url = f"https://doi.org/{html.escape(pub_raw)}"
                else:
                    pub_url = f"https://ui.adsabs.harvard.edu/abs/{html.escape(pub_raw)}/abstract"
                stat = str(app.get("status", "pending")).lower()
                stat_label = (
                    "Approved reviewer" if stat == "approved"
                    else ("Dismissed" if stat == "rejected" else "Pending manual verification")
                )
                with st.container(border=True, key=f"app_{section_prefix}_{app['id'][:10]}"):
                    h_col, s_col = st.columns([3, 1])
                    h_col.markdown(
                        f"**{html.escape(app['signature'])}** — {html.escape(app['institution'])}  \n"
                        f"Account nickname: `{html.escape(str(app.get('nick', '')))}` · Submitted {html.escape(app['at'])}"
                    )
                    s_col.markdown(tema.estado(stat_label, stat == "approved"), unsafe_allow_html=True)
                    st.markdown(
                        f"**ORCID iD:** [{html.escape(app['orcid'])}](https://orcid.org/{html.escape(app['orcid'])}) · "
                        f"**Publication (DOI / ADS):** [{html.escape(pub_raw)}]({pub_url}) · "
                        f"**Specialty:** {html.escape(app['specialty'])}"
                    )
                    st.caption(f"Declared catalogues & checks: {app['note']}")
                    b_ok, b_no, _ = st.columns([1.8, 1.4, 2.4])
                    if stat != "approved":
                        if b_ok.button("Approve as reviewer", key=f"ok_{section_prefix}_{app['id'][:10]}", type="primary", use_container_width=True):
                            try:
                                hallazgos.decide_accreditation(app["id"], "approved", reviewer)
                            except Exception as error:
                                st.error(f"Could not approve accreditation. Detail: {error}")
                            else:
                                st.rerun()
                    if stat != "rejected":
                        btn_lbl = "Revoke accreditation" if stat == "approved" else "Dismiss"
                        if b_no.button(btn_lbl, key=f"no_{section_prefix}_{app['id'][:10]}", use_container_width=True):
                            try:
                                hallazgos.decide_accreditation(app["id"], "rejected", reviewer)
                            except Exception as error:
                                st.error(f"Could not update accreditation. Detail: {error}")
                            else:
                                st.rerun()

            if pending_apps:
                for app in pending_apps:
                    _render_app_card(app, "pend")
            else:
                st.info(
                    "No accreditation requests are currently waiting for manual verification. "
                    "When a researcher submits the accreditation form on the Review Desk, their "
                    "ORCID link, DOI/ADS citation and 1-click approval buttons appear right here."
                )
            if decided_apps:
                with st.expander(f"Previously reviewed accreditation applications ({len(decided_apps)})"):
                    for app in decided_apps:
                        _render_app_card(app, "hist")

        def by_me(report, kinds):
            full_r = str(reviewer or "").strip().lower()
            short_r = full_r.split(",")[0].strip()
            for e in report.get("events", []):
                if e.get("type") in kinds:
                    by = str(e.get("by", "")).strip().lower()
                    by_s = by.split(",")[0].strip()
                    if full_r and (by == full_r or (short_r and by_s == short_r)):
                        return True
            return False

        queue = sorted((r for r in reports if r["status"] == hallazgos.STATUS_NEW), key=lambda r: r["number"])
        in_progress = [r for r in reports if r["status"] == hallazgos.STATUS_OPENED]
        mine_open = [r for r in in_progress if by_me(r, [hallazgos.STATUS_OPENED])]
        others_open = [r for r in in_progress if r not in mine_open]
        signed = [r for r in reports if r["status"] in hallazgos.VERDICTS and by_me(r, hallazgos.VERDICTS)]

        sec_base = 3 if is_team_admin else 2
        tema.seccion(sec_base, "Citizen report review queue")
        columns = st.columns(3)
        columns[0].metric("Waiting for a reviewer", len(queue))
        columns[1].metric("Opened by me", len(mine_open))
        columns[2].metric("Verdicts I signed", len(signed))

        with st.container(key="board"):
            tema.seccion(sec_base + 1, "Opened by me: verdict pending")
            if not mine_open:
                st.caption("Nothing here. Open a report from the queue below.")
            for report in mine_open:
                card(report, reviewer)
            tema.seccion(sec_base + 2, "Queue: oldest first")
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

    with st.expander("Where do reports & manual accreditation requests go? (Team DecZero & GitHub architecture)"):
        st.markdown(
            "- **Citizen finding reports (`[Finding]`):** Every report submitted from the Viewer creates an immutable "
            "GitHub Issue in [`JMVP0016/DECZERO/issues`](https://github.com/JMVP0016/DECZERO/issues) with a readable "
            "summary, SIMBAD coordinates, and a hidden JSON block (`<!-- hawapacha-data ... -->`). When an astronomer "
            "opens a report or signs a verdict, a signed GitHub Issue comment is appended to that exact issue.\n"
            "- **Manual astronomer accreditation requests (`[Accounts]`):** Every request submitted via the accreditation "
            "form is stored in the master `[Accounts] HAWAPACHA nicknames` GitHub Issue with a live Markdown table "
            "(Nickname, Signature, Institution, ORCID iD, DOI/ADS publication, Status) and posts a notification comment "
            "so Team DecZero receives an instant GitHub alert.\n"
            "- **Team DecZero special access:** Core team members (`[REVIEWER_EMAILS]` via Google OAuth or `[REVIEWERS]` "
            "codes) see pending accreditation requests right above the review queue and can approve or dismiss them with "
            "one click."
        )
        pdf_guide = Path(__file__).resolve().parent.parent / "GUIA_REVISION_MANUAL_Y_REPOSITORIO_DECZERO.pdf"
        if pdf_guide.is_file():
            st.download_button(
                "Download Team DecZero Manual Review & Repository Guide (PDF)",
                data=pdf_guide.read_bytes(),
                file_name="GUIA_REVISION_MANUAL_Y_REPOSITORIO_DECZERO.pdf",
                mime="application/pdf",
                key="dl_deczero_guide_pdf",
            )

tema.pie()
