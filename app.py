import os
import requests
import streamlit as st
from dotenv import load_dotenv
from agno.agent import Agent
from agno.run.agent import RunOutput
from agno.models.openai import OpenAIChat
from agno.tools.firecrawl import FirecrawlTools

# 1. Load environment variables from .env
load_dotenv()

# 2. Retrieve keys from environment
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
MURF_API_KEY = os.getenv("MURF_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

# 3. Streamlit UI Setup
st.set_page_config(page_title="60s Blog Podcast", page_icon="🎙️")
st.title("🎙️ 60-Second Podcast Generator")

# 4. Key Status Sidebar & Voice Settings
with st.sidebar:
    st.header("🔑 API Status")
    st.write(f"GitHub: {'✅' if GITHUB_TOKEN else '❌'}")
    st.write(f"Murf AI: {'✅' if MURF_API_KEY else '❌'}")
    st.write(f"Firecrawl: {'✅' if FIRECRAWL_API_KEY else '❌'}")
    
    st.divider()
    st.header("⚙️ Voice Settings")
    # Marcus is a reliable high-energy voice for these scripts
    voice_choice = st.selectbox("Select Murf Voice", ["en-US-marcus", "en-US-natalie", "en-US-clinton"])

# 5. Critical Key Check
if not all([GITHUB_TOKEN, MURF_API_KEY, FIRECRAWL_API_KEY]):
    st.error("Missing API Keys! Please ensure GITHUB_TOKEN, MURF_API_KEY, and FIRECRAWL_API_KEY are in your .env file.")
    st.stop()

# 6. User Input
url = st.text_input("🔗 Paste Blog URL:", placeholder="https://example.com/blog-article")

# 7. Execution Logic
if st.button("🎙️ Generate 1-Min Podcast"):
    if not url.strip():
        st.warning("Please enter a blog URL.")
    else:
        # Step 1: Scraping and Summarization
        with st.spinner("Step 1: Scraping & Summarizing with GitHub Models..."):
            try:
                # Set Firecrawl key for the tool
                os.environ["FIRECRAWL_API_KEY"] = FIRECRAWL_API_KEY
                
                # Initialize Agent using GitHub Models endpoint
                agent = Agent(
                    name="Minute-Podcast-Host",
                    model=OpenAIChat(
                        id="gpt-4o", 
                        api_key=GITHUB_TOKEN, 
                        base_url="https://models.inference.ai.azure.com"
                    ),
                    tools=[FirecrawlTools()],
                    instructions=[
                        "Scrape the blog and identify the core message.",
                        "Write a solo-host podcast script that is STRICTLY between 130 and 145 words.",
                        "This word count ensures the final audio stays under 60 seconds.",
                        "Use a 'TL;DR' high-energy style. No markdown symbols like asterisks or hashtags.",
                        "Start with: 'Welcome to the 60-second breakdown.'",
                        "End with: 'That is the minute. See you next time!'"
                    ],
                )
                
                # Generate Script
                response: RunOutput = agent.run(f"Summarize this blog for a 60-second podcast: {url}")
                summary = response.content if hasattr(response, 'content') else str(response)
                
                if summary:
                    word_count = len(summary.split())
                    st.info(f"Script Generated (~{word_count} words).")
                    
                    # Step 2: Murf AI Audio Generation
                    with st.spinner("Step 2: Generating Voice with Murf AI..."):
                        murf_url = "https://api.murf.ai/v1/speech/generate"
                        headers = {
                            "Content-Type": "application/json",
                            "api-key": MURF_API_KEY
                        }
                        payload = {
                            "voiceId": voice_choice, 
                            "text": summary,
                            "format": "MP3",
                            "sampleRate": 48000
                        }

                        murf_res = requests.post(murf_url, json=payload, headers=headers)
                        
                        if murf_res.status_code == 200:
                            res_data = murf_res.json()
                            
                            # Fixed: Added 'audioFile' key based on Murf's actual API response
                            audio_url = (
                                res_data.get("audioFile") or 
                                res_data.get("audioUrl") or 
                                res_data.get("encodedAudio")
                            )
                            
                            if audio_url:
                                audio_data = requests.get(audio_url).content
                                
                                # Step 3: Final Display
                                st.success("Podcast Ready! 🎧")
                                st.audio(audio_data, format="audio/mp3")
                                
                                st.download_button(
                                    label="📥 Download MP3",
                                    data=audio_data,
                                    file_name="60_second_podcast.mp3",
                                    mime="audio/mp3"
                                )
                                
                                with st.expander("📄 View Podcast Script"):
                                    st.write(summary)
                            else:
                                st.error("Audio link not found in Murf response.")
                                st.json(res_data) # Debug display
                        else:
                            st.error(f"Murf AI Error: {murf_res.status_code}")
                            st.write(murf_res.text)
                else:
                    st.error("Could not generate a summary from that URL.")
                    
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")