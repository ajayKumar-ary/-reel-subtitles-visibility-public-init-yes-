import streamlit as st
import subprocess
import os
import re
import cv2
import numpy as np
import sqlite3
import hashlib
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from faster_whisper import WhisperModel
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# ==================== 1. PAGE SETUP & STYLING ====================
st.set_page_config(
    page_title="CaptionVFX AI Studio Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- SENDER EMAIL & APP PASSWORD -----------------
SMTP_SENDER_EMAIL = "tiwariajaykumar690@gmail.com"
SMTP_SENDER_PASSWORD = "zcnqpshuswnhztto"
# ---------------------------------------------------------------

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
        height: 3rem !important;
        border-radius: 8px !important;
    }
    .auth-container {
        max-width: 450px;
        margin: 1.5rem auto;
        padding: 2rem;
        background: rgba(15, 23, 42, 0.8);
        backdrop-filter: blur(16px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
        text-align: center;
    }
    .auth-title {
        font-size: 1.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #60a5fa, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .auth-sub { color: #94a3b8; font-size: 0.9rem; margin-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ==================== 2. EMAIL DATABASE & OTP ENGINE ====================
def get_db():
    return sqlite3.connect("users.db", check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email.strip()) is not None

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(email, password):
    email = email.strip().lower()
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, hash_pw(password)))
        conn.commit()
        return True, "Account verify ho gaya! Ab Sign In karein."
    except sqlite3.IntegrityError:
        return False, "Yeh Email pehle se registered hai."
    finally:
        conn.close()

def verify_user(email, password):
    email = email.strip().lower()
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE email = ?', (email,))
    row = c.fetchone()
    conn.close()
    return True if row and row[0] == hash_pw(password) else False

def send_otp_email(target_email, otp_code):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"CaptionVFX AI Studio <{SMTP_SENDER_EMAIL}>"
        msg['To'] = target_email
        msg['Subject'] = f"Your Verification OTP: {otp_code} - CaptionVFX Studio"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #0f172a; color: #ffffff; padding: 20px; border-radius: 10px;">
            <h2 style="color: #818cf8;">CaptionVFX AI Studio</h2>
            <p>Aapka one-time verification code (OTP) neeche diya gaya hai:</p>
            <div style="background: #1e293b; padding: 15px; border-radius: 8px; font-size: 28px; font-weight: bold; letter-spacing: 5px; color: #38bdf8; text-align: center; margin: 20px 0;">
                {otp_code}
            </div>
            <p style="color: #94a3b8; font-size: 13px;">Yeh OTP 10 minute ke liye valid hai. Kisi ke sath share na karein.</p>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SMTP_SENDER_EMAIL, SMTP_SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "OTP successfully bhej diya gaya hai! Inbox check karein."
    except Exception as e:
        return False, f"Email send failed: {str(e)}"

init_db()

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""
if "generated_otp" not in st.session_state:
    st.session_state["generated_otp"] = None
if "otp_target_email" not in st.session_state:
    st.session_state["otp_target_email"] = ""

# ==================== AUTHENTICATION & OTP PORTAL ====================
if not st.session_state["logged_in"]:
    col_l, col_center, col_r = st.columns([1, 1.4, 1])
    with col_center:
        st.markdown("""
        <div class="auth-container">
            <div class="auth-title">CaptionVFX AI Studio</div>
            <div class="auth-sub">Enter Email & Verify OTP to Access Video Studio</div>
        </div>
        """, unsafe_allow_html=True)

        auth_tab1, auth_tab2 = st.tabs(["🔑 Sign In", "📝 Create Account (OTP)"])
        
        # TAB 1: SIGN IN
        with auth_tab1:
            login_email = st.text_input("Email Address", placeholder="name@example.com", key="l_email")
            login_pass = st.text_input("Password", type="password", key="l_pass")
            if st.button("Sign In to Studio 🚀", use_container_width=True):
                if not is_valid_email(login_email):
                    st.error("Kripya valid email address format daalein.")
                elif verify_user(login_email, login_pass):
                    st.session_state["logged_in"] = True
                    st.session_state["user_email"] = login_email.strip().lower()
                    st.rerun()
                else:
                    st.error("Galat Email ya Password! Pehle Create Account tab me OTP verify karke account banayein.")

        # TAB 2: SIGN UP WITH OTP
        with auth_tab2:
            reg_email = st.text_input("Your Email Address", placeholder="name@example.com", key="r_email")
            
            if st.button("📩 Send 6-Digit OTP", use_container_width=True):
                if not is_valid_email(reg_email):
                    st.error("Kripya valid email enter karein.")
                else:
                    otp = str(random.randint(100000, 999999))
                    success, msg = send_otp_email(reg_email.strip().lower(), otp)
                    if success:
                        st.session_state["generated_otp"] = otp
                        st.session_state["otp_target_email"] = reg_email.strip().lower()
                        st.success(msg)
                    else:
                        st.error(msg)
            
            if st.session_state["generated_otp"]:
                st.info(f"📧 Verification OTP sent to: `{st.session_state['otp_target_email']}`")
                user_entered_otp = st.text_input("Enter 6-Digit OTP", max_chars=6, key="otp_input")
                reg_pass = st.text_input("Create Password", type="password", key="r_pass")
                
                if st.button("✅ Verify OTP & Create Account", use_container_width=True):
                    if user_entered_otp.strip() != st.session_state["generated_otp"]:
                        st.error("Galat OTP code! Email check karke sahi 6-digit OTP daalein.")
                    elif len(reg_pass) < 4:
                        st.warning("Password kam se kam 4 characters ka banayein.")
                    else:
                        success, reg_msg = register_user(st.session_state["otp_target_email"], reg_pass)
                        if success:
                            st.success(reg_msg)
                            st.session_state["generated_otp"] = None
                        else:
                            st.warning(reg_msg)
    st.stop()

# ==================== 3. AI SUBTITLE & VFX FUNCTIONS ====================
@st.cache_resource
def load_whisper_models():
    tiny = WhisperModel("tiny", device="cpu", compute_type="int8", cpu_threads=4)
    base = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=4)
    return tiny, base

tiny_model, base_model = load_whisper_models()

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
    cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
    success, frame = cap.read()
    if not success or frame is None:
        cap.set(cv2.CAP_PROP_POS_MSEC, 0)
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
        return "&H00FF5500&"  # Cyan Blue
    elif avg_g > avg_r and avg_g > avg_b:
        return "&H00D900FF&"  # Hot Pink
    elif avg_r > avg_g and avg_r > avg_b:
        return "&H0000FF00&"  # Neon Green
    else:
        return "&H0000FFFF&"  # Neon Yellow

def classify_reel_vibe(transcript_text):
    text_lower = transcript_text.lower()
    if any(w in text_lower for w in ["welcome", "hello", "today", "aaj", "dekho", "listen", "secret", "kaise", "stop", "wait"]):
        return {
            "name": "⚡ Intro / High-Energy Hook",
            "tag": r"{\t(0,70,\fscx130\fscy130)\t(70,140,\fscx100\fscy100)\shad6}",
            "font": "Impact", "words": "1 Word", "outline": 8, "shadow": 4
        }
    elif any(w in text_lower for w in ["vlog", "travel", "trip", "morning", "life", "friends", "khana", "market", "day"]):
        return {
            "name": "🎬 Travel & Daily Vlog",
            "tag": r"{\fad(140,80)}",
            "font": "Montserrat Black", "words": "2-3 Words", "outline": 6, "shadow": 2
        }
    elif any(w in text_lower for w in ["hardwork", "success", "mehnat", "gym", "money", "focus", "goal", "mindset", "power"]):
        return {
            "name": "🔥 Motivation & Fitness",
            "tag": r"{\blur6\t(0,60,\fscx120\fscy120)\t(60,120,\fscx100\fscy100)}",
            "font": "Arial Black", "words": "1 Word", "outline": 10, "shadow": 5
        }
    else:
        return {
            "name": "🎙️ Podcast & Storytelling",
            "tag": r"{\2c&H00FFFFFF&\k45}",
            "font": "Trebuchet MS", "words": "2-3 Words", "outline": 6, "shadow": 3
        }

def attach_smart_emoji(word):
    clean_w = re.sub(r'[^\w\s]', '', word.lower()).strip()
    emoji_dict = {
        "money": " 💰", "paisa": " 💰", "paise": " 💰", "cash": " 💵", "rich": " 🤑",
        "fire": " 🔥", "viral": " 🚀", "super": " ⚡", "energy": " ⚡", "power": " 💥",
        "gym": " 🏋️", "workout": " 💪", "hardwork": " 💪", "mehnat": " 🦾",
        "love": " ❤️", "pyar": " ❤️", "dil": " ❤️", "happy": " 😄", "khush": " 😊",
        "travel": " ✈️", "trip": " 🧳", "car": " 🚗", "gaadi": " 🚘", "bike": " 🏍️",
        "phone": " 📱", "mobile": " 📱", "video": " 🎬", "stop": " 🛑", "time": " ⏰"
    }
    return word + emoji_dict.get(clean_w, "")

# ==================== 4. SIDEBAR CONTROLS ====================
st.sidebar.markdown(f"📧 **Verified User:** `{st.session_state['user_email']}`")
if st.sidebar.button("🚪 Logout"):
    st.session_state["logged_in"] = False
    st.session_state["user_email"] = ""
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("## ⚙️ Studio Controls")

with st.sidebar.expander("⚡ Processing Speed Mode", expanded=True):
    perf_mode = st.radio("Select Engine Speed", ["🚀 Turbo Fast (5x Speed)", "🎯 Ultra Precision"])

with st.sidebar.expander("🤖 AI Motion & Emojis", expanded=True):
    auto_vibe = st.checkbox("AI Auto-Match Reel Type (Vlog/Intro/Podcast)", value=True)
    enable_emojis = st.checkbox("😍 Auto-Add Smart Emojis", value=True)

with st.sidebar.expander("🎨 Subtitle Styling & Presets", expanded=False):
    preset_style = st.selectbox(
        "✨ Animation Preset",
        ["🔥 Hormozi Pop-Bounce", "🎤 CapCut Karaoke Highlight", "⚡ Neon Cyberpunk Glow", "🧊 3D Deep Shadow Drop", "✨ Smooth Fade-In Up", "🎯 Clean Minimal"]
    )
    font_family = st.selectbox("🔤 Font Family", ["Arial Black", "Impact", "Montserrat Black", "Trebuchet MS", "Verdana"])
    words_per_line = st.radio("📝 Layout Flow", ["1 Word (Fast Reels)", "2-3 Words (Natural)", "Full Sentence"])
    font_size = st.slider("📏 Font Size", 40, 130, 80, step=5)
    position = st.selectbox("📍 Text Position", ["Center-Bottom", "Middle Center", "Lower Bottom", "Top Header"])

with st.sidebar.expander("🎯 Color Settings", expanded=False):
    highlight_color_choice = st.selectbox(
        "Highlight Color",
        ["🤖 Auto-Detect (Video AI Contrast)", "Neon Yellow", "Neon Green", "Cyan Blue", "Hot Pink", "Electric Orange", "Bright Red"]
    )

with st.sidebar.expander("🌐 Language & Translation", expanded=False):
    language_choice = st.selectbox(
        "Select Audio Language",
        ["Pure Hinglish / Roman Hindi", "Auto-Detect Language", "English", "Hindi (हिन्दी)", "Spanish (Español)", "French (Français)", "German (Deutsch)", "Russian (Русский)", "Arabic (العربية)", "Japanese (日本語)"]
    )
    translate_to_en = st.checkbox("🔄 Translate to English Words", value=False)
    all_uppercase = st.checkbox("🔠 Convert All to UPPERCASE", value=True)

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

# ==================== 5. MAIN WORKSPACE ====================
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
                active_color = detect_best_contrast_color("temp_input.mp4")
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
                elif "3D Deep Shadow" in 
