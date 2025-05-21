import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("OpenAI API key not found. Please add it to .env")
    st.stop()

# Initialize OpenAI client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

EXTRA_HEADERS = {
    "HTTP-Referer": "http://localhost",
    "X-Title": "My Streamlit File Q&A"
}

MODEL_NAME = "nvidia/llama-3.1-nemotron-ultra-253b-v1:free"

st.set_page_config(page_title="📄 Deus AI")
st.title("📄 Deus AI")

# === Initialize Session State ===
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "system", "content": "You are a helpful assistant that answers questions based on uploaded file content."}
    ]
if "file_summarized" not in st.session_state:
    st.session_state.file_summarized = False

# === Reset Function ===
def reset_state():
    st.session_state.uploaded_file = None
    st.session_state.chat_history = [
        {"role": "system", "content": "You are a helpful assistant that answers questions based on uploaded file content."}
    ]
    st.session_state.file_summarized = False

# === Upload Section ===
if st.session_state.uploaded_file is None:
    uploaded = st.file_uploader(
        label="Drag and drop file here\nLimit 200MB per file • TXT, CSV, XLSX, PDF",
        type=["txt", "csv", "xlsx", "pdf"],
        label_visibility="visible"
    )
    if uploaded:
        st.session_state.uploaded_file = uploaded
        st.rerun()
else:
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        st.success(f"📎 File uploaded: `{st.session_state.uploaded_file.name}`")
    with col2:
        if st.button("❌", help="Remove file", use_container_width=True):
            reset_state()
            st.rerun()

# === Continue if File is Uploaded ===
if st.session_state.uploaded_file:
    uploaded_file = st.session_state.uploaded_file
    filename = uploaded_file.name.lower()
    file_content = ""

    if filename.endswith(".txt"):
        file_content = uploaded_file.read().decode("utf-8")

    elif filename.endswith(".pdf"):
        try:
            with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
                file_content = "".join([page.get_text() for page in doc])
        except Exception as e:
            st.error(f"Error reading PDF: {e}")

    elif filename.endswith(".csv") or filename.endswith(".xlsx"):
        try:
            if filename.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file, engine="openpyxl")
            file_content = df.head(20).to_csv(index=False)
        except Exception as e:
            st.error(f"Error reading spreadsheet: {e}")

    # === File Summary Only Once ===
    if file_content and not st.session_state.file_summarized:
        with st.spinner("Summarizing file..."):
            try:
                summary_prompt = f"Summarize the following content:\n\n{file_content}"
                st.session_state.chat_history.append({"role": "user", "content": summary_prompt})

                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    extra_headers=EXTRA_HEADERS,
                    messages=st.session_state.chat_history
                )

                summary = (
                    completion.choices[0].message.content
                    if completion and completion.choices and completion.choices[0].message and completion.choices[0].message.content
                    else "Sorry, I couldn't generate a summary."
                )

                summary_message = f"**Based on the document you uploaded, here's a summary:**\n\n{summary}"
                st.session_state.chat_history.append({"role": "assistant", "content": summary_message})
                st.session_state.file_summarized = True

            except Exception as e:
                st.error(f"API request failed: {e}")

    # === Display Chat History ===
    for msg in st.session_state.chat_history[1:]:  # skip system prompt
        if msg["role"] == "user" and "Summarize the following content" in msg["content"]:
            continue
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # === Q&A Input ===
    user_input = st.chat_input("Ask something about the file...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    completion = client.chat.completions.create(
                        model=MODEL_NAME,
                        extra_headers=EXTRA_HEADERS,
                        messages=st.session_state.chat_history
                    )
                    reply = (
                        completion.choices[0].message.content
                        if completion and completion.choices and completion.choices[0].message and completion.choices[0].message.content
                        else "Sorry, I couldn't generate a response."
                    )
                except Exception as e:
                    reply = f"API error: {e}"

                st.markdown(reply)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
