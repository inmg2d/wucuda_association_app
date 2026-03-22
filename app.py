from __future__ import annotations

import io
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

import database as db

st.set_page_config(
    page_title="WUCUDA Association Manager",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)


db.init_db()


st.markdown(
    """
    <style>
        .block-container {padding-top: 1.2rem;}
        .small-note {font-size: 0.90rem; color: #555;}
    </style>
    """,
    unsafe_allow_html=True,
)



def fcfa(value: Any) -> str:
    try:
        return f"{float(value):,.0f} FCFA"
    except (TypeError, ValueError):
        return "0 FCFA"



def safe_add_years(input_date: date, years: int) -> date:
    try:
        return input_date.replace(year=input_date.year + years)
    except ValueError:
        return input_date + timedelta(days=365 * years)



def excel_bytes(df: pd.DataFrame, sheet_name: str = "Report") -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31] or "Report")
    output.seek(0)
    return output.read()



def render_download_buttons(df: pd.DataFrame, base_name: str, sheet_name: str = "Report") -> None:
    if df.empty:
        return
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    xlsx_bytes = excel_bytes(df, sheet_name=sheet_name)
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name=f"{base_name}.csv",
            mime="text/csv",
            key=f"csv_{base_name}",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "Download Excel",
            data=xlsx_bytes,
            file_name=f"{base_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"xlsx_{base_name}",
            use_container_width=True,
        )



def table_or_info(df: pd.DataFrame, message: str = "No records available yet.") -> None:
    if df.empty:
        st.info(message)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)



def get_branch_choice(label: str, include_national: bool = True, key: str | None = None) -> int | None:
    branches = db.get_branch_options()
    options: dict[str, int | None] = {}
    if include_national:
        options["National / Not linked to one branch"] = None
    for item in branches:
        options[f"{item['name']} - {item['city']}"] = item["id"]
    selected = st.selectbox(label, options=list(options.keys()), key=key)
    return options[selected]



def get_member_choice(label: str, active_only: bool = False, key: str | None = None) -> int:
    members = db.get_member_options(active_only=active_only)
    options = {f"{item['membership_no']} - {item['full_name']} ({item['branch_name']})": item["id"] for item in members}
    selected = st.selectbox(label, options=list(options.keys()), key=key)
    return options[selected]



def get_election_choice(label: str, allow_none: bool = True, key: str | None = None) -> int | None:
    elections = db.get_election_options()
    options: dict[str, int | None] = {}
    if allow_none:
        options["Not linked to a specific election"] = None
    for item in elections:
        options[f"{item['title']} - {item['election_date']} ({item['status']})"] = item["id"]
    selected = st.selectbox(label, options=list(options.keys()), key=key)
    return options[selected]



def get_project_choice(label: str, key: str | None = None) -> int:
    projects = db.get_project_options()
    options = {f"{item['title']} ({item['status']})": item["id"] for item in projects}
    selected = st.selectbox(label, options=list(options.keys()), key=key)
    return options[selected]



def dashboard_page(report_year: int, settings: dict[str, str]) -> None:
    st.title("WUCUDA Association Dashboard")
    st.caption(
        f"Patron: {settings.get('patron', 'The King of Babessi')} | "
        f"Reference year: {report_year}"
    )

    metrics = db.get_dashboard_metrics(report_year)
    branch_report = db.get_branch_summary_report(report_year)
    member_compliance = db.get_member_compliance_report(report_year)
    project_report = db.get_projects_report("All")
    executive_expiry = db.get_executive_expiry_report(180)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total branches", metrics["total_branches"])
    c2.metric("Total members", metrics["total_members"])
    c3.metric("Active members", metrics["active_members"])
    c4.metric("Members paid this year", metrics["members_paid_this_year"])

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Member dues collected", fcfa(metrics["member_dues_collected"]))
    c6.metric("Branch regulations collected", fcfa(metrics["branch_regulations_collected"]))
    c7.metric("Active projects", metrics["active_projects"])
    c8.metric("Planned or open elections", metrics["planned_or_open_elections"])

    expected_member_due = float(settings.get("member_annual_due", "2000"))
    expected_branch_due = float(settings.get("branch_annual_regulation", "15000"))
    estimated_total_members = int(settings.get("estimated_total_members", "30000"))
    major_event_expected_attendance = int(settings.get("major_event_expected_attendance", "1500"))

    total_member_due_expected = member_compliance["annual_due"].sum() if not member_compliance.empty else 0
    total_branch_due_expected = branch_report["annual_regulation"].sum() if not branch_report.empty else 0
    outstanding_member_due = max(total_member_due_expected - metrics["member_dues_collected"], 0)
    outstanding_branch_due = max(total_branch_due_expected - metrics["branch_regulations_collected"], 0)

    st.info(
        f"Configured annual member due: {fcfa(expected_member_due)} | "
        f"Configured branch regulation: {fcfa(expected_branch_due)} | "
        f"Planned large event capacity: about {major_event_expected_attendance:,} people | "
        f"Estimated association size: about {estimated_total_members:,} members."
    )

    tab1, tab2, tab3 = st.tabs(["Branch Snapshot", "Finance Snapshot", "Election Readiness"])

    with tab1:
        if not branch_report.empty:
            st.subheader("Branch summary")
            st.dataframe(branch_report, use_container_width=True, hide_index=True)
            chart_df = branch_report.set_index("branch_name")[["total_members", "members_paid"]]
            st.bar_chart(chart_df)
        else:
            st.info("No branch data available.")

    with tab2:
        x1, x2, x3, x4 = st.columns(4)
        x1.metric("Expected member dues", fcfa(total_member_due_expected))
        x2.metric("Outstanding member dues", fcfa(outstanding_member_due))
        x3.metric("Expected branch regulations", fcfa(total_branch_due_expected))
        x4.metric("Outstanding branch regulations", fcfa(outstanding_branch_due))
        if not member_compliance.empty:
            st.subheader("Member payment status")
            status_count = (
                member_compliance.groupby("payment_status").size().rename("count").to_frame()
            )
            st.bar_chart(status_count)

    with tab3:
        if executive_expiry.empty:
            st.success("No executive term is due to expire within the next 180 days.")
        else:
            st.warning("Some executive terms are approaching expiry. Plan elections and handover on time.")
            st.dataframe(executive_expiry, use_container_width=True, hide_index=True)
        if not project_report.empty:
            st.subheader("Projects under implementation")
            st.dataframe(project_report[[
                "title", "category", "supervising_branch", "status", "budget", "amount_spent", "progress_percent"
            ]], use_container_width=True, hide_index=True)



def branches_page(default_branch_regulation: float) -> None:
    st.title("Branches")
    st.write("Register city branches and track their annual association regulation payments.")

    with st.expander("Add a new branch", expanded=False):
        with st.form("branch_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Branch name", placeholder="WUCUDA Yaounde")
                city = st.text_input("City", placeholder="Yaounde")
                region = st.text_input("Region", placeholder="Centre")
                contact_person = st.text_input("Contact person")
            with col2:
                phone = st.text_input("Phone")
                annual_regulation = st.number_input(
                    "Annual branch regulation (FCFA)",
                    min_value=0.0,
                    value=float(default_branch_regulation),
                    step=1000.0,
                )
                status = st.selectbox("Status", ["Active", "Inactive"])
            submitted = st.form_submit_button("Save branch", use_container_width=True)
            if submitted:
                if not name.strip() or not city.strip():
                    st.error("Branch name and city are required.")
                else:
                    try:
                        db.create_branch(
                            name=name.strip(),
                            city=city.strip(),
                            region=region.strip(),
                            contact_person=contact_person.strip(),
                            phone=phone.strip(),
                            annual_regulation=annual_regulation,
                            status=status,
                        )
                        st.success(f"Branch '{name}' saved successfully.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not save branch: {exc}")

    branches_df = db.get_branches_df()
    st.subheader("Registered branches")
    table_or_info(branches_df, "No branches have been registered yet.")
    render_download_buttons(branches_df, "wucuda_branches", "Branches")



def members_page(default_member_due: float) -> None:
    st.title("Members")
    st.write("Register members, assign them to branches, and keep the membership list organized.")

    with st.expander("Add a new member", expanded=False):
        with st.form("member_form"):
            c1, c2 = st.columns(2)
            with c1:
                full_name = st.text_input("Full name")
                gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])
                phone = st.text_input("Phone")
                email = st.text_input("Email")
                occupation = st.text_input("Occupation")
            with c2:
                city = st.text_input("City")
                branch_id = get_branch_choice("Branch", include_national=True, key="member_branch")
                joined_on = st.date_input("Date joined", value=date.today())
                status = st.selectbox("Membership status", ["Active", "Inactive", "Suspended"])
                annual_due = st.number_input(
                    "Annual member due (FCFA)",
                    min_value=0.0,
                    value=float(default_member_due),
                    step=500.0,
                )
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Save member", use_container_width=True)
            if submitted:
                if not full_name.strip():
                    st.error("Member full name is required.")
                else:
                    try:
                        membership_no = db.create_member(
                            full_name=full_name.strip(),
                            gender=gender,
                            phone=phone.strip(),
                            email=email.strip(),
                            occupation=occupation.strip(),
                            city=city.strip(),
                            branch_id=branch_id,
                            joined_on=joined_on.isoformat(),
                            status=status,
                            annual_due=annual_due,
                            notes=notes.strip(),
                        )
                        st.success(f"Member saved successfully with membership number {membership_no}.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not save member: {exc}")

    members_df = db.get_members_df()
    st.subheader("Membership register")
    search_text = st.text_input("Search members by name, membership number, phone or email")
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        branch_filter = st.selectbox(
            "Filter by branch",
            ["All"] + sorted(members_df["branch_name"].dropna().unique().tolist()) if not members_df.empty else ["All"],
        )
    with filter_col2:
        status_filter = st.selectbox(
            "Filter by status",
            ["All", "Active", "Inactive", "Suspended"],
        )
    filtered_df = members_df.copy()
    if search_text.strip() and not filtered_df.empty:
        search_value = search_text.strip().lower()
        filtered_df = filtered_df[
            filtered_df.apply(
                lambda row: search_value in " ".join(str(value).lower() for value in row.values),
                axis=1,
            )
        ]
    if branch_filter != "All" and not filtered_df.empty:
        filtered_df = filtered_df[filtered_df["branch_name"] == branch_filter]
    if status_filter != "All" and not filtered_df.empty:
        filtered_df = filtered_df[filtered_df["status"] == status_filter]

    table_or_info(filtered_df, "No members match the selected filters.")
    render_download_buttons(filtered_df, "wucuda_members", "Members")



def finance_page(report_year: int, default_member_due: float, default_branch_regulation: float) -> None:
    st.title("Finance")
    st.write("Record member annual dues and branch regulations, then review transactions for the year.")

    metrics = db.get_dashboard_metrics(report_year)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Members paid", metrics["members_paid_this_year"])
    c2.metric("Branches paid", metrics["branches_paid_this_year"])
    c3.metric("Member dues collected", fcfa(metrics["member_dues_collected"]))
    c4.metric("Branch regulations collected", fcfa(metrics["branch_regulations_collected"]))

    tab1, tab2, tab3 = st.tabs(["Record Member Payment", "Record Branch Payment", "Transactions"])

    with tab1:
        with st.form("member_payment_form"):
            member_id = get_member_choice("Member", active_only=False, key="member_payment_member")
            col1, col2, col3 = st.columns(3)
            with col1:
                payment_year = st.number_input("Payment year", min_value=2000, value=report_year, step=1)
                amount = st.number_input("Amount (FCFA)", min_value=0.0, value=float(default_member_due), step=500.0)
            with col2:
                date_paid = st.date_input("Date paid", value=date.today())
                payment_type = st.selectbox("Payment type", ["Annual Due", "Contribution", "Penalty", "Other"])
            with col3:
                method = st.selectbox("Method", ["Cash", "Mobile Money", "Bank Transfer", "Cheque", "Other"])
                reference = st.text_input("Reference")
            notes = st.text_area("Notes", key="member_payment_notes")
            submitted = st.form_submit_button("Save member payment", use_container_width=True)
            if submitted:
                try:
                    db.record_member_payment(
                        member_id=member_id,
                        payment_year=int(payment_year),
                        amount=amount,
                        date_paid=date_paid.isoformat(),
                        payment_type=payment_type,
                        method=method,
                        reference=reference.strip(),
                        notes=notes.strip(),
                    )
                    st.success("Member payment recorded successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not record payment: {exc}")

    with tab2:
        with st.form("branch_payment_form"):
            branch_id = get_branch_choice("Branch", include_national=False, key="branch_payment_branch")
            col1, col2, col3 = st.columns(3)
            with col1:
                payment_year = st.number_input("Regulation year", min_value=2000, value=report_year, step=1, key="branch_year")
                amount = st.number_input("Amount (FCFA)", min_value=0.0, value=float(default_branch_regulation), step=1000.0, key="branch_amount")
            with col2:
                date_paid = st.date_input("Date paid", value=date.today(), key="branch_date")
                method = st.selectbox("Method", ["Cash", "Mobile Money", "Bank Transfer", "Cheque", "Other"], key="branch_method")
            with col3:
                reference = st.text_input("Reference", key="branch_reference")
                notes = st.text_area("Notes", key="branch_notes")
            submitted = st.form_submit_button("Save branch payment", use_container_width=True)
            if submitted:
                try:
                    db.record_branch_payment(
                        branch_id=branch_id,
                        payment_year=int(payment_year),
                        amount=amount,
                        date_paid=date_paid.isoformat(),
                        method=method,
                        reference=reference.strip(),
                        notes=notes.strip(),
                    )
                    st.success("Branch payment recorded successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not record branch payment: {exc}")

    with tab3:
        member_payments_df = db.get_member_payments_df(report_year)
        branch_payments_df = db.get_branch_payments_df(report_year)
        transaction_df = db.get_finance_transactions_report(report_year)
        st.subheader(f"Member payments in {report_year}")
        table_or_info(member_payments_df, "No member payments recorded for this year.")
        render_download_buttons(member_payments_df, f"member_payments_{report_year}", "MemberPayments")
        st.subheader(f"Branch payments in {report_year}")
        table_or_info(branch_payments_df, "No branch payments recorded for this year.")
        render_download_buttons(branch_payments_df, f"branch_payments_{report_year}", "BranchPayments")
        st.subheader(f"All finance transactions in {report_year}")
        table_or_info(transaction_df, "No transactions recorded for this year.")
        render_download_buttons(transaction_df, f"finance_transactions_{report_year}", "Transactions")



def elections_page(term_years: int, default_attendance: int) -> None:
    st.title("Elections")
    st.write("Prepare elections, register candidates, and keep official election records.")

    tab1, tab2, tab3 = st.tabs(["Schedule Election", "Register Candidate", "Election Records"])

    with tab1:
        with st.form("election_form"):
            c1, c2 = st.columns(2)
            with c1:
                title = st.text_input("Election title", value="WUCUDA National Elections")
                level = st.selectbox("Level", ["National", "Branch"])
                branch_id = None
                if level == "Branch":
                    branch_id = get_branch_choice("Branch concerned", include_national=False, key="election_branch")
                election_date = st.date_input("Election date", value=date.today() + timedelta(days=60))
                venue = st.text_input("Venue", value="Babessi Community Hall")
            with c2:
                expected_attendance = st.number_input(
                    "Expected attendance",
                    min_value=0,
                    value=int(default_attendance),
                    step=50,
                )
                configured_term_years = st.number_input(
                    "Term of office (years)",
                    min_value=1,
                    value=int(term_years),
                    step=1,
                )
                status = st.selectbox("Election status", ["Planned", "Open", "Closed", "Completed"])
                notes = st.text_area("Notes")
            submitted = st.form_submit_button("Save election", use_container_width=True)
            if submitted:
                if not title.strip():
                    st.error("Election title is required.")
                else:
                    try:
                        db.create_election(
                            title=title.strip(),
                            level=level,
                            branch_id=branch_id,
                            election_date=election_date.isoformat(),
                            venue=venue.strip(),
                            expected_attendance=int(expected_attendance),
                            term_years=int(configured_term_years),
                            status=status,
                            notes=notes.strip(),
                        )
                        st.success("Election saved successfully.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not save election: {exc}")

    with tab2:
        if not db.get_election_options() or not db.get_member_options():
            st.info("You need at least one election and one member before registering candidates.")
        else:
            with st.form("candidate_form"):
                election_id = get_election_choice("Election", allow_none=False, key="candidate_election")
                member_id = get_member_choice("Member", active_only=True, key="candidate_member")
                col1, col2 = st.columns(2)
                with col1:
                    position = st.text_input("Position", placeholder="National President")
                    votes = st.number_input("Votes", min_value=0, value=0, step=1)
                with col2:
                    status = st.selectbox("Clearance status", ["Cleared", "Pending", "Disqualified"])
                    manifesto = st.text_area("Manifesto / remarks")
                submitted = st.form_submit_button("Register candidate", use_container_width=True)
                if submitted:
                    if not position.strip():
                        st.error("Position is required.")
                    else:
                        try:
                            db.register_candidate(
                                election_id=int(election_id),
                                member_id=member_id,
                                position=position.strip(),
                                manifesto=manifesto.strip(),
                                votes=int(votes),
                                status=status,
                            )
                            st.success("Candidate registered successfully.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Could not register candidate: {exc}")

    with tab3:
        elections_df = db.get_elections_df()
        candidates_df = db.get_candidates_df()
        st.subheader("Election schedule")
        table_or_info(elections_df, "No election records available yet.")
        render_download_buttons(elections_df, "wucuda_elections", "Elections")
        st.subheader("Candidates")
        table_or_info(candidates_df, "No candidates registered yet.")
        render_download_buttons(candidates_df, "wucuda_candidates", "Candidates")



def executives_page(term_years: int) -> None:
    st.title("Executives")
    st.write("Track elected officers, their offices, and their three-year terms.")

    expiring_df = db.get_executive_expiry_report(180)
    if expiring_df.empty:
        st.success("No executive term expires within the next 180 days.")
    else:
        st.warning("Some executive terms are expiring soon. They appear below.")
        st.dataframe(expiring_df, use_container_width=True, hide_index=True)

    with st.expander("Register executive term", expanded=False):
        if not db.get_member_options():
            st.info("Please add members before recording executive terms.")
        else:
            with st.form("executive_form"):
                col1, col2 = st.columns(2)
                with col1:
                    level = st.selectbox("Level", ["National", "Branch"])
                    branch_id = None
                    if level == "Branch":
                        branch_id = get_branch_choice("Branch", include_national=False, key="exec_branch")
                    office_name = st.text_input("Office name", placeholder="National Secretary")
                    member_id = get_member_choice("Officer", active_only=True, key="exec_member")
                    linked_election_id = get_election_choice("Linked election", allow_none=True, key="exec_election")
                with col2:
                    start_date = st.date_input("Start date", value=date.today())
                    end_date = st.date_input(
                        "End date",
                        value=safe_add_years(date.today(), int(term_years)),
                    )
                    status = st.selectbox("Status", ["Serving", "Completed", "Vacant"])
                    notes = st.text_area("Notes", key="exec_notes")
                submitted = st.form_submit_button("Save executive term", use_container_width=True)
                if submitted:
                    if not office_name.strip():
                        st.error("Office name is required.")
                    elif end_date <= start_date:
                        st.error("End date must be after the start date.")
                    else:
                        try:
                            db.create_executive_term(
                                level=level,
                                branch_id=branch_id,
                                office_name=office_name.strip(),
                                member_id=member_id,
                                start_date=start_date.isoformat(),
                                end_date=end_date.isoformat(),
                                election_id=linked_election_id,
                                status=status,
                                notes=notes.strip(),
                            )
                            st.success("Executive term saved successfully.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Could not save executive term: {exc}")

    executives_df = db.get_executives_df()
    st.subheader("Executive register")
    table_or_info(executives_df, "No executive terms have been recorded yet.")
    render_download_buttons(executives_df, "wucuda_executives", "Executives")



def agm_page(default_attendance: int) -> None:
    st.title("Annual General Assembly")
    st.write("Record AGM planning details, venue information, and attendance records.")

    with st.expander("Add AGM record", expanded=False):
        with st.form("agm_form"):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Meeting title", value="WUCUDA Annual General Assembly")
                meeting_date = st.date_input("Meeting date", value=date.today() + timedelta(days=30))
                venue = st.text_input("Venue", value="Babessi Community Hall")
            with col2:
                expected_attendance = st.number_input(
                    "Expected attendance",
                    min_value=0,
                    value=int(default_attendance),
                    step=50,
                )
                attendance_not_yet_taken = st.checkbox("Actual attendance not yet available", value=True)
                actual_attendance = None
                if not attendance_not_yet_taken:
                    actual_attendance = st.number_input("Actual attendance", min_value=0, value=0, step=10)
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Save AGM record", use_container_width=True)
            if submitted:
                if not title.strip():
                    st.error("Meeting title is required.")
                else:
                    try:
                        db.create_agm(
                            title=title.strip(),
                            meeting_date=meeting_date.isoformat(),
                            venue=venue.strip(),
                            expected_attendance=int(expected_attendance),
                            actual_attendance=int(actual_attendance) if actual_attendance is not None else None,
                            notes=notes.strip(),
                        )
                        st.success("AGM record saved successfully.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not save AGM record: {exc}")

    agm_df = db.get_agm_df()
    st.subheader("AGM records")
    table_or_info(agm_df, "No AGM records available yet.")
    render_download_buttons(agm_df, "wucuda_agm", "AGM")



def projects_page() -> None:
    st.title("Projects")
    st.write("Register development projects, manage budgets, and track implementation progress in Babessi.")

    projects_df = db.get_projects_df()
    total_budget = float(projects_df["budget"].sum()) if not projects_df.empty else 0
    total_spent = float(projects_df["amount_spent"].sum()) if not projects_df.empty else 0
    active_projects = int((projects_df["status"] == "Active").sum()) if not projects_df.empty else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total project budget", fcfa(total_budget))
    c2.metric("Amount spent", fcfa(total_spent))
    c3.metric("Active projects", active_projects)

    tab1, tab2, tab3 = st.tabs(["Register Project", "Progress Updates", "Project Registers"])

    with tab1:
        with st.form("project_form"):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Project title")
                category = st.text_input("Category", placeholder="Water Supply")
                location = st.text_input("Location", placeholder="Babessi Central")
                branch_id = get_branch_choice("Supervising branch", include_national=True, key="project_branch")
                sponsor = st.text_input("Sponsor / funding source")
                manager = st.text_input("Project manager / desk")
            with col2:
                budget = st.number_input("Budget (FCFA)", min_value=0.0, value=0.0, step=100000.0)
                amount_spent = st.number_input("Amount spent so far (FCFA)", min_value=0.0, value=0.0, step=100000.0)
                start_date = st.date_input("Start date", value=date.today())
                end_date = st.date_input("Expected end date", value=date.today() + timedelta(days=180))
                status = st.selectbox("Project status", ["Planned", "Active", "Ongoing", "Completed", "On Hold", "Cancelled"])
                progress_percent = st.slider("Progress %", min_value=0, max_value=100, value=0)
            description = st.text_area("Description")
            submitted = st.form_submit_button("Save project", use_container_width=True)
            if submitted:
                if not title.strip():
                    st.error("Project title is required.")
                else:
                    try:
                        db.create_project(
                            title=title.strip(),
                            category=category.strip(),
                            location=location.strip(),
                            branch_id=branch_id,
                            budget=budget,
                            amount_spent=amount_spent,
                            start_date=start_date.isoformat(),
                            end_date=end_date.isoformat(),
                            status=status,
                            sponsor=sponsor.strip(),
                            manager=manager.strip(),
                            progress_percent=progress_percent,
                            description=description.strip(),
                        )
                        st.success("Project saved successfully.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not save project: {exc}")

    with tab2:
        if not db.get_project_options():
            st.info("Please add a project before recording progress updates.")
        else:
            with st.form("project_update_form"):
                project_id = get_project_choice("Project", key="project_update_project")
                col1, col2 = st.columns(2)
                with col1:
                    update_date = st.date_input("Update date", value=date.today())
                    progress_percent = st.slider("Updated progress %", min_value=0, max_value=100, value=0, key="update_slider")
                with col2:
                    summary = st.text_area("Progress summary")
                submitted = st.form_submit_button("Save update", use_container_width=True)
                if submitted:
                    if not summary.strip():
                        st.error("Progress summary is required.")
                    else:
                        try:
                            db.add_project_update(
                                project_id=project_id,
                                update_date=update_date.isoformat(),
                                progress_percent=progress_percent,
                                summary=summary.strip(),
                            )
                            st.success("Project update saved successfully.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Could not save project update: {exc}")

    with tab3:
        updates_df = db.get_project_updates_df()
        st.subheader("Project register")
        table_or_info(projects_df, "No projects have been recorded yet.")
        render_download_buttons(projects_df, "wucuda_projects", "Projects")
        st.subheader("Project updates")
        table_or_info(updates_df, "No project updates have been recorded yet.")
        render_download_buttons(updates_df, "wucuda_project_updates", "ProjectUpdates")



def reports_page(report_year: int) -> None:
    st.title("Reports")
    st.write("Generate reports for national leadership, branch leadership, finance, elections, AGM, and projects.")

    report_type = st.selectbox(
        "Select report",
        [
            "National Summary",
            "Branch Summary",
            "Member Compliance",
            "Branch Compliance",
            "Finance Transactions",
            "Projects",
            "Elections",
            "Candidate Results",
            "Executive Expiry",
            "AGM",
        ],
    )

    if report_type == "National Summary":
        summary_text = db.get_national_summary_text(report_year)
        st.text_area("Summary report", value=summary_text, height=360)
        st.download_button(
            "Download summary as text",
            data=summary_text.encode("utf-8"),
            file_name=f"wucuda_national_summary_{report_year}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    elif report_type == "Branch Summary":
        df = db.get_branch_summary_report(report_year)
        table_or_info(df)
        render_download_buttons(df, f"branch_summary_{report_year}", "BranchSummary")

    elif report_type == "Member Compliance":
        branch_id = get_branch_choice("Optional branch filter", include_national=True, key="report_member_branch")
        df = db.get_member_compliance_report(report_year, branch_id=branch_id)
        paid_count = int((df["payment_status"] == "Paid").sum()) if not df.empty else 0
        outstanding_count = int((df["payment_status"] == "Outstanding").sum()) if not df.empty else 0
        col1, col2 = st.columns(2)
        col1.metric("Paid members", paid_count)
        col2.metric("Outstanding members", outstanding_count)
        table_or_info(df)
        render_download_buttons(df, f"member_compliance_{report_year}", "MemberCompliance")

    elif report_type == "Branch Compliance":
        df = db.get_branch_compliance_report(report_year)
        paid_count = int((df["payment_status"] == "Paid").sum()) if not df.empty else 0
        outstanding_count = int((df["payment_status"] == "Outstanding").sum()) if not df.empty else 0
        col1, col2 = st.columns(2)
        col1.metric("Branches compliant", paid_count)
        col2.metric("Branches outstanding", outstanding_count)
        table_or_info(df)
        render_download_buttons(df, f"branch_compliance_{report_year}", "BranchCompliance")

    elif report_type == "Finance Transactions":
        df = db.get_finance_transactions_report(report_year)
        total_amount = float(df["amount"].sum()) if not df.empty else 0
        st.metric("Total finance transactions", fcfa(total_amount))
        table_or_info(df)
        render_download_buttons(df, f"finance_transactions_report_{report_year}", "FinanceTransactions")

    elif report_type == "Projects":
        status_filter = st.selectbox(
            "Project status filter",
            ["All", "Planned", "Active", "Ongoing", "Completed", "On Hold", "Cancelled"],
        )
        df = db.get_projects_report(status_filter)
        table_or_info(df)
        render_download_buttons(df, f"projects_report_{status_filter.lower()}_{report_year}", "ProjectsReport")

    elif report_type == "Elections":
        df = db.get_election_report()
        table_or_info(df)
        render_download_buttons(df, f"elections_report_{report_year}", "ElectionsReport")

    elif report_type == "Candidate Results":
        df = db.get_candidate_results_report()
        table_or_info(df)
        render_download_buttons(df, f"candidate_results_{report_year}", "CandidateResults")

    elif report_type == "Executive Expiry":
        days_ahead = st.slider("Show terms expiring within this many days", min_value=30, max_value=730, value=180, step=30)
        df = db.get_executive_expiry_report(days_ahead=days_ahead)
        table_or_info(df, "No executive term falls inside the selected time window.")
        render_download_buttons(df, f"executive_expiry_{days_ahead}_days", "ExecutiveExpiry")

    elif report_type == "AGM":
        df = db.get_agm_report()
        table_or_info(df)
        render_download_buttons(df, f"agm_report_{report_year}", "AGMReport")



def settings_page(settings: dict[str, str]) -> None:
    st.title("Association Settings")
    st.write("Adjust core configuration values used throughout the system.")

    with st.form("settings_form"):
        col1, col2 = st.columns(2)
        with col1:
            association_name = st.text_input("Association name", value=settings.get("association_name", "WUCUDA"))
            patron = st.text_input("Patron", value=settings.get("patron", "The King of Babessi"))
            member_annual_due = st.number_input(
                "Annual member due (FCFA)",
                min_value=0.0,
                value=float(settings.get("member_annual_due", "2000")),
                step=500.0,
            )
            branch_annual_regulation = st.number_input(
                "Annual branch regulation (FCFA)",
                min_value=0.0,
                value=float(settings.get("branch_annual_regulation", "15000")),
                step=1000.0,
            )
        with col2:
            executive_term_years = st.number_input(
                "Executive term (years)",
                min_value=1,
                value=int(settings.get("executive_term_years", "3")),
                step=1,
            )
            major_event_expected_attendance = st.number_input(
                "Expected attendance for major events",
                min_value=0,
                value=int(settings.get("major_event_expected_attendance", "1500")),
                step=50,
            )
            estimated_total_members = st.number_input(
                "Estimated total association membership",
                min_value=0,
                value=int(settings.get("estimated_total_members", "30000")),
                step=100,
            )
        submitted = st.form_submit_button("Save settings", use_container_width=True)
        if submitted:
            try:
                db.save_settings(
                    {
                        "association_name": association_name.strip(),
                        "patron": patron.strip(),
                        "member_annual_due": member_annual_due,
                        "branch_annual_regulation": branch_annual_regulation,
                        "executive_term_years": executive_term_years,
                        "major_event_expected_attendance": major_event_expected_attendance,
                        "estimated_total_members": estimated_total_members,
                    }
                )
                st.success("Settings saved successfully.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save settings: {exc}")

    db_file = Path(__file__).with_name("wucuda.db")
    st.caption(f"Database file: {db_file}")
    st.markdown(
        "<div class='small-note'>Tip: This application ships with small demo data so the screens are not empty on first launch. Replace or extend the records with your real WUCUDA data.</div>",
        unsafe_allow_html=True,
    )


settings = db.get_settings_dict()
default_member_due = float(settings.get("member_annual_due", "2000"))
default_branch_regulation = float(settings.get("branch_annual_regulation", "15000"))
term_years = int(settings.get("executive_term_years", "3"))
default_attendance = int(settings.get("major_event_expected_attendance", "1500"))

st.sidebar.title(settings.get("association_name", "WUCUDA"))
st.sidebar.caption(f"Patron: {settings.get('patron', 'The King of Babessi')}")
report_year = st.sidebar.selectbox(
    "Reporting year",
    options=[date.today().year - 2, date.today().year - 1, date.today().year, date.today().year + 1],
    index=2,
)
page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Branches",
        "Members",
        "Finance",
        "Elections",
        "Executives",
        "Annual General Assembly",
        "Projects",
        "Reports",
        "Settings",
    ],
)

if page == "Dashboard":
    dashboard_page(report_year, settings)
elif page == "Branches":
    branches_page(default_branch_regulation)
elif page == "Members":
    members_page(default_member_due)
elif page == "Finance":
    finance_page(report_year, default_member_due, default_branch_regulation)
elif page == "Elections":
    elections_page(term_years, default_attendance)
elif page == "Executives":
    executives_page(term_years)
elif page == "Annual General Assembly":
    agm_page(default_attendance)
elif page == "Projects":
    projects_page()
elif page == "Reports":
    reports_page(report_year)
elif page == "Settings":
    settings_page(settings)
