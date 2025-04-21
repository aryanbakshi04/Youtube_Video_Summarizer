# app.py

import os
import streamlit as st

st.set_page_config(
    page_title="YouTube Video Summarizer",
    page_icon="🎥",
    layout="wide",
)

from youtube_transcript_api import YouTubeTranscriptApi
from rpunct import RestorePuncts
from agno.agent import Agent
from agno.models.google import Gemini

st.title("YouTube Video Summarizer")
st.markdown(
    """
    Paste the YouTube link below, enter your Gemini API key,  
    and get its brief summary
    """
)


with st.sidebar:
    st.header("Configuration")
    url = st.text_input("YouTube URL", "")
    api_key = st.text_input("Gemini API Key", type="password")s
    model_id = st.selectbox(
        "Gemini Model",
        ["gemini-2.0-flash-exp", "gemini-2.0-flash"]
    )
    summarize = st.button("Summarize Video")

if summarize:
    if not url:
        st.sidebar.error("Please enter a YouTube URL.")
    elif not api_key:
        st.sidebar.error(" Please enter your Gemini API key.")
    else:
        
        os.environ["GOOGLE_API_KEY"] = api_key

        try:
            
            video_id = url.split("watch?v=")[-1].split("&")[0]

            
            with st.spinner("Fetching transcript..."):
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                raw_text = " ".join([t["text"] for t in transcript_list])

            
            with st.spinner("Restoring punctuation..."):
                punctuator = RestorePuncts()
                punctuated = punctuator.punctuate(raw_text)

            
            with st.spinner("Summarizing transcript..."):
                summarizer = Agent(
                    model=Gemini(id=model_id),
                    description="Summarize a punctuated YouTube transcript",
                    instructions=["Provide a clear, concise summary of the text."],
                    markdown=True,
                )
                prompt = f"Summarize the following text:\n\n{punctuated}"
                response = summarizer.run(prompt)
                summary = response.content

            
            st.subheader("Summary")
            st.markdown(summary)

            with st.expander(" Show full punctuated transcript"):
                st.write(punctuated)

        except Exception as e:
            st.error(f"An error occurred: {e}")
