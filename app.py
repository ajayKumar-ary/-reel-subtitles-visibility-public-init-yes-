import streamlit as st
import subprocess
import os
import re
from faster_whisper import WhisperModel
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

st.set_page_config(page_title="AI Subtitle Studio", layout="centered")
st.title("🎬 AI Subtitle Studio (100% English Script)")

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

def clean_to_roman_text(text):
    # Agar text me Devanagari Hindi hai, toh use Roman English me convert karega
    has_devanagari = re.search(r'[\u0900-\u097F]', text)
    if has_devanagari:
        text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    
    # Arabic/Urdu characters ko remove karke clean English rakhna
    text = re.sub(r'[\u0600-\u06FF\u0750-\u077F]', '', text)
    return text.strip()

# 1. Video Upload
uploaded_file = st.file_uploader("📁 Upload Reel / Video (MP4/MOV)", type=["mp4", "mov"])

# 2. Options
st.subheader("🎨 Subtitle Controls")
col1, col2 = st.columns(2)
with col1:
    preset_style = st.selectbox(
        "✨ Animation Preset",
        ["Alex Hormozi (Bounce + Pop)", "Neon Glow", "3D Bold Shadow", "Classic Minimal"]
    )
    words_per_line = st.radio(
        "📝 Words per Screen",
        ["1 Word (Fast Reels)", "2-3 Words (Natural)", "Full Sentence"],
        index=0
    )

with col2:
    highlight_color = st.selectbox(
        "🎯 Highlight Color",
        ["Neon Yellow", "Neon Green", "Cyan Blue", "Hot Pink", "Electric Orange", "Bright Red"]
    )
    font_size = st.slider("📏 Font Size", 40, 130, 80, step=5)

# Mode Selector
sub_mode = st.radio(
    "🌐 Subtitle Style Mode",
    [
        "Pure Hinglish / Roman Script (Jo bol rahe hain wahi English letters me)",
        "English Meaning Translation (Pure English Translation)"
    ]
)

# Optional Enhancer
enable_enhancer = st.checkbox("✨ Enhance Video Quality & Sharpness Boost", value=False)

if st.button("Generate Subtitles ⚡", type="primary") and uploaded_file is not None:
    with st.spinner("Processing Audio Transcription..."):
        with open("temp_input.mp4", "wb") as f:
            f.write(uploaded_file.read())

        color_map = {
            "Neon Yellow": "&H0000FFFF&",
            "Neon Green": "&H0000FF00&",
            "Cyan Blue": "&H00FFFF00&",
            "Hot Pink": "&H00D900FF&",
            "Electric Orange": "&H000088FF&",
            "Bright Red": "&H000000FF&"
        }
        active_color = color_map.get(highlight_color, "&H0000FFFF&")

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

        # Forced Hindi detection + Transliteration logic
        if "Pure Hinglish" in sub_mode:
            # language='hi' lock karne se Urdu detection 0% ho jayegi
            segments, _ = model.transcribe(
                "temp_input.mp4",
                word_timestamps=True,
                language="hi",
                initial_prompt="यह हिंदी भाषा में है।"
            )
            convert_to_roman = True
        else:
            segments, _ = model.transcribe(
                "temp_input.mp4",
                word_timestamps=True,
                task="translate"
            )
            convert_to_roman = False

        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ReelStyle,Arial Black,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,{outline_size},{shadow_size},2,20,20,450,1

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
                    if convert_to_roman:
                        text = clean_to_roman_text(text)
                    text = text.upper()
                    if text:
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
                    text_parts = []
                    for w in chunk:
                        wt = w.word.strip()
                        if convert_to_roman:
                            wt = clean_to_roman_text(wt)
                        if wt:
                            text_parts.append(wt)
                    text = " ".join(text_parts).upper()
                    if text:
                        events.append(f"Dialogue: 0,{start},{end},ReelStyle,,0,0,0,,{effect_tag}{text}")
        else:
            for segment in segments:
                start = format_ass_time(segment.start)
                end = format_ass_time(segment.end)
                text = segment.text.strip()
                if convert_to_roman:
                    text = clean_to_roman_text(text)
                text = text.upper()
                if text:
                    events.append(f"Dialogue: 0,{start},{end},ReelStyle,,0,0,0,,{effect_tag}{text}")

        with open("subtitles.ass", "w", encoding="utf-8") as f:
            f.write(ass_header + "\n".join(events))

        if enable_enhancer:
            vf_command = 'ass=subtitles.ass,unsharp=7:7:1.4:7:7:0.0,eq=contrast=1.1:saturation=1.15'
        else:
            vf_command = 'ass=subtitles.ass'

        cmd = f'ffmpeg -y -i temp_input.mp4 -vf "{vf_command}" -c:v libx264 -pix_fmt yuv420p -preset ultrafast -c:a aac output.mp4'
        subprocess.run(cmd, shell=True)

        st.success("🎉 Video Ready!")
        st.video("output.mp4")
        with open("output.mp4", "rb") as file:
            st.download_button("📥 Download Styled Reel", data=file, file_name="styled_reel.mp4", mime="video/mp4")
                
