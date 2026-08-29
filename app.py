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
    page_title="CaptionVFX Studio AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        text-align: center;
        padding: 0.8rem;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        border-radius: 10px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .main-title h2 {
        color: white !important;
        margin: 0;
        font-weight: 700;
    }
    .main-title p {
        margin: 0.2rem 0 0 0;
        color: #e0e7ff;
        font-size: 0.95rem;
    }
    .stButton button {
        background: linear-gradient(90deg, #4f46e5, #7c3aed) !important;
        color: white !important;
        font-weight: 700 !important;
        height: 3rem !important;
        border-radius: 8px !important;
    }
</style>
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

def classify_reel_vibe(transcript_text):
    text_lower = transcript_text.lower()
    
    # 1. Introduction / Fast Hook
    if any(w in text_lower for w in ["welcome", "hello", "today", "aaj", "dekho", "listen", "secret", "kaise", "stop", "wait"]):
        return {
            "name": "⚡ Intro / High-Energy Hook",
            "tag": r"{\t(0,70,\fscx130\fscy130)\t(70,140,\fscx100\fscy100)\shad6}",
            "font": "Impact",
            "words": "1 Word",
            "outline": 8, "shadow": 4
        }
    # 2. Vlog / Travel / Lifestyle
    elif any(w in text_lower for w in ["vlog", "travel", "trip", "morning", "life", "friends", "khana", "market", "day"]):
        return {
            "name": "🎬 Travel & Daily Vlog",
            "tag": r"{\fad(140,80)}",
            "font": "Montserrat Black",
            "words": "2-3 Words",
            "outline": 6, "shadow": 2
        }
    # 3. Motivation / Fitness / Success
    elif any(w in text_lower for w in ["hardwork", "success", "mehnat", "gym", "money", "focus", "goal", "mindset", "power"]):
        return {
            "name": "🔥 Motivation & Fitness",
            "tag": r"{\blur6\t(0,60,\fscx120\fscy120)\t(60,120,\fscx100\fscy100)}",
            "font": "Arial Black",
            "words": "1 Word",
            "outline": 10, "shadow": 5
        }
    # 4. Podcast / Story / Casual
    else:
        return {
            "name": "🎙️ Podcast & Storytelling",
            "tag": r"{\2c&H00FFFFFF&\k45}",
            "font": "Trebuchet MS",
            "words": "2-3 Words",
            "outline": 6, "shadow": 3
        }

# ==================== SIDEBAR CONTROLS ====================
st.sidebar.markdown("## ⚙️ Studio Controls")

# AI Auto-Motion Toggle
with st.sidebar.expander("🤖 AI Auto-Motion & Genre Matching", expanded=True):
    auto_vibe = st.checkbox("AI Auto-Detect Reel Type (Vlog/Intro/Podcast)", value=True)
    st.caption("AI video ke words sun kar automatically motion aur font match karega.")

# Manual Styling (agar user khud customize karna chahe)
with st.sidebar.expander("🎨 Manual VFX & Style Settings", expanded=False):
    preset_style = st.selectbox(
        "✨ Animation Preset",
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
        "📝 Layout Flow",
        ["1 Word (Fast Reels)", "2-3 Words (Natural)", "Full Sentence"]
    )
    font_size = st.slider("📏 Font Size", 40, 130, 80, step=5)
    position = st.selectbox(
        "📍 Text Position",
        ["Center-Bottom", "Middle Center", "Lower Bottom", "Top Header"]
    )

# Highlight Color Settings
with st.sidebar.expander("🎯 Color Settings", expanded=False):
    highlight_color_choice = st.selectbox(
        "Highlight Color",
        [
            "🤖 Auto-Detect (Video AI Contrast)",
            "Neon Yellow",
            "Neon Green",
            "Cyan Blue",
            "Hot Pink",
            "Electric Orange",
            "Bright Red"
        ]
    )

# Language Settings
with st.sidebar.expander("🌐 Language & Translation", expanded=False):
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
    translate_to_en = st.checkbox("🔄 Translate to English Words", value=False)
    all_uppercase = st.checkbox("🔠 Convert All to UPPERCASE", value=True)

# Speed & 4K Enhancer
with st.sidebar.expander("⚡ Speed & 4K Quality Boost", expanded=False):
    enable_slowmo = st.checkbox("Enable Slow Motion", value=False)
    speed_rate = "0.5x (Smooth Half Speed)"
    if enable_slowmo:
        speed_rate = st.selectbox(
            "Speed Factor",
            ["0.75x (Cinematic Slow)", "0.5x (Smooth Half Speed)", "0.25x (Super Slow-Mo)"]
        )
    
    st.markdown("---")
    enable_enhancer = st.checkbox("Enable 4K Clarity Boost", value=False)
    sharpness_level = "High Sharpness"
    if enable_enhancer:
        sharpness_level = st.select_slider(
            "Sharpness Level",
            options=["Subtle Clear", "High Sharpness", "Ultra 4K Feel"],
            value="High Sharpness"
        )

# ==================== MAIN WORKSPACE ====================
st.markdown("""
<div class="main-title">
    <h2>🎬 CaptionVFX AI Studio</h2>
    <p>Auto-Genre Motion • CapCut VFX • True Hinglish • AI Color Match</p>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("📁 Upload Reel / Short Video (MP4/MOV)", type=["mp4", "mov"])

if uploaded_file:
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.markdown("##### 📹 Original Video Preview")
        st.video(uploaded_file)

    with col_v2:
        st.markdown("##### ⚡ Render Workspace")
        st.info("💡 Side panel se AI Auto-Motion, Language ya 4K Enhancer customize karein.")
        render_clicked = st.button("🚀 Render Subtitled Video", use_container_width=True)

    if render_clicked:
        with st.spinner("AI analyzing video content & generating subtitles..."):
            with open("temp_input.mp4", "wb") as f:
                f.write(uploaded_file.read())

            # Color Selection
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

            # Language & Transcription
            lang_code_map = {
                "English": "en", "Hindi (हिन्दी)": "hi", "Spanish (Español)": "es",
                "French (Français)": "fr", "German (Deutsch)": "de", "Russian (Русский)": "ru",
                "Arabic (العربية)": "ar", "Japanese (日本語)": "ja"
            }

            convert_to_roman = False
            task_type = "translate" if translate_to_en else "transcribe"

            if language_choice == "Pure Hinglish / Roman Hindi":
                segments_gen, _ = model.transcribe("temp_input.mp4", word_timestamps=True, language="hi", initial_prompt="यह हिंदी में है।")
                convert_to_roman = True
            elif language_choice in lang_code_map:
                segments_gen, _ = model.transcribe("temp_input.mp4", word_timestamps=True, language=lang_code_map[language_choice], task=task_type)
            else:
                segments_gen, _ = model.transcribe("temp_input.mp4", word_timestamps=True, task=task_type)

            segments = list(segments_gen)
            full_text = " ".join([seg.text for seg in segments])

            # AI Auto Vibe or Manual Style decision
            if auto_vibe:
                vibe_info = classify_reel_vibe(full_text)
                st.success(f"🎯 AI Detected Video Genre: **{vibe_info['name']}**")
                effect_tag = f"{{\\c{active_color}" + vibe_info["tag"][1:]
                chosen_font = vibe_info["font"]
                chosen_layout = vibe_info["words"]
                outline_size = vibe_info["outline"]
                shadow_size = vibe_info["shadow"]
            else:
                chosen_font = font_family
                chosen_layout = words_per_line
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
Style: ReelStyle,{chosen_font},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,{outline_size},{shadow_size},2,20,20,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
            events = []
            if "1 Word" in chosen_layout:
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
            elif "2-3 Words" in chosen_layout:
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

            st.success("🎉 Video Generated Successfully!")
            st.video("output.mp4")
            with open("output.mp4", "rb") as file:
                st.download_button("📥 Download Final Reel", data=file, file_name="caption_vfx_reel.mp4", mime="video/mp4", use_container_width=True)
                
