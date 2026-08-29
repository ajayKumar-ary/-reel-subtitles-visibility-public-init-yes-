import streamlit as st
import subprocess
import os
import re
import cv2
import numpy as np
from faster_whisper import WhisperModel
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

st.set_page_config(
    page_title="CaptionVFX Studio • Pro AI Video Suite",
    page_icon="🎬",
    layout="wide"
)

# Custom Sleek Modern CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1.2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: white !important;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    .main-header p {
        color: #e2e8f0;
        font-size: 1.05rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        border-radius: 8px;
        background-color: #1e293b;
        color: white;
        padding: 0 20px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #6366f1, #8b5cf6) !important;
        color: white !important;
    }
    .status-card {
        background-color: #0f172a;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)

# Header Banner
st.markdown("""
<div class="main-header">
    <h1>🎬 CaptionVFX Studio AI</h1>
    <p>CapCut Style Animations • Dynamic Auto-Color • True Hinglish • 4K Quality</p>
</div>
""", unsafe_allow_html=True)

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
    has_devanagari = re.search(r'[\u0900-\u097F]', text)
    if has_devanagari:
        text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    text = re.sub(r'[\u0600-\u06FF\u0750-\u077F]', '', text)
    return text.strip()

def detect_best_contrast_color(video_path):
    cap = cv2.VideoCapture(video_path)
    success, frame = cap.read()
    cap.release()
    if not success or frame is None:
        return "&H0000FFFF&"
    h, w, _ = frame.shape
    bottom_crop = frame[int(h * 0.65):h, 0:w]
    avg_b = float(np.mean(bottom_crop[:, :, 0]))
    avg_g = float(np.mean(bottom_crop[:, :, 1]))
    avg_r = float(np.mean(bottom_crop[:, :, 2]))
    brightness = 0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b

    if brightness > 150:
        return "&H00FF5500&"
    elif avg_g > avg_r and avg_g > avg_b:
        return "&H00D900FF&"
    elif avg_r > avg_g and avg_r > avg_b:
        return "&H0000FF00&"
    else:
        return "&H0000FFFF&"

# Left Column (Upload) & Right Column (Tabs & Settings)
col_left, col_right = st.columns([1.1, 1.4], gap="large")

with col_left:
    st.markdown("### 📁 1. Video Upload")
    uploaded_file = st.file_uploader("Upload Reel / Short Video (MP4/MOV)", type=["mp4", "mov"])
    if uploaded_file:
        st.video(uploaded_file)

with col_right:
    st.markdown("### ⚙️ 2. Customization Studio")
    tab_style, tab_lang, tab_video = st.tabs(["🎨 Subtitle Style", "🌐 Language Engine", "⚡ Speed & 4K Quality"])

    with tab_style:
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            preset_style = st.selectbox(
                "✨ VFX Preset",
                [
                    "🔥 Hormozi Pop-Bounce",
                    "🎤 CapCut Karaoke Highlight",
                    "⚡ Neon Cyberpunk Glow",
                    "🧊 3D Deep Shadow Drop",
                    "✨ Smooth Fade-In Up",
                    "🎯 Clean Minimal"
                ]
            )
            font_family = st.selectbox(
                "🔤 Font Family",
                ["Arial Black", "Impact", "Montserrat Black", "Trebuchet MS", "Verdana"]
            )
            words_per_line = st.radio(
                "📝 Layout Mode",
                ["1 Word (Fast Reels)", "2-3 Words (Natural)", "Full Sentence"],
                horizontal=True
            )
        with sub_col2:
            highlight_color_choice = st.selectbox(
                "🎨 Active Highlight Color",
                [
                    "🤖 Auto-Detect (AI Video Contrast)",
                    "Neon Yellow",
                    "Neon Green",
                    "Cyan Blue",
                    "Hot Pink",
                    "Electric Orange",
                    "Bright Red"
                ]
            )
            font_size = st.slider("📏 Font Size", 40, 130, 80, step=5)
            position = st.selectbox(
                "📍 Subtitle Position",
                ["Center-Bottom", "Middle Center", "Lower Bottom", "Top Header"]
            )

    with tab_lang:
        lang_col1, lang_col2 = st.columns(2)
        with lang_col1:
            language_choice = st.selectbox(
                "Select Audio Language",
                [
                    "Pure Hinglish / Roman Hindi",
                    "Auto-Detect Language",
                    "English",
                    "Hindi (हिन्दी)",
                    "Spanish (Español)",
                    "French (Français)",
                    "German (Deutsch)",
                    "Russian (Русский)",
                    "Arabic (العربية)",
                    "Japanese (日本語)"
                ]
            )
        with lang_col2:
            translate_to_en = st.checkbox("🔄 Auto-Translate to English Words", value=False)
            all_uppercase = st.checkbox("🔠 Convert All to UPPERCASE", value=True)

    with tab_video:
        vid_col1, vid_col2 = st.columns(2)
        with vid_col1:
            enable_slowmo = st.checkbox("Enable Slow Motion", value=False)
            speed_rate = "0.5x (Smooth Half Speed)"
            if enable_slowmo:
                speed_rate = st.selectbox(
                    "Speed Factor",
                    ["0.75x (Cinematic Slow)", "0.5x (Smooth Half Speed)", "0.25x (Super Slow-Mo)"]
                )
        with vid_col2:
            enable_enhancer = st.checkbox("Enable 4K Clarity Boost", value=False)
            sharpness_level = "High Sharpness"
            if enable_enhancer:
                sharpness_level = st.select_slider(
                    "Sharpness Boost",
                    options=["Subtle Clear", "High Sharpness", "Ultra 4K Feel"],
                    value="High Sharpness"
                )

st.markdown("---")

# Render Action Button
if st.button("🚀 Render & Export Video", type="primary", use_container_width=True) and uploaded_file is not None:
    with st.spinner("Processing AI Subtitles & Rendering Final Video..."):
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

        if "Auto-Detect" in highlight_color_choice:
            active_color = detect_best_contrast_color("temp_input.mp4")
        else:
            active_color = color_map.get(highlight_color_choice, "&H0000FFFF&")

        pos_map = {
            "Center-Bottom": 450,
            "Middle Center": 900,
            "Lower Bottom": 220,
            "Top Header": 1600
        }
        margin_v = pos_map.get(position, 450)

        outline_size = 8
        shadow_size = 4
        if "Hormozi Pop-Bounce" in preset_style:
            effect_tag = f"{{\\c{active_color}\\t(0,70,\\fscx125\\fscy125)\\t(70,140,\\fscx100\\fscy100)\\shad5}}"
        elif "Karaoke" in preset_style:
            effect_tag = f"{{\\c{active_color}\\2c&H00FFFFFF&\\k50}}"
            outline_size = 6
        elif "Neon Cyberpunk" in preset_style:
            effect_tag = f"{{\\c{active_color}\\blur7\\3c{active_color}\\shad0}}"
            outline_size = 4
        elif "3D Deep Shadow" in preset_style:
            effect_tag = f"{{\\c{active_color}\\shad10\\4c&H00000000&}}"
            outline_size = 10
        elif "Fade-In Up" in preset_style:
            effect_tag = f"{{\\c{active_color}\\fad(120,60)}}"
        else:
            effect_tag = f"{{\\c{active_color}}}"
            outline_size = 5
            shadow_size = 2

        lang_code_map = {
            "English": "en", "Hindi (हिन्दी)": "hi", "Spanish (Español)": "es",
            "French (Français)": "fr", "German (Deutsch)": "de", "Russian (Русский)": "ru",
            "Arabic (العربية)": "ar", "Japanese (日本語)": "ja"
        }

        convert_to_roman = False
        task_type = "translate" if translate_to_en else "transcribe"

        if language_choice == "Pure Hinglish / Roman Hindi":
            segments, _ = model.transcribe("temp_input.mp4", word_timestamps=True, language="hi", initial_prompt="यह हिंदी में है।")
            convert_to_roman = True
        elif language_choice in lang_code_map:
            segments, _ = model.transcribe("temp_input.mp4", word_timestamps=True, language=lang_code_map[language_choice], task=task_type)
        else:
            segments, _ = model.transcribe("temp_input.mp4", word_timestamps=True, task=task_type)

        speed_factor = 1.0
        if enable_slowmo:
            if "0.75x" in speed_rate:
                speed_factor = 1.0 / 0.75
            elif "0.5x" in speed_rate:
                speed_factor = 2.0
            elif "0.25x" in speed_rate:
                speed_factor = 4.0

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
                    start = format_ass_time(word.start * speed_factor)
                    end = format_ass_time(word.end * speed_factor)
                    text = word.word.strip()
                    if convert_to_roman:
                        text = clean_to_roman_text(text)
                    if all_uppercase:
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
                    start = format_ass_time(chunk[0].start * speed_factor)
                    end = format_ass_time(chunk[-1].end * speed_factor)
                    text_parts = []
                    for w in chunk:
                        wt = w.word.strip()
                        if convert_to_roman:
                            wt = clean_to_roman_text(wt)
                        if wt:
                            text_parts.append(wt)
                    text = " ".join(text_parts)
                    if all_uppercase:
                        text = text.upper()
                    if text:
                        events.append(f"Dialogue: 0,{start},{end},ReelStyle,,0,0,0,,{effect_tag}{text}")
        else:
            for segment in segments:
                start = format_ass_time(segment.start * speed_factor)
                end = format_ass_time(segment.end * speed_factor)
                text = segment.text.strip()
                if convert_to_roman:
                    text = clean_to_roman_text(text)
                if all_uppercase:
                    text = text.upper()
                if text:
                    events.append(f"Dialogue: 0,{start},{end},ReelStyle,,0,0,0,,{effect_tag}{text}")

        with open("subtitles.ass", "w", encoding="utf-8") as f:
            f.write(ass_header + "\n".join(events))

        vf_filters = ["ass=subtitles.ass"]
        af_filters = []

        if enable_slowmo:
            if "0.75x" in speed_rate:
                vf_filters.insert(0, "setpts=1.333*PTS")
                af_filters.append("atempo=0.75")
            elif "0.5x" in speed_rate:
                vf_filters.insert(0, "setpts=2.0*PTS")
                af_filters.append("atempo=0.5")
            elif "0.25x" in speed_rate:
                vf_filters.insert(0, "setpts=4.0*PTS")
                af_filters.append("atempo=0.5,atempo=0.5")

        if enable_enhancer:
            if sharpness_level == "Subtle Clear":
                vf_filters.append("unsharp=5:5:0.8:5:5:0.0,eq=contrast=1.05:saturation=1.1")
            elif sharpness_level == "High Sharpness":
                vf_filters.append("unsharp=7:7:1.4:7:7:0.0,eq=contrast=1.1:saturation=1.15")
            else:
                vf_filters.append("unsharp=9:9:1.8:9:9:0.0,eq=contrast=1.15:saturation=1.22:brightness=0.01")

        vf_str = ",".join(vf_filters)
        af_str = f'-af "{",".join(af_filters)}"' if af_filters else '-c:a aac'

        cmd = f'ffmpeg -y -i temp_input.mp4 -vf "{vf_str}" {af_str} -c:v libx264 -pix_fmt yuv420p -preset ultrafast output.mp4'
        subprocess.run(cmd, shell=True)

        st.success("🎉 Video Successfully Rendered!")
        st.video("output.mp4")
        with open("output.mp4", "rb") as file:
            st.download_button("📥 Download Final Reel", data=file, file_name="caption_vfx_reel.mp4", mime="video/mp4", use_container_width=True)
             
