# app.py

import os
import streamlit as st

# 1) Always call this first!
st.set_page_config(
    page_title="YouTube Video Summarizer",
    page_icon="🎥",
    layout="wide",
)

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)
from rpunct import RestorePuncts
from agno.agent import Agent
from agno.models.google import Gemini

st.title("YouTube Video Summarizer")
st.markdown(
    """
    Paste the YouTube link below, enter your Gemini API key,  
    and get its brief summary.
    """
)

# Sidebar inputs
with st.sidebar:
    st.header("Configuration")
    url = st.text_input("YouTube URL")
    api_key = st.text_input("Gemini API Key", type="password")
    model_id = st.selectbox(
        "Gemini Model",
        ["gemini-2.0-flash-exp", "gemini-2.0-flash"],
    )
    use_proxy = st.checkbox("Use proxy (if configured)") 
    summarize = st.button("Summarize Video")

if summarize:
    # validations
    if not url:
        st.sidebar.error("Please enter a YouTube URL.")
        st.stop()
    if not api_key:
        st.sidebar.error("Please enter your Gemini API key.")
        st.stop()

    os.environ["GOOGLE_API_KEY"] = api_key

    # extract video ID
    video_id = url.split("watch?v=")[-1].split("&")[0]

    # prepare optional proxies from Streamlit secrets
    proxies = {}
    if use_proxy:
        http = st.secrets.get("HTTP_PROXY")
        https = st.secrets.get("HTTPS_PROXY")
        if http:   proxies["http"] = http
        if https:  proxies["https"] = https

    # STEP 1: fetch (or fallback to manual paste)
    try:
        with st.spinner("Fetching transcript…"):
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id, 
                proxies=proxies if proxies else None
            )
        raw_text = " ".join(seg["text"] for seg in transcript_list)
    except (TranscriptsDisabled, NoTranscriptFound, Exception) as e:
        st.warning(
            "⚠️ Auto‑fetch failed. YouTube may be blocking transcript requests.\n"
            "Please paste your transcript below:"
        )
        raw_text = st.text_area("Transcript (paste here)", height=200)
        if not raw_text.strip():
            st.error("Transcript is required to proceed.")
            st.stop()

    # STEP 2: restore punctuation
    with st.spinner("Restoring punctuation…"):
        punctuator = RestorePuncts()
        punctuated = punctuator.punctuate(raw_text)

    # STEP 3: run Gemini summarization
    with st.spinner("Summarizing transcript…"):
        summarizer = Agent(
            model=Gemini(id=model_id),
            description="Summarize a punctuated YouTube transcript",
            instructions=["Provide a clear, concise summary of the text."],
            markdown=True,
        )
        prompt = f"Summarize the following text:\n\n{punctuated}"
        response = summarizer.run(prompt)
        summary = response.content

    # display results
    st.subheader("Summary")
    st.markdown(summary)

    with st.expander("Show full punctuated transcript"):
        st.write(punctuated)
