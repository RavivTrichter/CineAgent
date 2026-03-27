"""CineAssist — Streamlit chat interface."""

import os

import httpx
import streamlit as st

BACKEND_URL = os.environ.get("ASSISTANT_API_URL", "http://localhost:8001")

st.set_page_config(page_title="CineAssist", page_icon="🎬", layout="wide")

# --- Session state init ---
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []


def api_call(method: str, path: str, **kwargs) -> dict | list | None:
    """Make an API call to the backend."""
    try:
        resp = getattr(httpx, method)(f"{BACKEND_URL}{path}", timeout=60.0, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        st.error(f"API error: {e.response.status_code} — {e.response.text}")
        return None
    except httpx.RequestError as e:
        st.error(f"Cannot connect to backend: {e}")
        return None


# --- Sidebar ---
with st.sidebar:
    st.title("🎬 CineAssist")
    st.caption("Your intelligent film assistant")

    if st.button("➕ New Conversation", use_container_width=True):
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.subheader("Past Conversations")

    conversations = api_call("get", "/conversations") or []
    for conv in conversations:
        label = conv.get("title") or "Untitled"
        if st.button(label, key=conv["id"], use_container_width=True):
            st.session_state.conversation_id = conv["id"]
            detail = api_call("get", f"/conversations/{conv['id']}")
            if detail:
                st.session_state.messages = detail["messages"]
            st.rerun()


# --- Main chat area ---
st.header("🎬 CineAssist")

# Render chat messages
for msg in st.session_state.messages:
    role = msg["role"] if isinstance(msg["role"], str) else msg["role"]
    with st.chat_message(role):
        st.markdown(msg["content"])

        # Confidence badge (assistant messages only)
        if role == "assistant":
            confidence = msg.get("confidence")
            if confidence == "verified":
                st.caption("✅ Verified by API data")
            elif confidence == "general":
                st.caption("💡 Based on general knowledge")
            elif confidence == "mixed":
                st.caption("ℹ️ Partially verified by API data")

            # Booking success indicator
            tool_calls = msg.get("tool_calls") or []
            if any(
                (tc.get("name") if isinstance(tc, dict) else tc) == "book_tickets"
                for tc in tool_calls
            ):
                st.success("🎬 Booking confirmed!")

            # Debug expander
            thinking = msg.get("thinking")
            if thinking or tool_calls:
                with st.expander("🔍 Debug: Chain of Thought & Tool Calls"):
                    if thinking:
                        st.text_area(
                            "Thinking",
                            thinking,
                            height=150,
                            disabled=True,
                            key=f"thinking_{msg.get('id', id(msg))}",
                        )
                    if tool_calls:
                        st.json(tool_calls)

# Chat input
if prompt := st.chat_input("Ask about movies, showtimes, or book tickets..."):
    # Ensure we have a conversation
    if not st.session_state.conversation_id:
        result = api_call("post", "/conversations")
        if result:
            st.session_state.conversation_id = result["id"]
        else:
            st.stop()

    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            data = api_call(
                "post",
                f"/conversations/{st.session_state.conversation_id}/messages",
                json={"message": prompt},
            )

        if data:
            st.markdown(data["text"])

            # Confidence badge
            confidence = data.get("confidence")
            if confidence == "verified":
                st.caption("✅ Verified by API data")
            elif confidence == "general":
                st.caption("💡 Based on general knowledge")
            elif confidence == "mixed":
                st.caption("ℹ️ Partially verified by API data")

            # Debug expander
            thinking = data.get("thinking")
            tool_calls = data.get("tool_calls_made", [])
            if thinking or tool_calls:
                with st.expander("🔍 Debug: Chain of Thought & Tool Calls"):
                    if thinking:
                        st.text_area("Thinking", thinking, height=150, disabled=True)
                    if tool_calls:
                        st.json(tool_calls)

            # Save to session
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": data["text"],
                    "confidence": data.get("confidence"),
                    "thinking": data.get("thinking"),
                    "tool_calls": data.get("tool_calls_made", []),
                }
            )
