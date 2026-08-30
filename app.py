import streamlit as st
import os
import subprocess
import whisper
import gc
import re
import tempfile

# ----------------- PAGE CONFIG -----------------
st.set_page_config(
    page_title="CaptionVFX AI Studio Pro",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ----------------- CUSTOM CSS -----------------
st.markdown("""
<style>
    .main { background-color: #0f172a; color: #ffffff; }
    .stButton>button {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# ----------------- HELPER FUNCTIONS -----------------
def format_timestamp_ass(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:01d}:{minutes:02d}:{secs:05.2f}"

def cleanup_files(files_list):
    for f in files_list:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

# ----------------- SUBTITLE GENERATOR -----------------
def generate_ass_subtitles(segments, font_style, font_size, primary_color, outline_color, position):
    # Position: Bottom (2), Middle (5), Top (8)
    align_val = 2
    margin_v = 40
    if position == "Middle":
        align_val = 5
        margin_v = 0
    elif position == "Top":
        align_val = 8
        margin_v = 40

    # Color mapping to ASS BGR format
    colors_map = {
        "Yellow": "&H0000FFFF",
        "White": "&H00FFFFFF",
        "Cyan": "&H00FFFF00",
        "Green": "&H0000FF00"
    }
    outline_map = {
        "Black": "&H00000000",
        "Dark Red": "&H0000008B",
        "Dark Blue": "&H008B0000"
    }

    pri_c = colors_map.get(primary_color, "&H0000FFFF")
    out_c = outline_map.get(outline_color, "&H00000000")

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,{font_size},{pri_c},&H000000FF,{out_c},&H80000000,-1,0,0,0,100,100,0,0,1,3.5,0,{align_val},20,20,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for seg in segments:
        start_time = format_timestamp_ass(seg['start'])
        end_time = format_timestamp_ass(seg['end'])
        text = seg['text'].strip().upper()
        
        # Word-by-word or short chunk formatting
        words = text.split()
        if len(words) > 4:
            # Chunking long sentences for Reels
            chunk_duration = (seg['end'] - seg['start']) / 2
            mid_time = seg['start'] + chunk_duration
            
            w1 = " ".join(words[:len(words)//2])
            w2 = " ".join(words[len(words)//2:])
            
            events.append(f"Dialogue: 0,{start_time},{format_timestamp_ass(mid_time)},Default,,0,0,0,,{{\\fad(80,80)}}{w1}")
            events.append(f"Dialogue: 0,{format_timestamp_ass(mid_time)},{end_time},Default,,0,0,0,,{{\\fad(80,80)}}{w2}")
        else:
            events.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{{\\fad(80,80)}}{text}")

    return ass_header + "\n".join(events)

# ----------------- MAIN UI -----------------
st.title("🎬 CaptionVFX AI Studio Pro")
st.caption("AI-Powered Auto Subtitles & Viral Reel Enhancer")

uploaded_file = st.file_uploader("📤 Upload Video (MP4/MOV)", type=["mp4", "mov"])

if uploaded_file:
    with open("temp_input.mp4", "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.video("temp_input.mp4")

    st.subheader("⚙️ Customization Settings")
    col1, col2 = st.columns(2)
    with col1:
        font_size = st.slider("Font Size", 18, 48, 32)
        primary_color = st.selectbox("Primary Color", ["Yellow", "White", "Cyan", "Green"])
        position = st.selectbox("Subtitle Position", ["Bottom", "Middle", "Top"])
    with col2:
        outline_color = st.selectbox("Outline Color", ["Black", "Dark Red", "Dark Blue"])
        whisper_model = st.selectbox("Whisper AI Model", ["base", "tiny", "small"])
        enable_enhancer = st.checkbox("AI Clarity & Sharpness Boost", value=True)

    if st.button("🚀 Render Subtitled Video", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 1. Extract Audio
        status_text.text("🎙️ Extracting Audio...")
        progress_bar.progress(20)
        cmd_extract = "ffmpeg -y -i temp_input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 temp_audio.wav"
        subprocess.run(cmd_extract, shell=True, capture_output=True)

        # 2. Whisper Speech Recognition
        status_text.text("🤖 Generating AI Subtitles (Whisper)...")
        progress_bar.progress(45)
        model = whisper.load_model(whisper_model)
        transcription = model.transcribe("temp_audio.wav", fp16=False)

        # 3. Create ASS Subtitle file
        status_text.text("🎨 Styling Subtitle Animations...")
        progress_bar.progress(65)
        ass_content = generate_ass_subtitles(
            transcription["segments"],
            "DejaVu Sans",
            font_size,
            primary_color,
            outline_color,
            position
        )
        with open("subtitles.ass", "w", encoding="utf-8") as f:
            f.write(ass_content)

        # 4. FFmpeg Video Merge
        status_text.text("⚡ Final Video Rendering...")
        progress_bar.progress(85)
        
        vf_filters = ["ass=subtitles.ass"]
        if enable_enhancer:
            vf_filters.append("unsharp=5:5:0.8:5:5:0.0,eq=contrast=1.05:saturation=1.12")
        
        vf_str = ",".join(vf_filters)
        cmd_render = f'ffmpeg -y -i temp_input.mp4 -vf "{vf_str}" -c:a copy -c:v libx264 -preset ultrafast -pix_fmt yuv420p output.mp4'
        subprocess.run(cmd_render, shell=True, capture_output=True)

        progress_bar.progress(100)
        status_text.empty()

        # 5. Result Display & Download
        if os.path.exists("output.mp4") and os.path.getsize("output.mp4") > 1000:
            st.success("✅ Reel Successfully Rendered!")
            with open("output.mp4", "rb") as vid_file:
                video_bytes = vid_file.read()
                st.video(video_bytes)
                st.download_button(
                    label="📥 Download Subtitled Reel (MP4)",
                    data=video_bytes,
                    file_name="edited_viral_reel.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )
        else:
            st.error("Rendering issue detected. Please verify packages.txt has ffmpeg installed.")

        cleanup_files(["temp_input.mp4", "temp_audio.wav", "subtitles.ass", "output.mp4"])
        gc.collect()
    
