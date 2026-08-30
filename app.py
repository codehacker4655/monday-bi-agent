import streamlit as st
import requests
import json
import uuid

st.set_page_config(
    page_title="Monday BI Agent",
    page_icon="🤖",
    layout="wide"
)

st.title("📊 Founder BI Agent (Monday.com Integration)")
st.caption("Cross-board intelligence across Sales Pipeline and Work Order Execution")

BACKEND_URL = st.sidebar.text_input(
    "Backend Endpoint",
    value="http://localhost:8000/api/chat"
)

# --------------------------------------------------
# Conversation session
# --------------------------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []


# --------------------------------------------------
# Render chat history
# --------------------------------------------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --------------------------------------------------
# User prompt input
# --------------------------------------------------
if prompt := st.chat_input(
    "Ask a business question "
    "(e.g., 'How is our pipeline looking for renewables?')"
):

    # Display user message
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    with st.chat_message("assistant"):
        with st.spinner(
            "Fetching live board data & computing BI metrics..."
        ):
            try:
                # Send both the question and the conversation
                # session ID to the backend.
                res = requests.post(
                    BACKEND_URL,
                    json={
                        "query": prompt,
                        "session_id": st.session_state.session_id
                    },
                    timeout=60
                )

                if res.status_code == 200:

                    data = res.json()

                    answer = data.get(
                        "answer",
                        "No response generated."
                    )

                    st.markdown(answer)

                    # --------------------------------------------------
                    # Display data-quality warnings
                    # --------------------------------------------------
                    pipeline_caveats = (
                        data.get("pipeline_data", {})
                        .get("data_caveats", [])
                    )

                    financial_caveats = (
                        data.get("financial_data", {})
                        .get("data_caveats", [])
                    )

                    all_caveats = (
                        pipeline_caveats +
                        financial_caveats
                    )

                    if all_caveats:
                        with st.expander(
                            "⚠️ Data Quality Caveats & Missing Records"
                        ):
                            for caveat in all_caveats:
                                st.warning(caveat)

                    # Save assistant response to chat history
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer
                        }
                    )

                else:
                    st.error(
                        f"Error {res.status_code}: {res.text}"
                    )

            except requests.exceptions.Timeout:
                st.error(
                    "The backend took too long to respond. "
                    "Please try again."
                )

            except requests.exceptions.RequestException as e:
                st.error(
                    f"Failed to reach API: {str(e)}"
                )

            except Exception as e:
                st.error(
                    f"Unexpected error: {str(e)}"
                )