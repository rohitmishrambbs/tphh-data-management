"""
TPHH Data Management System - Access Security & Authentication
Provides passcode protection for online deployments.
"""
import streamlit as st
from src.config import DEFAULT_APP_PIN


def check_authentication() -> bool:
    """
    Checks if the user has entered the correct PIN / password.
    Returns True if authenticated, False otherwise.
    """
    if st.session_state.get("authenticated", False):
        return True

    # Retrieve expected PIN (from Streamlit Cloud Secrets if configured, otherwise default)
    try:
        expected_pin = st.secrets.get("APP_PIN", DEFAULT_APP_PIN)
    except Exception:
        expected_pin = DEFAULT_APP_PIN

    # Center-aligned authentication screen
    _, center_col, _ = st.columns([1, 1.8, 1])

    with center_col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 25px;">
                <h2 style="color: #1E3A8A; margin-bottom: 5px;">🏛️ TPHH Data Management System</h2>
                <p style="color: #64748B; font-size: 14px;">Authorized Access Only • Household Database Portal</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown("#### 🔒 Enter Access PIN")
            st.caption("Please enter your security PIN to view and manage beneficiary records.")

            pin_input = st.text_input(
                "Security PIN:",
                type="password",
                placeholder="Enter PIN...",
                key="login_pin_input",
            )

            submit_btn = st.button("🔓 Unlock Portal", type="primary", use_container_width=True)

            if submit_btn:
                if pin_input == expected_pin:
                    st.session_state["authenticated"] = True
                    st.success("Access Granted! Loading portal...")
                    st.rerun()
                else:
                    st.error("❌ Incorrect PIN. Please try again.")

    return False


def render_logout_button():
    """Renders a logout button in the sidebar."""
    if st.session_state.get("authenticated", False):
        if st.sidebar.button("🔒 Log Out", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()

