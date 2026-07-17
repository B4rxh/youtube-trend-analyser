import streamlit as st
import os
import tempfile
import gc
import base64
import re
import time
import yaml

from tqdm import tqdm
from brightdata_scrapper import *
from dotenv import load_dotenv
load_dotenv()

from crewai import Agent, Crew, Process, Task, LLM
from crewai_tools import FileReadTool

docs_tool = FileReadTool()

bright_data_api_key = os.getenv("BRIGHT_DATA_API_KEY")

st.set_page_config(
    page_title="Signal / YouTube Trend Console",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ===========================
#   Design system — "Signal Console"
#   A dark, terminal-inflected dashboard theme built around the
#   idea of picking a trend "signal" out of channel "noise".
# ===========================
def inject_custom_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

        :root {
            --ink: #10141C;
            --panel: #171C26;
            --panel-raised: #1D2330;
            --line: #2A3140;
            --paper: #ECE9E2;
            --text: #E4E2DA;
            --muted: #8B93A6;
            --teal: #2DD4BF;
            --teal-dim: rgba(45, 212, 191, 0.14);
            --amber: #F2B705;
            --amber-dim: rgba(242, 183, 5, 0.14);
        }

        html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }

        .stApp {
            background:
                radial-gradient(circle at 15% 0%, rgba(45,212,191,0.06), transparent 40%),
                var(--ink);
            color: var(--text);
        }

        h1, h2, h3, h4, .signal-eyebrow, .stage-label {
            font-family: 'IBM Plex Mono', monospace;
            letter-spacing: 0.02em;
        }

        /* ---- Header ---- */
        .signal-header {
            border: 1px solid var(--line);
            background: linear-gradient(180deg, var(--panel-raised), var(--panel));
            border-radius: 10px;
            padding: 22px 28px;
            margin-bottom: 22px;
            position: relative;
            overflow: hidden;
        }
        .signal-header::after {
            content: "";
            position: absolute;
            left: 0; right: 0; bottom: 0;
            height: 2px;
            background: linear-gradient(90deg, var(--teal), transparent 60%);
            animation: scan 3.2s linear infinite;
        }
        @keyframes scan {
            0% { transform: translateX(-40%); opacity: 0.2; }
            50% { opacity: 1; }
            100% { transform: translateX(140%); opacity: 0.2; }
        }
        .signal-eyebrow {
            color: var(--teal);
            font-size: 12px;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 6px;
        }
        .signal-title {
            font-size: 26px;
            font-weight: 600;
            color: var(--text);
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        /* ---- Stage labels (real pipeline order: ingest -> synthesize) ---- */
        .stage-label {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            font-weight: 600;
            color: var(--ink);
            background: var(--teal);
            padding: 4px 10px;
            border-radius: 4px;
            margin-bottom: 12px;
        }
        .stage-label.amber { background: var(--amber); }

        /* ---- Cards / panels ---- */
        .signal-card, div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--panel) !important;
            border: 1px solid var(--line) !important;
            border-radius: 10px !important;
        }
        .signal-card { padding: 16px 18px; margin-bottom: 12px; }

        /* ---- Status / log line ---- */
        .signal-log {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 13px;
            border: 1px solid var(--line);
            background: #0C0F16;
            color: var(--teal);
            border-radius: 6px;
            padding: 10px 14px;
            margin-bottom: 10px;
        }
        .signal-log.warn { color: var(--amber); }
        .signal-log.error { color: #FF6B6B; }
        .signal-log.done { color: var(--text); }
        .signal-log .dot {
            display: inline-block; width: 7px; height: 7px; border-radius: 50%;
            background: currentColor; margin-right: 8px;
        }

        /* ---- Sidebar ---- */
        section[data-testid="stSidebar"] {
            background: var(--panel);
            border-right: 1px solid var(--line);
        }
        section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
            font-family: 'IBM Plex Mono', monospace;
            color: var(--text);
            font-size: 15px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        /* ---- Inputs ---- */
        .stTextInput input, .stDateInput input {
            background: var(--ink) !important;
            color: var(--text) !important;
            border: 1px solid var(--line) !important;
            border-radius: 6px !important;
        }

        /* ---- Buttons ---- */
        .stButton button {
            border-radius: 6px !important;
            border: 1px solid var(--line) !important;
            background: var(--panel-raised) !important;
            color: var(--text) !important;
            font-family: 'IBM Plex Mono', monospace;
        }
        .stButton button[kind="primary"] {
            background: var(--teal) !important;
            color: var(--ink) !important;
            border: none !important;
            font-weight: 600 !important;
        }
        .stDownloadButton button {
            background: var(--amber) !important;
            color: var(--ink) !important;
            border: none !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            font-family: 'IBM Plex Mono', monospace;
        }

        /* ---- Metrics ---- */
        div[data-testid="stMetric"] {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 12px 16px;
        }
        div[data-testid="stMetricLabel"] {
            font-family: 'IBM Plex Mono', monospace;
            color: var(--muted) !important;
            text-transform: uppercase;
            font-size: 11px !important;
        }
        div[data-testid="stMetricValue"] { color: var(--teal) !important; }

        /* ---- Tabs ---- */
        button[data-baseweb="tab"] {
            font-family: 'IBM Plex Mono', monospace;
            color: var(--muted);
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: var(--teal) !important;
        }
        div[data-baseweb="tab-highlight"] { background-color: var(--teal) !important; }

        /* ---- Divider / signal rule ---- */
        .signal-rule {
            height: 1px;
            background: linear-gradient(90deg, var(--teal), var(--line) 40%, transparent);
            border: none;
            margin: 18px 0;
        }

        /* ---- Chips ---- */
        .signal-chip {
            display: inline-block;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 11px;
            padding: 3px 9px;
            border-radius: 999px;
            border: 1px solid var(--line);
            color: var(--muted);
            margin-right: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_status_log(container, message, state="info"):
    """Render a themed terminal-style status line into a placeholder container."""
    css_state = {"info": "", "warn": "warn", "error": "error", "done": "done"}.get(state, "")
    container.markdown(
        f'<div class="signal-log {css_state}"><span class="dot"></span>{message}</div>',
        unsafe_allow_html=True,
    )


inject_custom_css()

@st.cache_resource
def load_llm():

    llm = LLM(
        model="ollama/llama3.2",
        base_url="http://localhost:11434",
    )

    # Previously tried (both blocked by card/billing issues):
    # llm = LLM(
    #     model="openai/gemini-2.0-flash",
    #     base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    #     api_key=os.getenv("GEMINI_API_KEY"),
    # )
    # llm = LLM(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
    return llm

# ===========================
#   Define Agents & Tasks
# ===========================
def create_agents_and_tasks():
    """Creates a Crew for analysis of the channel scrapped output"""

    with open("config.yaml", 'r', encoding="utf-8") as file:
        config = yaml.safe_load(file)
    
    analysis_agent = Agent(
        role=config["agents"][0]["role"],
        goal=config["agents"][0]["goal"],
        backstory=config["agents"][0]["backstory"],
        verbose=True,
        tools=[docs_tool],
        llm=load_llm()
    )

    response_synthesizer_agent = Agent(
        role=config["agents"][1]["role"],
        goal=config["agents"][1]["goal"],
        backstory=config["agents"][1]["backstory"],
        verbose=True,
        llm=load_llm()
    )

    analysis_task = Task(
        description=config["tasks"][0]["description"],
        expected_output=config["tasks"][0]["expected_output"],
        agent=analysis_agent
    )

    response_task = Task(
        description=config["tasks"][1]["description"],
        expected_output=config["tasks"][1]["expected_output"],
        agent=response_synthesizer_agent
    )

    crew = Crew(
        agents=[analysis_agent, response_synthesizer_agent],
        tasks=[analysis_task, response_task],
        process=Process.sequential,
        verbose=True
    )
    return crew

# ===========================
#   Streamlit Setup
# ===========================

st.markdown(
    """
    <div class="signal-header">
        <div class="signal-eyebrow">// channel signal intelligence</div>
        <div class="signal-title">
            📡 YouTube Trend Console
            <span style="color: var(--muted); font-weight: 400; font-size: 15px;">
                powered by
                <img src="data:image/png;base64,{}" width="100" style="vertical-align: -5px; margin: 0 4px;">
                &amp;
                <img src="data:image/png;base64,{}" width="100" style="vertical-align: -5px; margin: 0 4px;">
            </span>
        </div>
    </div>
    """.format(
        base64.b64encode(open("assets/crewai.png", "rb").read()).decode(),
        base64.b64encode(open("assets/brightdata.png", "rb").read()).decode(),
    ),
    unsafe_allow_html=True,
)


if "messages" not in st.session_state:
    st.session_state.messages = []  # Chat history

if "response" not in st.session_state:
    st.session_state.response = None

if "crew" not in st.session_state:
    st.session_state.crew = None      # Store the Crew object

def reset_chat():
    st.session_state.messages = []
    gc.collect()

def start_analysis():
    # Create a status container
    
    
    with st.spinner('Scraping videos... This may take a moment.'):

        status_container = st.empty()
        render_status_log(status_container, "Extracting videos from the channels…")

        if not bright_data_api_key:
            render_status_log(
                status_container,
                "BRIGHT_DATA_API_KEY is missing. Check your .env file.",
                state="error",
            )
            return

        valid_channels = [c for c in st.session_state.youtube_channels if c.strip()]
        if not valid_channels:
            render_status_log(status_container, "Add at least one channel URL before starting.", state="error")
            return

        channel_snapshot_id = trigger_scraping_channels(bright_data_api_key, valid_channels, 10, st.session_state.start_date, st.session_state.end_date, "Latest", "")

        if not channel_snapshot_id or "snapshot_id" not in channel_snapshot_id:
            render_status_log(
                status_container,
                f"Bright Data didn't return a snapshot_id. Raw response: {channel_snapshot_id}",
                state="error",
            )
            return

        status = get_progress(bright_data_api_key, channel_snapshot_id['snapshot_id'])
        if not status or "status" not in status:
            render_status_log(status_container, f"Unexpected progress response: {status}", state="error")
            return

        while status['status'] != "ready":
            render_status_log(status_container, f"Current status: {status['status']}", state="warn")
            time.sleep(10)
            status = get_progress(bright_data_api_key, channel_snapshot_id['snapshot_id'])

            if status['status'] == "failed":
                render_status_log(status_container, f"Scraping failed: {status}", state="error")
                return
        
        if status['status'] == "ready":
            render_status_log(status_container, "Scraping completed successfully.", state="done")

            # Show a list of YouTube vidoes here in a scrollable container
            
            channel_scrapped_output = get_output(bright_data_api_key, status['snapshot_id'], format="json")

            if not channel_scrapped_output or not channel_scrapped_output[0]:
                render_status_log(
                    status_container,
                    "Bright Data returned no videos for this channel/date range. Try a wider date range or a different channel.",
                    state="error",
                )
                return

            st.markdown('<div class="stage-label">STAGE 01 · INGEST</div>', unsafe_allow_html=True)
            st.markdown("## YouTube Videos Extracted")
            # Create a container for the carousel
            carousel_container = st.container()

            # Calculate number of videos per row (adjust as needed)
            videos_per_row = 3

            with carousel_container:
                # Calculate number of rows needed
                num_videos = len(channel_scrapped_output[0])
                num_rows = (num_videos + videos_per_row - 1) // videos_per_row
                
                for row in range(num_rows):
                    # Create columns for each row
                    cols = st.columns(videos_per_row)
                    
                    # Fill each column with a video
                    for col_idx in range(videos_per_row):
                        video_idx = row * videos_per_row + col_idx
                        
                        # Check if we still have videos to display
                        if video_idx < num_videos:
                            with cols[col_idx]:
                                with st.container(border=True):
                                    st.video(channel_scrapped_output[0][video_idx]['url'])
                                    st.markdown(
                                        f'<span class="signal-chip">clip {video_idx + 1}</span>',
                                        unsafe_allow_html=True,
                                    )

            render_status_log(status_container, "Processing transcripts…")
            st.session_state.all_files = []
            skipped_videos = 0
            # Calculate transcripts
            for i in tqdm(range(len(channel_scrapped_output[0]))):

                video_record = channel_scrapped_output[0][i]
                transcript = video_record.get('formatted_transcript')

                if not transcript:
                    # No transcript available for this video (captions off,
                    # a Short, members-only, etc.) — skip it rather than crash.
                    skipped_videos += 1
                    continue

                # save transcript to file
                youtube_video_id = video_record['shortcode']

                file = "transcripts/" + youtube_video_id + ".txt"

                with open(file, "w", encoding="utf-8") as f:
                    for segment in transcript:
                        text = segment['text']
                        start_time = segment['start_time']
                        end_time = segment['end_time']
                        f.write(f"({start_time:.2f}-{end_time:.2f}): {text}\n")

                st.session_state.all_files.append(file)

            if skipped_videos:
                render_status_log(
                    status_container,
                    f"Skipped {skipped_videos} video(s) with no available transcript.",
                    state="warn",
                )

            if not st.session_state.all_files:
                render_status_log(
                    status_container,
                    "None of the scraped videos had usable transcripts. Try a different channel or date range.",
                    state="error",
                )
                return

            st.session_state.channel_scrapped_output = channel_scrapped_output
            render_status_log(status_container, "Scraping complete. Handing off to the analysis stage…", state="done")

        else:
            render_status_log(status_container, f"Scraping failed with status: {status}", state="error")

    if status['status'] == "ready":

        status_container = st.empty()
        st.markdown('<div class="stage-label amber">STAGE 02 · SYNTHESIZE</div>', unsafe_allow_html=True)
        with st.spinner('The agent is analyzing the videos... This may take a moment.'):
            # create crew
            st.session_state.crew = create_agents_and_tasks()
            st.session_state.response = st.session_state.crew.kickoff(inputs={"file_paths": ", ".join(st.session_state.all_files)})
            render_status_log(status_container, "Analysis complete. Report ready below.", state="done")
                    


# ===========================
#   Sidebar
# ===========================
with st.sidebar:
    st.markdown('<div class="stage-label">STAGE 01 · INGEST</div>', unsafe_allow_html=True)
    st.header("YouTube Channels")
    st.caption("Add one or more channel URLs to pull recent uploads from.")

    # Initialize the channels list in session state if it doesn't exist
    if "youtube_channels" not in st.session_state:
        st.session_state.youtube_channels = [""]  # Start with one empty field
    
    # Function to add new channel field
    def add_channel_field():
        st.session_state.youtube_channels.append("")
    
    # Create input fields for each channel
    for i, channel in enumerate(st.session_state.youtube_channels):
        col1, col2 = st.columns([6, 1])
        with col1:
            st.session_state.youtube_channels[i] = st.text_input(
                "Channel URL",
                value=channel,
                key=f"channel_{i}",
                label_visibility="collapsed"
            )
        # Show remove button for all except the first field
        with col2:
            if i > 0:
                if st.button("❌", key=f"remove_{i}"):
                    st.session_state.youtube_channels.pop(i)
                    st.rerun()
    
    # Add channel button
    st.button("Add Channel ➕", on_click=add_channel_field)
    
    st.markdown('<hr class="signal-rule">', unsafe_allow_html=True)

    st.subheader("Date Range")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date")
        st.session_state.start_date = start_date
        # store date as string
        st.session_state.start_date = start_date.strftime("%Y-%m-%d")
    with col2:
        end_date = st.date_input("End Date")
        st.session_state.end_date = end_date
        st.session_state.end_date = end_date.strftime("%Y-%m-%d")

    st.markdown('<hr class="signal-rule">', unsafe_allow_html=True)
    st.markdown('<div class="stage-label amber">STAGE 02 · SYNTHESIZE</div>', unsafe_allow_html=True)
    st.button("Start Analysis 🚀", type="primary", on_click=start_analysis, use_container_width=True)
    # st.button("Clear Chat", on_click=reset_chat)

# ===========================
#   Main Chat Interface
# ===========================

def parse_report_sections(raw_markdown):
    """Split the agent's markdown report into a {heading: body} dict using ## headings."""
    sections = {}
    current_heading = "Report"
    buffer = []
    for line in raw_markdown.splitlines():
        match = re.match(r"^#{2,3}\s+(.*)", line)
        if match:
            if buffer:
                sections[current_heading] = "\n".join(buffer).strip()
            current_heading = match.group(1).strip()
            buffer = []
        else:
            buffer.append(line)
    if buffer:
        sections[current_heading] = "\n".join(buffer).strip()
    return sections


def find_section(sections, *keywords):
    """Best-effort match of a section by keyword(s) appearing in its heading."""
    for heading, body in sections.items():
        if any(kw.lower() in heading.lower() for kw in keywords):
            return body
    return None


def to_plain_text(raw_markdown):
    """Very light markdown -> plain text conversion for the .txt export."""
    text = re.sub(r"^#{1,6}\s*", "", raw_markdown, flags=re.MULTILINE)
    text = re.sub(r"[*_`]", "", text)
    return text


# ===========================
#   Main content area — Trend Report Dashboard
# ===========================
if st.session_state.response:
    with st.spinner('Generating content... This may take a moment.'):
        try:
            result = st.session_state.response
            raw_report = result.raw
            sections = parse_report_sections(raw_report)

            num_channels = len(
                [c for c in st.session_state.get("youtube_channels", []) if c.strip()]
            )
            num_videos = len(st.session_state.get("all_files", []))
            word_count = len(raw_report.split())
            read_minutes = max(1, round(word_count / 200))

            st.markdown('<div class="stage-label">OUTPUT · TREND REPORT</div>', unsafe_allow_html=True)
            st.markdown("### Generated Analysis")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Channels scanned", num_channels or "—")
            m2.metric("Videos analyzed", num_videos or "—")
            m3.metric("Date range", f"{st.session_state.get('start_date','—')} → {st.session_state.get('end_date','—')}")
            m4.metric("Est. read time", f"{read_minutes} min")

            st.markdown('<hr class="signal-rule">', unsafe_allow_html=True)

            summary_body = find_section(sections, "summary", "overview", "executive")
            trends_body = find_section(sections, "trend", "theme", "pattern", "analysis")
            recs_body = find_section(sections, "recommend", "action", "next step", "opportunit")

            tab_summary, tab_trends, tab_recs, tab_full = st.tabs(
                ["📊 Executive Summary", "🔎 Trend Breakdown", "💡 Content Recommendations", "📄 Full Report"]
            )

            with tab_summary:
                if summary_body:
                    st.markdown(summary_body)
                else:
                    st.caption("No dedicated summary section was found in the report — showing the top of the full report instead.")
                    st.markdown(raw_report[:1200] + ("…" if len(raw_report) > 1200 else ""))

            with tab_trends:
                if trends_body:
                    st.markdown(trends_body)
                else:
                    st.caption("No dedicated trend-breakdown section was detected — see the full report tab.")

            with tab_recs:
                if recs_body:
                    st.markdown(recs_body)
                else:
                    st.caption("No dedicated recommendations section was detected — see the full report tab.")

            with tab_full:
                st.markdown(raw_report)

            st.markdown('<hr class="signal-rule">', unsafe_allow_html=True)

            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button(
                    label="⬇ Download Markdown",
                    data=raw_report,
                    file_name="youtube_trend_analysis.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with dl2:
                st.download_button(
                    label="⬇ Download Plain Text",
                    data=to_plain_text(raw_report),
                    file_name="youtube_trend_analysis.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

# Footer
st.markdown('<hr class="signal-rule">', unsafe_allow_html=True)
st.markdown(
    '<div style="text-align:center; color: var(--muted); font-family: \'IBM Plex Mono\', monospace; font-size: 12px;">'
    'BUILT WITH CREWAI · BRIGHT DATA · STREAMLIT</div>',
    unsafe_allow_html=True,
)