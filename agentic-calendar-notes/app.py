"""
Streamlit front end for the notes/reminders agent.

Run:
    streamlit run app.py
"""

import uuid

import streamlit as st
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from agent import graph, SYSTEM_PROMPT
import storage

st.set_page_config(page_title="Personal Assistant", page_icon="🗒️")

# --- one thread_id per browser session -> one persistent conversation ------
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "history" not in st.session_state:
    st.session_state.history = []  # for rendering only; graph keeps the real state

config = {"configurable": {"thread_id": st.session_state.thread_id}}

# --- sidebar: live view of what's actually stored --------------------------
with st.sidebar:
    st.header("📝 Notes")
    notes = storage.list_notes()
    if not notes:
        st.caption("No notes yet.")
    for n in notes:
        st.markdown(f"- **{n['text']}**  \n  `{n['id']}` · {n['created_at']}")

    st.header("⏰ Reminders")
    reminders = storage.list_reminders()
    if not reminders:
        st.caption("No reminders yet.")
    for r in reminders:
        st.markdown(f"- **{r['text']}** — {r['when']}  \n  `{r['id']}`")

    st.divider()
    if st.button("Clear chat (new session)"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.history = []
        st.rerun()

# --- main chat area ----------------------------------------------------------
st.title("🗒️ Personal Assistant")
st.caption("Ask me to save notes, list them, set reminders, or delete either.")

for role, content in st.session_state.history:
    with st.chat_message(role):
        st.markdown(content)

user_input = st.chat_input("e.g. 'remind me to call the bank tomorrow at 10am'")

if user_input:
    st.session_state.history.append(("user", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    # first turn of this thread: prime it with the system prompt
    messages = []
    if len(st.session_state.history) == 1:
        messages.append(SystemMessage(content=SYSTEM_PROMPT))
    messages.append(HumanMessage(content=user_input))

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = graph.invoke({"messages": messages}, config)
            reply = result["messages"][-1].content
        st.markdown(reply)

    st.session_state.history.append(("assistant", reply))
    st.rerun()  # refresh sidebar so new notes/reminders show immediately
