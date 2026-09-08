import os
import requests
import streamlit as st
import importlib

import uuid
st = importlib.import_module("streamlit")

from config.settings import settings

API_HEADERS = {
    "X-API-Token": settings.API_TOKEN
}
API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://localhost:8000/api/v1",
)
CHAT_URL = f"{API_BASE_URL}/agent/chat"
APPROVAL_URL = f"{API_BASE_URL}/admin/override"


st.set_page_config(layout="wide", page_title="Autonomous Agent Enterprise Portal")

st.title("🏦 Production Grade-A Conversational Agent")
st.caption("Structured Pydantic Extraction Layer + LangGraph State Management")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "current_logs" not in st.session_state:
    st.session_state.current_logs = []
if "status" not in st.session_state:
    st.session_state.status = "Awaiting natural language message..."
if "backend_state" not in st.session_state:
    st.session_state.backend_state = "idle"

col1, col2 = st.columns([1.2, 1.0], gap="large")

with col1:
    st.subheader("💬 Live Customer Chat Portal")
    st.info("Type complex sentences. The AI will pull variables cleanly out of your text.")
    
    user_chat_text = st.text_area(
        "Chat Message", 
        placeholder="Type here: e.g., 'Hey, cancel my order ORD-222. My account email is vip@example.com'"
    )
    submit_btn = st.button("Send Message to Agent")
        
    if submit_btn and user_chat_text.strip():
        with st.spinner("Sending request to the FastAPI agent service..."):
            try:
                response = requests.post(
                    CHAT_URL,
                    headers=API_HEADERS,
                    json={
                        "thread_id": st.session_state.thread_id,
                        "user_message": user_chat_text,
                    },
                    timeout=120,
                )
                response.raise_for_status()
                data = response.json()
                st.session_state.current_logs = data.get("logs", [])
                st.session_state.status = data.get("current_status_msg", "")
                st.session_state.backend_state = data.get("status", "completed")
            except requests.RequestException as error:
                st.error(f"Could not reach the FastAPI service: {error}")

with col2:
    st.subheader("🕵️‍♂️ Core Logic Engine Trace Logs")
    st.metric(label="Current System Status Indicator", value=st.session_state.status)

    st.write("**Live Engine Thought Telemetry:**")
    for log_item in st.session_state.current_logs:
        st.code(f"💡 {log_item}", language="text")

    if st.session_state.backend_state == "held_for_review":
        st.error("⚠️ CRITICAL EVENT: Transaction held for manager approval.")
        with st.expander("🔐 Open Administrative Action Overrides Portal", expanded=True):
            if st.button("AUTHORIZE TRANSACTION AND DEPLOY PAYOUT", type="primary"):
                with st.spinner("Sending authorization to the FastAPI service..."):
                    try:
                        response = requests.post(
                            APPROVAL_URL,
                            headers=API_HEADERS,
                            json={
                                "thread_id": st.session_state.thread_id,
                                "action": "APPROVE",
                            },
                            timeout=120,
                        )
                        response.raise_for_status()
                        data = response.json()
                        st.session_state.current_logs = data.get("logs", [])
                        st.session_state.status = data.get("current_status_msg", "")
                        st.session_state.backend_state = data.get("status", "completed")
                        st.rerun()
                    except requests.RequestException as error:
                        st.error(f"Authorization request failed: {error}")
             