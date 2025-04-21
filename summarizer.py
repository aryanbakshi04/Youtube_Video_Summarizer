# app.py

import os
import tempfile
import streamlit as st
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)
from rpunct import RestorePuncts
from agno.agent import Agent
from agno.models.google import Gemini

# 1) Must be the very first Streamlit command
st.set_page_config(
    page_title="YouTube Video Summarizer",
    page_icon="🎥",
    layout="wide",
)

st.title("YouTube Video Summarizer")
st.markdown(
    """
    Paste the YouTube link below, enter your Gemini API key,  
    and optionally supply a proxy URL or cookies file to fetch transcripts.
    """
)

with st.sidebar:
    st.header("Configuration")
    url       = st.text_input("YouTube URL")
    api_key   = st.text_input("Gemini API Key", type="password")
    model_id  = st.selectbox(
        "Gemini Model", ["gemini-2.0-flash-exp", "gemini-2.0-flash"]
    )
    proxy_url = st.text_input(
        "HTTP(S) Proxy URL (e.g. http://user:pass@host:port)", ""
    )
    cookie_file = st.file_uploader(
        "Upload YouTube cookies.txt (Netscape format)", type="txt"
    )
    summarize = st.button("Summarize Video")

if summarize:
    # --- validate inputs
    if not url:
        st.sidebar.error("▶️ Please enter a YouTube URL.")
        st.stop()
    if not api_key:
        st.sidebar.error("🔑 Please enter your Gemini API key.")
        st.stop()

    # set Gemini key
    os.environ["GOOGLE_API_KEY"] = api_key

    # extract video ID
    video_id = url.split("watch?v=")[-1].split("&")[0]

    # build proxies dict if provided
    proxies = None
    if proxy_url.strip():
        proxies = {
            "http": proxy_url.strip(),
            "https": proxy_url.strip()
        }

    # save uploaded cookies to a temp file
    cookie_path = None
    if cookie_file is not None:
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        tf.write(cookie_file.read())
        tf.flush()
        cookie_path = tf.name

    # ----- STEP 1: fetch transcript -----
    try:
        with st.spinner("⏳ Fetching transcript…"):
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id,
                proxies=proxies,
                cookies=cookie_path
            )
        raw_text = " ".join(seg["text"] for seg in transcript_list)
    except (TranscriptsDisabled, NoTranscriptFound):
        st.error(
            "❌ Could not fetch transcript automatically.\n"
            "– Captions disabled or unavailable for this video.\n"
            "– You may need a valid cookies.txt authentication.\n"
            "– Or try supplying a working proxy."
        )
        st.stop()
    except Exception as e:
        st.error(f"❌ Unexpected error fetching transcript:\n{e}")
        st.stop()

    # ----- STEP 2: restore punctuation -----
    with st.spinner("✍️ Restoring punctuation…"):
        punctuator  = RestorePuncts()
        punctuated  = punctuator.punctuate(raw_text)

    # ----- STEP 3: summarize with Gemini -----
    with st.spinner("🤖 Summarizing transcript…"):
        summarizer = Agent(
            model=Gemini(id=model_id),
            description="Summarize a punctuated YouTube transcript",
            instructions=["Provide a clear, concise summary of the text."],
            markdown=True,
        )
        prompt   = f"Summarize the following text:\n\n{punctuated}"
        response = summarizer.run(prompt)
        summary  = response.content

    # ----- Display results -----
    st.subheader("🔖 Summary")
    st.markdown(summary)

    with st.expander("📜 Show full punctuated transcript"):
        st.write(punctuated)
