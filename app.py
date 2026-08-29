import streamlit as st
import subprocess
import os
from faster_whisper import WhisperModel

st.set_page_config(page_title="Pro AI Subtitle Studio", layout="centered")
st.title("🎬 Pro AI Subtitle & Enhancer Studio")
st.caption("Alex Hormozi Style • Pop Bounce • Hinglish Support • Optional 4K Sharpness")

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

# 1. Video Upload
uploaded_file = st.file_uploader("📁 Upload Reel / Video (MP4/MOV)", type=["mp4", "mov"])

# 2. Subtitle Styling Options
st.subheader("🎨 Subtitle Styles & Animation")
col1, col2 = st.columns(2)
with col1:
    preset_style = st.selectbox(
        "✨ Animation Preset",
        ["Alex Hormozi (Bounce + Pop)", "Neon Glow", "3D Bold Shadow", "Classic Minimal"]
    )
    font_family = st.selectbox(
        "🔤 Font Family",
        ["Arial Black", "Impact", "Montserrat Black", "Trebuchet MS", "Verdana"]
    )
    words_per_line = st.radio(
        "📝 Words per Screen",
        ["1 Word (Fast Reels)", "2-3 Words (Natural)", "Full Sentence"],
        index=0
    )

with col2:
    highlight_color = st.selectbox(
        "🎯 Active Highlight Color",
        ["Neon Yellow", "Neon Green", "Cyan Blue", "Hot Pink", "Electric Orange", "Bright Red"]
    )
    font_size = st.slider("📏 Font Size", 40, 130, 80, step=5)
    position = st.selectbox(
        "📍 Text Position",
        ["Center-Bottom", "Middle Center", "Lower Bottom", "Top Header"]
    )

# 3. Language & Output Mode (Hinglish / Translation Fix)
st.subheader("🌐 Language & Translation")
col_lang1, col_lang2 = st.columns(2)
with col_lang1:
    sub_mode = st.selectbox(
        "Subtitle Output Mode",
        [
            "English Translation (English Words)",
            "Hinglish / Roman Hindi (Audio as English Letters)",
            "Original Audio"
        ]
    )
with col_lang2:
    all_uppercase = st.checkbox("🔠 All CAPS (Uppercase)", value=True)

# 4. Optional Quality Enhancer
st.subheader("✨ Video Quality Settings")
enable_enhancer = st.checkbox("Enable Video Quality & Sharpness Boost (Optional)", value=False)

sharpness_level = "High Sharpness"
if enable_enhancer:
    sharpness_level = st.select_slider(
        "Sharpness & Clarity Level",
        options=["Subtle Clear", "High Sharpness", "Ultra 4K Feel"],
        value="High Sharpness"
    )

# 5. Processing & Rendering Logic
if st.button("Generate Subtitles ⚡", type="primary") and uploaded_file is not None:
    with st.spinner("Processing Audio Transcription & Styling Video..."):
        with open("temp_input.mp4", "wb") as f:
            f.write(uploaded_file.read())

        # ASS BGR Colors
        color_map = {
            "Neon Yellow": "&H0000FFFF&",
            "Neon Green": "&H0000FF00&",
            "Cyan Blue": "&H00FFFF00&",
            "Hot Pink": "&H00D900FF&",
            "Electric Orange": "&H000088FF&",
            "Bright Red": "&H000000FF&"
        }
        active_color = color_map.get(highlight_color, "&H0000FFFF&")

        pos_map = {
            "Center-Bottom": 450,
            "Middle Center": 900,
            "Lower Bottom": 220,
            "Top Header": 1600
        }
        margin_v = pos_map.get(position, 450)

        # Style tag mapping
        outline_size = 8
        shadow_size = 4
        if preset_style == "Alex Hormozi (Bounce + Pop)":
            effect_tag = f"{{\\c{active_color}\\t(0,70,\\fscx125\\fscy125)\\t(70,140,\\fscx100\\fscy100)\\shad5}}"
        elif preset_style == "Neon Glow":
            effect_tag = f"{{\\c{active_color}\\blur6\\3c{active_color}\\shad0}}"
            outline_size = 4
        elif preset_style == "3D Bold Shadow":
            effect_tag = f"{{\\c{active_color}\\shad8\\4c&H00000000&}}"
            outline_size = 10
        else:
            effect_tag = f"{{\\c{active_color}}}"
            outline_size = 5
            shadow_size = 2

        # Language transcription configuration
        if sub_mode == "English Translation (English Words)":
            prompt_text = "Translate audio accurately into clear English words."
            segments, _ = model.transcribe(
                "temp_input.mp4",
                word_timestamps=True,
                task="translate",
                initial_prompt=prompt_text
            )
        elif sub_mode == "Hinglish / Roman Hindi (Audio as English Letters)":
            # Force Whisper to use Latin / Roman script for Hindi words
            prompt_text = "Transcribe the Hindi and Urdu speech strictly using English Roman alphabet like: kya hal hai, kaise ho, video, subscribe, follow."
            segments, _ = model.transcribe(
                "temp_input.mp4",
                word_timestamps=True,
                language="en",
                initial_prompt=prompt_text
            )
        else:
            prompt_text = "Transcribe clearly without Arabic or Urdu script."
            segments, _ = model.transcribe(
                "temp_input.mp4",
                word_timestamps=True,
                initial_prompt=prompt_text
            )

        # Header generation
        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ReelStyle,{font_family},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,{outline_size},{shadow_size},2,20,20,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        if words_per_line == "1 Word (Fast Reels)":
            for segment in segments:
                for word in segment.words:
                    start = format_ass_time(word.start)
                    end = format_ass_time(word.end)
                    text = word.word.strip()
                    if all_uppercase:
                        text = text.upper()
                    events.append(f"Dialogue: 0,{start},{end},ReelStyle,,0,0,0,,{effect_tag}{text}")
        elif words_per_line == "2-3 Words (Natural)":
            for segment in segments:
                words = segment.words
                chunk_size = 3
                for i in range(0, len(words), chunk_size):
                    chunk = words[i:i + chunk_size]
                    if not chunk:
                        continue
                    start = format_ass_time(chunk[0].start)
                    end = format_ass_time(chunk[-1].end)
                    text_parts = [w.word.strip() for w in chunk]
                    text = " ".join(text_parts)
                    if all_uppercase:
                        text = text.upper()
                    events.append(f"Dialogue: 0,{start},{end},ReelStyle,,0,0,0,,{effect_tag}{text}")
        else:
            for segment in segments:
                start = format_ass_time(segment.start)
                end = format_ass_time(segment.end)
                text = segment.text.strip()
                if all_uppercase:
                    text = text.upper()
                events.append(f"Dialogue: 0,{start},{end},ReelStyle,,0,0,0,,{effect_tag}{text}")

        with open("subtitles.ass", "w", encoding="utf-8") as f:
            f.write(ass_header + "\n".join(events))

        # Check quality enhancer toggle
        if enable_enhancer:
            if sharpness_level == "Subtle Clear":
                enhance_filter = "unsharp=5:5:0.8:5:5:0.0,eq=contrast=1.05:saturation=1.1"
            elif sharpness_level == "High Sharpness":
                enhance_filter = "unsharp=7:7:1.4:7:7:0.0,eq=contrast=1.1:saturation=1.15"
            else:
                enhance_filter = "unsharp=9:9:1.8:9:9:0.0,eq=contrast=1.15:saturation=1.22:brightness=0.01"
            vf_command = f'ass=subtitles.ass,{enhance_filter}'
        else:
            vf_command = 'ass=subtitles.ass'

        cmd = f'ffmpeg -y -i temp_input.mp4 -vf "{vf_command}" -c:v libx264 -pix_fmt yuv420p -preset ultrafast -c:a aac output.mp4'
        subprocess.run(cmd, shell=True)

        st.success("🎉 Video Ready!")
        st.video("output.mp4")
        with open("output.mp4", "rb") as file:
            st.download_button("📥 Download Styled Reel", data=file, file_name="styled_reel.mp4", mime="video/mp4")
            
