"""
Parent Mode - Family Dashboard & Reports
InstaSchool multi-page app
"""
import os
import sys

# NOTE: Module cleanup removed - causes KeyError crashes on Python 3.13/Streamlit Cloud
# The previous approach of clearing sys.modules broke nested imports

import json
import streamlit as st
from datetime import datetime
from pathlib import Path

# Import shared initialization
from src.shared_init import setup_page, init_session_state, load_config
from src.ui_components import ThemeManager, FamilyDashboard
from src.state_manager import StateManager
from services.user_service import UserService
from services.family_service import get_family_service

# Report / certificate services can fail to import under certain hot-reload
# conditions on Python 3.13, so guard their imports and degrade gracefully.
try:
    from services.report_service import get_report_service  # type: ignore
except Exception:
    get_report_service = None  # type: ignore[assignment]

try:
    from services.certificate_service import get_certificate_service  # type: ignore
except Exception:
    get_certificate_service = None  # type: ignore[assignment]

# Page config
setup_page(title="InstaSchool - Parent", icon="👨‍👩‍👧")

# Apply theme
if "theme" in st.session_state:
    ThemeManager.apply_theme(st.session_state.theme)

st.markdown("# 👨‍👩‍👧 Parent Dashboard")

# Parent mode tabs
parent_tab1, parent_tab2, parent_tab3, parent_tab4 = st.tabs([
    "👨‍👩‍👧‍👦 Family Overview",
    "📊 Reports & Certificates",
    "📚 Curricula",
    "⚙️ Settings"
])

# Tab 1: Family Overview
with parent_tab1:
    family_service = get_family_service()
    user_service = UserService()
    children = user_service.list_users()

    if not children:
        # Empty state with onboarding
        st.markdown("""
        <div style="text-align: center; padding: 60px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; color: white; margin: 20px 0;">
            <h1 style="font-size: 48px; margin-bottom: 10px;">👨‍👩‍👧‍👦</h1>
            <h2 style="margin-bottom: 10px;">Welcome to InstaSchool!</h2>
            <p style="opacity: 0.9; max-width: 400px; margin: 0 auto 20px;">
                Get started by adding your children's profiles. Each child gets their own
                personalized learning experience with progress tracking.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 🎯 Quick Start")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("**Step 1:** Add your children below")
        with col2:
            st.info("**Step 2:** Switch to Create mode to build curricula")
        with col3:
            st.info("**Step 3:** Children learn in Student mode")

        st.markdown("---")
        st.markdown("### ➕ Add Your First Child")
        new_child_data = FamilyDashboard.render_add_child_form(
            form_key="add_child_overview_form",
            show_header=False
        )
        if new_child_data:
            user_service.create_user(
                username=new_child_data["username"],
                pin=new_child_data.get("pin")
            )
            st.success(f"✅ Added {new_child_data['username']}!")
            st.rerun()
    else:
        # Show family dashboard
        family_data = family_service.get_family_summary()
        FamilyDashboard.render_dashboard(family_data)

# Tab 2: Reports & Certificates
with parent_tab2:
    if get_report_service is None or get_certificate_service is None:
        st.warning(
            "Report and certificate services are currently unavailable in this environment."
        )
        st.info(
            "You can still view curricula and use Student / Teacher modes while this feature is disabled."
        )
    else:
        report_service = get_report_service()
        cert_service = get_certificate_service()
        user_service_reports = UserService()
        children = user_service_reports.list_usernames()

        if not children:
            st.info("Add children in the Family Overview tab to generate reports.")
        else:
            report_col, cert_col = st.columns(2)

            with report_col:
                st.markdown("### 📊 Progress Reports")
                selected_child = st.selectbox(
                    "Select Child",
                    options=["All Children"] + children,
                    key="report_child_select",
                )

                if st.button("📥 Generate PDF Report", type="primary", key="gen_report"):
                    with st.spinner("Generating report..."):
                        if selected_child == "All Children":
                            pdf_bytes = report_service.generate_family_report()
                            filename = "family_report.pdf"
                        else:
                            pdf_bytes = report_service.generate_child_report(selected_child)
                            filename = f"{selected_child}_report.pdf"

                        st.download_button(
                            "⬇️ Download Report",
                            data=pdf_bytes,
                            file_name=filename,
                            mime="application/pdf",
                        )

            with cert_col:
                st.markdown("### 🏆 Certificates")
                cert_child = st.selectbox(
                    "Select Child",
                    options=children,
                    key="cert_child_select",
                )

                cert_type = st.selectbox(
                    "Certificate Type",
                    ["Progress Certificate", "Custom Certificate"],
                    key="cert_type",
                )

                if cert_type == "Custom Certificate":
                    cert_title = st.text_input("Title", "Certificate of Achievement")
                    cert_text = st.text_area(
                        "Main Text", "For outstanding effort in learning!"
                    )

                if st.button("🎖️ Generate Certificate", type="secondary", key="gen_cert"):
                    with st.spinner("Creating certificate..."):
                        if cert_type == "Progress Certificate":
                            user_data = user_service_reports.get_user(cert_child) or {}
                            pdf_bytes = cert_service.generate_progress_certificate(
                                student_name=cert_child,
                                period=datetime.now().strftime("%B %Y"),
                                sections_completed=user_data.get(
                                    "sections_completed", 0
                                ),
                                xp_earned=user_data.get("xp", 0),
                                streak_days=user_data.get("streak", 0),
                                quizzes_passed=user_data.get("quizzes_passed", 0),
                            )
                        else:
                            pdf_bytes = cert_service.generate_custom_certificate(
                                student_name=cert_child,
                                title=cert_title,
                                main_text=cert_text,
                            )

                        st.download_button(
                            "⬇️ Download Certificate",
                            data=pdf_bytes,
                            file_name=f"{cert_child}_certificate.pdf",
                            mime="application/pdf",
                        )

# Tab 3: Curricula Overview
with parent_tab3:
    st.markdown("### 📚 Available Curricula")
    st.caption("View curricula created in Create mode. Switch to Create mode to add new ones.")

    curricula_dir = Path("curricula")
    if curricula_dir.exists():
        json_files = list(curricula_dir.glob("*.json"))
        if json_files:
            for json_file in sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
                try:
                    with open(json_file) as f:
                        data = json.load(f)
                    # Check for metadata in 'meta' block first (new format), fallback to top-level
                    meta = data.get('meta', {})
                    title = meta.get('subject', data.get('title', json_file.stem))
                    subject = meta.get('subject', data.get('subject', 'Unknown'))
                    grade = meta.get('grade', data.get('grade', ''))
                    units = len(data.get('units', []))
                    display_title = f"{subject} - Grade {grade}" if grade else title

                    with st.expander(f"{display_title}"):
                        st.write(f"**Subject:** {subject}")
                        if grade:
                            st.write(f"**Grade:** {grade}")
                        st.write(f"**Units:** {units}")
                        if meta.get('style'):
                            st.write(f"**Style:** {meta.get('style')}")
                        st.write(f"**File:** {json_file.name}")
                        if st.button("👀 Open in Student Mode", key=f"open_student_{json_file.stem}"):
                            # Remember this curriculum for the student page and switch
                            StateManager.set_state("preferred_curriculum_file", json_file.name)
                            st.switch_page("pages/1_Student.py")
                except Exception:
                    pass
        else:
            st.info("No curricula created yet. Switch to Create mode to build your first curriculum!")
    else:
        st.info("No curricula created yet. Switch to Create mode to build your first curriculum!")

# Tab 4: Settings
with parent_tab4:
    st.markdown("### ⚙️ Family Settings")

    settings_col1, settings_col2 = st.columns(2)

    with settings_col1:
        st.markdown("#### 🎨 Appearance")
        ThemeManager.get_theme_toggle()

    with settings_col2:
        st.markdown("#### 👥 Manage Children")
        settings_user_service = UserService()
        new_child_settings = FamilyDashboard.render_add_child_form(
            form_key="add_child_settings_form",
            show_header=False
        )
        if new_child_settings:
            settings_user_service.create_user(
                username=new_child_settings["username"],
                pin=new_child_settings.get("pin")
            )
            st.success(f"✅ Added {new_child_settings['username']}!")
            st.rerun()
