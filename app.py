import streamlit as st
import subprocess
import os
import sqlite3
import hashlib
from faster_whisper import WhisperModel
import vfx_engine as fx

st.set_page_config(
    page_title="CaptionVFX AI Studio Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== DATABASE AUTH SYSTEM ====================
def get_db():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL)')
    conn.commit()
    conn.close()

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hash_pw(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    return True if row and row[0] == hash_pw(password) else False

init_db()

# Session State
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# ==================== MODERN UI STYLING & BACKGROUND ====================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(rgba(15, 23, 42, 0.88), rgba(15, 23, 42, 0.88)), 
                    url("https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.95) !important;
        backdrop-filter: blur(12px);
    }
    .main-title {
        text-align: center;
        padding: 0.8rem;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        border-radius: 10px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .main-title h2 { color: white !important; margin: 0; font-weight: 700; }
    .main-title p { margin: 0.2rem 0 0 0; color: #e0e7ff; font-size: 0.95rem; }
    .stButton button {
        background: linear-gradient(90deg, #4f46e5, #7c3aed) !important;
        color: white !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================== LOGIN / SIGN-UP GATE ====================
if not st.session_state["logged_in"]:
    st.markdown("<div class='main-title'><h2>🔐 CaptionVFX AI • Access Portal</h2><p>Login or create an account to start editing</p></div>", unsafe_allow_html=True)
    
    col_l, col_center, col_r = st.columns([1, 1.8, 1])
    with col_center:
        auth_tab1, auth_tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
        
        with auth_tab1:
            login_u = st.text_input("Username", key="l_user")
            login_p = st.text_input("Password", type="password", key="l_pass")
            if st.button("Login 🚀", use_container_width=True):
                if verify_user(login_u, login_p):
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = login_u
                    st.rerun()
                else:
                    st.error("Invalid Username or Password!")

        with auth_tab2:
            reg_u = st.text_input("Create Username", key="r_user")
            reg_p = st.text_input("Create Password", type="password", key="r_pass")
            if st.button("Sign Up ✨", use_container_width=True):
                if reg_u and reg_p:
                    if register_user(reg_u, reg_p):
                        st.success("Account created successfully! Ab Login tab me jakar login karein.")
                    else:
                        st.warning("Username already exists.")
                else:
                    st.warning("Please fill both fields.")
    st.stop()

# ==================== AI MODEL LOADER ====================
@st.cache_resource
def load_whisper_models():
    tiny = WhisperModel("tiny", device="cpu", compute_type="int8", cpu_threads=4)
    base = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=4)
    return tiny, base

tiny_model, base_model = load_whisper_models()

# ==================== LOGGED IN SIDEBAR CONTROLS ====================
st.sidebar.markdown(f"👤 **Account:** `{st.session_state['username']}`")
if st.sidebar.button("🚪 Logout"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("## ⚙️ Studio Controls")

# 1. Speed Engine
with st.sidebar.expander("⚡ Processing Speed Mode", expanded=True):
    perf_mode = st.radio("Select Engine Speed", ["🚀 Turbo Fast (5x Speed)", "🎯 Ultra Precision"])

# 2. AI Auto Motion & Emojis
with st.sidebar.expander("🤖 AI Motion & Emojis", expanded=True):
    auto_vibe = st.checkbox("AI Auto-Match Reel Type (Vlog/Intro/Podcast)", value=True)
    enable_emojis = st.checkbox("😍 Auto-Add Smart Emojis", value=True)

# 3. Manual Style & VFX
with st.sidebar.expander("🎨 Subtitle Styling & Presets", expanded=False):
    preset_style = st.selectbox(
        "✨ Animation Preset",
        ["🔥 Hormozi Pop-Bounce", "🎤 CapCut Karaoke Highlight", "⚡ Neon Cyberpunk Glow", "🧊 3D Deep Shadow Drop", "✨ Smooth Fade-In Up", "🎯 Clean Minimal"]
    )
    font_family = st.selectbox("🔤 Font Family", ["Arial Black", "Impact", "Montserrat Black", "Trebuchet MS", "Verdana"])
    words_per_line = st.radio("📝 Layout Flow", ["1 Word (Fast Reels)", "2-3 Words (Natural)", "Full Sentence"])
    font_size = st.slider("📏 Font Size", 40, 130, 80, step=5)
    position = st.selectbox("📍 Text Position", ["Center-Bottom", "Middle Center", "Lower Bottom", "Top Header"])

# 4. Highlight Color
with st.sidebar.expander("🎯 Color Settings", expanded=False):
    highlight_color_choice = st.selectbox(
        "Highlight Color",
        ["🤖 Auto-Detect (Video AI Contrast)", "Neon Yellow", "Neon Green", "Cyan Blue", "Hot Pink", "Electric Orange", "Bright Red"]
    )

# 5. Language Engine
with st.sidebar.expander("🌐 Language & Translation", expanded=False):
    language_choice = st.selectbox(
        "Select Audio Language",
        ["Pure Hinglish / Roman Hindi", "Auto-Detect Language", "English", "Hindi (हिन्दी)", "Spanish (Español)", "French (Français)", "German (Deutsch)", "Russian (Русский)", "Arabic (العربية)", "Japanese (日本語)"]
    )
    translate_to_en = st.checkbox("🔄 Translate to English Words", value=False)
    all_uppercase = st.checkbox("🔠 Convert All to UPPERCASE", value=True)

# 6. Slow Motion & 4K Enhancer
with st.sidebar.expander("⏱️ Slow-Mo & 4K Clarity", expanded=False):
    enable_slowmo = st.checkbox("Enable Slow Motion", value=False)
    speed_rate = "0.5x (Smooth Half Speed)"
    if enable_slowmo:
        speed_rate = st.selectbox("Speed Factor", ["0.75x (Cinematic Slow)", "0.5x (Smooth Half Speed)", "0.25x (Super Slow-Mo)"])
    
    st.markdown("---")
    enable_enhancer = st.checkbox("Enable 4K Clarity Boost", value=False)
    sharpness_level = "High Sharpness"
    if enable_enhancer:
        sharpness_level = st.select_slider("Sharpness Level", options=["Subtle Clear", "High Sharpness", "Ultra 4K Feel"], value="High Sharpness")

# ==================== MAIN WORKSPACE ====================
st.markdown("""
<div class="main-title">
    <h2>🎬 CaptionVFX AI Studio Pro</h2>
    <p>Ultra-Fast 5x Engine • Auto-Genre Motion • CapCut VFX • Hinglish • Emojis</p>
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
        st.info("💡 Side panel se AI Auto-Motion, Language, Speed ya Emojis customize karein.")
        render_clicked = st.button("🚀 Render Subtitled Video", use_container_width=True)

    if render_clicked:
        with st.spinner("⚡ AI processing subtitles & rendering video..."):
            with open("temp_input.mp4", "wb") as f:
                f.write(uploaded_file.read())

            # Fast Audio Extraction
            subprocess.run(
                "ffmpeg -y -i temp_input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 temp_audio.wav",
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            active_whisper = tiny_model if "Turbo Fast" in perf_mode else base_model

            color_map = {
                "Neon Yellow": "&H0000FFFF&", "Neon Green": "&H0000FF00&",
                "Cyan Blue": "&H00FFFF00&", "Hot Pink": "&H00D900FF&",
                "Electric Orange": "&H000088FF&", "Bright Red": "&H000000FF&"
            }

            if "Auto-Detect" in highlight_color_choice:
                active_color = fx.detect_best_contrast_color("temp_input.mp4")
            else:
                active_color = color_map.get(highlight_color_choice, "&H0000FFFF&")

            pos_map = {"Center-Bottom": 450, "Middle Center": 900, "Lower Bottom": 220, "Top Header": 1600}
            margin_v = pos_map.get(position, 450)

            lang_code_map = {
                "English": "en", "Hindi (हिन्दी)": "hi", "Spanish (Español)": "es",
                "French (Français)": "fr", "German (Deutsch)": "de", "Russian (Русский)": "ru",
                "Arabic (العربية)": "ar", "Japanese (日本語)": "ja"
            }

            convert_to_roman = False
            task_type = "translate" if translate_to_en else "transcribe"

            if language_choice == "Pure Hinglish / Roman Hindi":
                segments_gen, _ = active_whisper.transcribe("temp_audio.wav", word_timestamps=True, language="hi", initial_prompt="यह हिंदी में है।")
                convert_to_roman = True
            elif language_choice in lang_code_map:
                segments_gen, _ = active_whisper.transcribe("temp_audio.wav", word_timestamps=True, language=lang_code_map[language_choice], task=task_type)
            else:
                segments_gen, _ = active_whisper.transcribe("temp_audio.wav", word_timestamps=True, task=task_type)

            segments = list(segments_gen)
            full_text = " ".join([seg.text for seg in segments])

            if auto_vibe:
                vibe_info = fx.classify_reel_vibe(full_text)
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
                if "0.75x" in speed_rate: speed_factor = 1.0 / 0.75
                elif "0.5x" in speed_rate: speed_factor = 2.0
                elif "0.25x" in speed_rate: speed_factor = 4.0

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
                        start = fx.format_ass_time(word.start * speed_factor)
                        end = fx.format_ass_time(word.end * speed_factor)
                        raw_w = word.word.strip()
                        if enable_emojis: raw_w = fx.attach_smart_emoji(raw_w)
                        text = fx.clean_to_roman_text(raw_w) if convert_to_roman else raw_w
                        if all_uppercase: text = text.upper()
                        if text: events.append(f"Dialogue: 0,{start},{end},ReelStyle,,0,0,0,,{effect_tag}{text}")
            elif "2-3 Words" in chosen_layout:
                for segment in segments:
                    words = segment.words
                    chunk_size = 3
                    for i in range(0, len(words), chunk_size):
                        chunk = words[i:i + chunk_size]
                        if not chunk: continue
                        start = fx.format_ass_time(chunk[0].start * speed_factor)
                        end = fx.format_ass_time(chunk[-1].end * speed_factor)
                        parts = []
                        for w in chunk:
                            raw_w = w.word.strip()
                            if enable_emojis: raw_w = fx.attach_smart_emoji(raw_w)
                            cleaned_w = fx.clean_to_roman_text(raw_w) if convert_to_roman else raw_w
                            parts.append(cleaned_w)
                        text = " ".join(parts)
                        if all_uppercase: text = text.upper()
                        if text: events.append(f"Dialogue: 0,{start},{end},ReelStyle,,0,0,0,,{effect_tag}{text}")
            else:
                for segment in segments:
                    start = fx.format_ass_time(segment.start * speed_factor)
                    end = fx.format_ass_time(segment.end * speed_factor)
                    raw_seg_words = segment.text.strip().split()
                    if enable_emojis: raw_seg_words = [fx.attach_smart_emoji(w) for w in raw_seg_words]
                    raw_seg = " ".join(raw_seg_words)
                    text = fx.clean_to_roman_text(raw_seg) if convert_to_roman else raw_seg
                    if all_uppercase: text = text.upper()
                    if text: events.append(f"Dialogue: 0,{start},{end},ReelStyle,,0,0,0,,{effect_tag}{text}")

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

            cmd = f'ffmpeg -y -i temp_input.mp4 -vf "{vf_str}" {af_str} -c:v libx264 -pix_fmt yuv420p -preset ultrafast -threads 4 output.mp4'
            subprocess.run(cmd, shell=True)

            st.success("⚡ Video Rendered Successfully!")
            st.video("output.mp4")
            with open("output.mp4", "rb") as file:
                st.download_button("📥 Download Final Reel", data=file, file_name="caption_vfx_reel.mp4", mime="video/mp4", use_container_width=True)
        
