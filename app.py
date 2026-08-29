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

st.set_page_config(
    page_title="CaptionVFX AI Studio",
    page_icon="🎬",
    layout="wide"
)

SMTP_SENDER_EMAIL = "tiwariajaykumar690@gmail.com"
SMTP_SENDER_PASSWORD = "zcnqpshuswnhztto"

# ==================== THREAD-SAFE DATABASE ====================
DB_FILE = "users_v2.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def register_user(email, pw):
    email = email.strip().lower()
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hash_pw(pw)))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def verify_user(email, pw):
    email = email.strip().lower()
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE email = ?", (email,))
        row = c.fetchone()
        conn.close()
        if row and row[0] == hash_pw(pw):
            return True
        return False
    except Exception:
        return False

def send_otp(target, code):
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_SENDER_EMAIL
        msg["To"] = target
        msg["Subject"] = "Your Verification OTP: " + str(code)
        body = "Your CaptionVFX OTP code is: " + str(code)
        msg.attach(MIMEText(body, "plain"))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SMTP_SENDER_EMAIL, SMTP_SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception:
        return False

# ==================== SESSION STATE ====================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""
if "otp_code" not in st.session_state:
    st.session_state["otp_code"] = None
if "otp_target" not in st.session_state:
    st.session_state["otp_target"] = ""

# ==================== AUTH SCREEN ====================
if not st.session_state["logged_in"]:
    st.markdown("<h2 style='text-align: center;'>🎬 CaptionVFX Studio Login</h2>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔑 Sign In", "📝 Create Account (OTP)"])
    
    with t1:
        l_email = st.text_input("Email", key="l_em")
        l_pass = st.text_input("Password", type="password", key="l_pw")
        if st.button("Login 🚀", use_container_width=True):
            if verify_user(l_email, l_pass):
                st.session_state["logged_in"] = True
                st.session_state["user_email"] = l_email.strip().lower()
                st.rerun()
            else:
                st.error("Invalid Email or Password!")

    with t2:
        r_email = st.text_input("Your Email", key="r_em")
        if st.button("📩 Send OTP", use_container_width=True):
            if "@" in r_email and "." in r_email:
                gen_code = str(random.randint(100000, 999999))
                if send_otp(r_email.strip().lower(), gen_code):
                    st.session_state["otp_code"] = gen_code
                    st.session_state["otp_target"] = r_email.strip().lower()
                    st.success("OTP sent to your email! Inbox check karein.")
                else:
                    st.error("Email send failed. Make sure your email is correct.")
            else:
                st.warning("Enter a valid email address.")

        if st.session_state["otp_code"]:
            user_otp = st.text_input("Enter 6-Digit OTP", key="in_otp")
            r_pass = st.text_input("Create Password", type="password", key="in_pw")
            if st.button("✅ Verify & Register", use_container_width=True):
                if user_otp.strip() == st.session_state["otp_code"]:
                    if register_user(st.session_state["otp_target"], r_pass):
                        st.success("Account created successfully! Ab Sign In tab me jakar login karein.")
                        st.session_state["otp_code"] = None
                    else:
                        st.warning("Email already registered.")
                else:
                    st.error("Incorrect OTP!")
    st.stop()

# ==================== MAIN STUDIO APP ====================
@st.cache_resource
def load_whisper():
    return WhisperModel("tiny", device="cpu", compute_type="int8", cpu_threads=4)

whisper_model = load_whisper()

def format_ass_time(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int((sec - int(sec)) * 100)
    return "{:d}:{:02d}:{:02d}.{:02d}".format(h, m, s, cs)

def clean_to_roman(text):
    if re.search(r'[\u0900-\u097F]', text):
        text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    text = re.sub(r'[\u0600-\u06FF\u0750-\u077F]', '', text)
    return text.strip()

def attach_emoji(word):
    clean_w = re.sub(r'[^\w\s]', '', word.lower()).strip()
    emojis = {
        "money": " 💰", "paisa": " 💰", "paise": " 💰", "cash": " 💵", "rich": " 🤑",
        "fire": " 🔥", "viral": " 🚀", "super": " ⚡", "energy": " ⚡", "power": " 💥",
        "gym": " 🏋️", "workout": " 💪", "hardwork": " 💪", "mehnat": " 🦾",
        "love": " ❤️", "pyar": " ❤️", "dil": " ❤️", "happy": " 😄", "khush": " 😊",
        "travel": " ✈️", "trip": " 🧳", "car": " 🚗", "gaadi": " 🚘", "bike": " 🏍️"
    }
    return word + emojis.get(clean_w, "")

# Sidebar
st.sidebar.markdown("📧 **User:** " + st.session_state['user_email'])
if st.sidebar.button("Logout"):
    st.session_state["logged_in"] = False
    st.session_state["user_email"] = ""
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Video Settings")
words_layout = st.sidebar.radio("Words Layout", ["1 Word", "2-3 Words", "Full Sentence"])
language_choice = st.sidebar.selectbox("Language", ["Pure Hinglish / Roman Hindi", "Auto-Detect", "English", "Hindi"])
enable_emojis = st.sidebar.checkbox("Auto Smart Emojis", value=True)
all_uppercase = st.sidebar.checkbox("Convert UPPERCASE", value=True)

# Main Workspace
st.title("🎬 CaptionVFX AI Studio Pro")
uploaded_file = st.file_uploader("Upload MP4 / MOV Video", type=["mp4", "mov"])

if uploaded_file:
    col1, col2 = st.columns(2)
    with col1:
        st.video(uploaded_file)
    with col2:
        if st.button("🚀 Render Subtitled Video", type="primary", use_container_width=True):
            with st.spinner("AI Generating Captions & Rendering..."):
                with open("temp_input.mp4", "wb") as f:
                    f.write(uploaded_file.read())

                subprocess.run("ffmpeg -y -i temp_input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 temp_audio.wav", shell=True)

                convert_to_roman = False
                if language_choice == "Pure Hinglish / Roman Hindi":
                    segs_gen, _ = whisper_model.transcribe("temp_audio.wav", word_timestamps=True, language="hi")
                    convert_to_roman = True
                elif language_choice == "English":
                    segs_gen, _ = whisper_model.transcribe("temp_audio.wav", word_timestamps=True, language="en")
                elif language_choice == "Hindi":
                    segs_gen, _ = whisper_model.transcribe("temp_audio.wav", word_timestamps=True, language="hi")
                else:
                    segs_gen, _ = whisper_model.transcribe("temp_audio.wav", word_timestamps=True)

                segments = list(segs_gen)

                ass_header = "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: ReelStyle,Arial Black,80,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,8,4,2,20,20,450,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                
                events = []
                if "1 Word" in words_layout:
                    for s in segments:
                        for w in s.words:
                            st_time = format_ass_time(w.start)
                            en_time = format_ass_time(w.end)
                            raw_txt = w.word.strip()
                            if enable_emojis:
                                raw_txt = attach_emoji(raw_txt)
                            txt = clean_to_roman(raw_txt) if convert_to_roman else raw_txt
                            if all_uppercase:
                                txt = txt.upper()
                            if txt:
                                events.append("Dialogue: 0," + st_time + "," + en_time + ",ReelStyle,,0,0,0,," + txt)
                elif "2-3 Words" in words_layout:
                    for s in segments:
                        wds = s.words
                        for i in range(0, len(wds), 3):
                            chk = wds[i:i + 3]
                            if not chk:
                                continue
                            st_time = format_ass_time(chk[0].start)
                            en_time = format_ass_time(chk[-1].end)
                            parts = []
                            for w in chk:
                                raw_w = w.word.strip()
                                if enable_emojis:
                                    raw_w = attach_emoji(raw_w)
                                cl_w = clean_to_roman(raw_w) if convert_to_roman else raw_w
                                parts.append(cl_w)
                            txt = " ".join(parts)
                            if all_uppercase:
                                txt = txt.upper()
                            if txt:
                                events.append("Dialogue: 0," + st_time + "," + en_time + ",ReelStyle,,0,0,0,," + txt)
                else:
                    for s in segments:
                        st_time = format_ass_time(s.start)
                        en_time = format_ass_time(s.end)
                        txt = clean_to_roman(s.text.strip()) if convert_to_roman else s.text.strip()
                        if all_uppercase:
                            txt = txt.upper()
                        if txt:
                            events.append("Dialogue: 0," + st_time + "," + en_time + ",ReelStyle,,0,0,0,," + txt)

                with open("subtitles.ass", "w", encoding="utf-8") as f:
                    f.write(ass_header + "\n".join(events))

                cmd = 'ffmpeg -y -i temp_input.mp4 -vf "ass=subtitles.ass" -c:a aac -c:v libx264 -pix_fmt yuv420p -preset ultrafast -threads 4 output.mp4'
                subprocess.run(cmd, shell=True)

                st.success("🎉 Video Ready!")
                st.video("output.mp4")
                with open("output.mp4", "rb") as file:
                    st.download_button("📥 Download Final Video", data=file, file_name="captioned_reel.mp4", mime="video/mp4", use_container_width=True)
                        
