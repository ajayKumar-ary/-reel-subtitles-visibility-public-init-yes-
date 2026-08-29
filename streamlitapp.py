import streamlit as st
import subprocess
import os
from faster_whisper import WhisperModel

st.set_page_config(page_title="AI Subtitle Generator", layout="centered")
st.title("🎬 AI Reel Subtitle Studio")

@st.cache_resource
def load_model():
    return WhisperModel("base", device="cpu", compute_type="int8")

model = load_model()

def format_ass_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds - int(seconds)) * 100)
    return f"{hours:d}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

uploaded_file = st.file_uploader("Upload Reel / Video", type=["mp4", "mov"])
highlight_color = st.selectbox("Highlight Color", ["Yellow", "Neon Green", "Cyan Blue", "Bright Red"])
font_size = st.slider("Font Size", 40, 110, 75)
position = st.radio("Position", ["Center-Bottom", "Center", "Bottom"])

if st.button("Generate Subtitles ⚡") and uploaded_file is not None:
    with st.spinner("Processing & Rendering Subtitles in English..."):
        with open("temp_input.mp4", "wb") as f:
            f.write(uploaded_file.read())

        color_map = {
            "Yellow": "&H0000FFFF&",
            "Neon Green": "&H0000FF00&",
            "Cyan Blue": "&H00FFFF00&",
            "Bright Red": "&H000000FF&"
        }
        active_color = color_map.get(highlight_color, "&H0000FFFF&")
        margin_v = 400 if position == "Center-Bottom" else (800 if position == "Center" else 200)

        # task="translate" lagane se kabhi Urdu ya galat bhasha nahi aayegi, direct English subtitles banenge
        segments, _ = model.transcribe("temp_input.mp4", word_timestamps=True, task="translate")

        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ReelStyle,Arial Black,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,8,0,2,20,20,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        for segment in segments:
            for word in segment.words:
                start = format_ass_time(word.start)
                end = format_ass_time(word.end)
                text = word.word.strip().upper()
                events.append(f"Dialogue: 0,{start},{end},ReelStyle,,0,0,0,,{{\\c{active_color}}}{text}")

        with open("subtitles.ass", "w", encoding="utf-8") as f:
            f.write(ass_header + "\n".join(events))

        cmd = 'ffmpeg -y -i temp_input.mp4 -vf "ass=subtitles.ass" -c:v libx264 -pix_fmt yuv420p -preset ultrafast -c:a aac output.mp4'
        subprocess.run(cmd, shell=True)

        st.success("Subtitles Complete!")
        st.video("output.mp4")
        with open("output.mp4", "rb") as file:
            st.download_button("Download Styled Reel", data=file, file_name="styled_reel.mp4", mime="video/mp4")
            
