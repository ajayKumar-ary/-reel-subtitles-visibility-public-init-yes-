import streamlit as st
import os
import subprocess
import whisper
import gc
import re

# ----------------- PAGE CONFIG -----------------
st.set_page_config(
    page_title="CaptionVFX AI Studio Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- CUSTOM CSS -----------------
st.markdown("""
<style>
    .main { background-color: #0b0f19; color: #f8fafc; }
    .stButton>button {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
        font-weight: 700;
        font-size: 1.05rem;
        width: 100%;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(168, 85, 247, 0.5);
    }
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- HINGLISH TRANSLITERATION ENGINE -----------------
HINDI_TO_HINGLISH_MAP = {
    'नमस्कार': 'Namaskar', 'नमस्ते': 'Namaste', 'आप': 'Aap', 'कैसे': 'Kaise', 'हो': 'Ho',
    'मैं': 'Main', 'हूँ': 'Hoon', 'अच्छा': 'Achha', 'बहुत': 'Bahut', 'धन्यवाद': 'Dhanyawad',
    'क्या': 'Kya', 'कर': 'Kar', 'रहे': 'Rahe', 'रहा': 'Raha', 'रही': 'Rahi', 'है': 'Hai',
    'हैं': 'Hain', 'यह': 'Yeh', 'वह': 'Woh', 'कहाँ': 'Kahan', 'यहाँ': 'Yahan', 'वहाँ': 'Wahan',
    'कब': 'Kab', 'क्यों': 'Kyun', 'नहीं': 'Nahi', 'हाँ': 'Haan', 'दोस्त': 'Dost', 'भाई': 'Bhai',
    'पैसा': 'Paisa', 'काम': 'Kaam', 'समय': 'Samay', 'वीडियो': 'Video', 'लाइक': 'Like',
    'शेयर': 'Share', 'सब्सक्राइब': 'Subscribe', 'फॉलो': 'Follow', 'दिन': 'Din', 'रात': 'Raat',
    'जिंदगी': 'Zindagi', 'सफलता': 'Success', 'मेहनत': 'Mehnat', 'सोचो': 'Socho', 'देखो': 'Dekho'
}

def hindi_to_hinglish(text: str) -> str:
    # Character replacement mapping for Devanagari
    matras = {
        'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'ृ': 'ri',
        'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'n', '्': '', 'ः': 'h'
    }
    vowels = {
        'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
        'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au'
    }
    consonants = {
        'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
        'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
        'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
        'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
        'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
        'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh',
        'ष': 'sh', 'स': 's', 'ह': 'h', 'ड़': 'd', 'ढ़': 'dh', 'ज़': 'z', 'फ़': 'f'
    }

    words = text.split()
    converted_words = []
    for word in words:
        clean_w = re.sub(r'[^\w\s]', '', word)
        if clean_w in HINDI_TO_HINGLISH_MAP:
            converted_words.append(HINDI_TO_HINGLISH_MAP[clean_w])
            continue

        res = []
        i = 0
        w_len = len(word)
        while i < w_len:
            c = word[i]
            if c in vowels:
                res.append(vowels[c])
            elif c in consonants:
                base = consonants[c]
                if i + 1 < w_len and word[i+1] in matras:
                    res.append(base + matras[word[i+1]])
                    i += 1
                elif i + 1 < w_len and word[i+1] == '्':
                    res.append(base)
                    i += 1
                else:
                    res.append(base + 'a' if i != w_len - 1 else base)
            elif c in matras:
                res.append(matras[c])
            else:
                res.append(c)
            i += 1
        converted_words.append("".join(res).capitalize())
    return " ".join(converted_words)

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

# ----------------- ASS SUBTITLE BUILDER -----------------
def generate_ass_subtitles(segments, preset_style, font_size, primary_color, position, convert_hinglish):
    align_val = 2
    margin_v = 45
    if position == "Middle":
        align_val = 5
        margin_v = 0
    elif position == "Top":
        align_val = 8
        margin_v = 45

    colors_map = {
        "Yellow Highlight": "&H0000FFFF",
        "Neon Cyan": "&H00FFFF00",
        "Pure White": "&H00FFFFFF",
        "Vibrant Green": "&H0000FF00",
        "Hot Pink": "&H00B400FF"
    }
    pri_c = colors_map.get(primary_color, "&H0000FFFF")

    outline_val = 4 if "Hormozi" in preset_style or "Bold" in preset_style else 2.5
    shadow_val = 3 if "Neon" in preset_style or "Shadow" in preset_style else 0

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,{font_size},{pri_c},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{outline_val},{shadow_val},{align_val},20,20,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for seg in segments:
        text = seg['text'].strip()
        if not text:
            continue
        
        if convert_hinglish:
            text = hindi_to_hinglish(text)
        
        words = text.split()
        if len(words) > 3:
            mid = len(words) // 2
            chunk_duration = (seg['end'] - seg['start']) / 2
            mid_time = seg['start'] + chunk_duration
            
            t1 = " ".join(words[:mid])
            t2 = " ".join(words[mid:])
            
            events.append(f"Dialogue: 0,{format_timestamp_ass(seg['start'])},{format_timestamp_ass(mid_time)},Default,,0,0,0,,{{\\fad(70,70)}}{t1}")
            events.append(f"Dialogue: 0,{format_timestamp_ass(mid_time)},{format_timestamp_ass(seg['end'])},Default,,0,0,0,,{{\\fad(70,70)}}{t2}")
        else:
            events.append(f"Dialogue: 0,{format_timestamp_ass(seg['start'])},{format_timestamp_ass(seg['end'])},Default,,0,0,0,,{{\\fad(70,70)}}{text}")

    return ass_header + "\n".join(events)

# ----------------- UI WORKSPACE -----------------
st.title("🎬 CaptionVFX AI Studio Pro")
st.caption("AI Subtitles • Hinglish Auto-Convert • VFX Animations • 4K Visual Boost")

uploaded_file = st.file_uploader("📤 Upload Video (MP4/MOV)", type=["mp4", "mov"])

if uploaded_file:
    with open("temp_input.mp4", "wb") as f:
        f.write(uploaded_file.getbuffer())

    col_preview, col_settings = st.columns([1, 1.2])

    with col_preview:
        st.video("temp_input.mp4")
        st.markdown("""
        <div class="metric-card">
            🎯 <b>AI Detected Preset:</b> Viral Shorts & Reels<br>
            ⚡ <b>Audio Engine:</b> Whisper Neural AI
        </div>
        """, unsafe_allow_html=True)

    with col_settings:
        st.subheader("⚙️ Style & Animation Controls")
        
        c1, c2 = st.columns(2)
        with c1:
            lang_choice = st.selectbox("🌐 Audio Language", ["Auto Detect", "Hindi (हिन्दी)", "English", "Hinglish Mode"])
            preset_style = st.selectbox("✨ Subtitle VFX Style", ["Hormozi Viral Pop", "Neon Glow & Shadow", "Clean Minimalist", "Classic Bold"])
            primary_color = st.selectbox("🎯 Highlight Color", ["Yellow Highlight", "Neon Cyan", "Pure White", "Vibrant Green", "Hot Pink"])
        
        with c2:
            position = st.selectbox("📍 Subtitle Position", ["Bottom", "Middle", "Top"])
            font_size = st.slider("🔤 Font Size", 20, 56, 36)
            whisper_model = st.selectbox("⚡ AI Processing Speed", ["tiny (Super Fast)", "base (Balanced)", "small (Ultra Accurate)"])

        st.markdown("---")
        st.subheader("🚀 Video Enhancements")
        e1, e2 = st.columns(2)
        with e1:
            enable_enhancer = st.checkbox("✨ 4K Clarity & Color Boost", value=True)
            convert_hinglish = st.checkbox("🔤 Convert Hindi to Hinglish (Aap Kaise Ho)", value=True if "Hinglish" in lang_choice else False)
        with e2:
            slowmo_option = st.selectbox("⏱️ Speed / Slow-Motion", ["Normal Speed (1.0x)", "Smooth Slow-Mo (0.75x)", "Dramatic Slow-Mo (0.5x)"])

    if st.button("🚀 Render Subtitled Video", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 1. Extract Audio
        status_text.text("🎙️ Extracting Audio...")
        progress_bar.progress(20)
        cmd_extract = "ffmpeg -y -i temp_input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 temp_audio.wav"
        subprocess.run(cmd_extract, shell=True, capture_output=True)

        # 2. Whisper AI Transcription
        status_text.text("🤖 Transcribing Voice with AI...")
        progress_bar.progress(45)
        model_name = whisper_model.split()[0]
        model = whisper.load_model(model_name)
        
        transcribe_args = {"fp16": False}
        if "Hindi" in lang_choice or "Hinglish" in lang_choice:
            transcribe_args["language"] = "hi"
        elif "English" in lang_choice:
            transcribe_args["language"] = "en"
            
        transcription = model.transcribe("temp_audio.wav", **transcribe_args)

        # 3. Create ASS Subtitles
        status_text.text("🎨 Styling Subtitle Animations...")
        progress_bar.progress(65)
        ass_content = generate_ass_subtitles(
            transcription["segments"],
            preset_style,
            font_size,
            primary_color,
            position,
            convert_hinglish
        )
        with open("subtitles.ass", "w", encoding="utf-8") as f:
            f.write(ass_content)

        # 4. FFmpeg Video Merge
        status_text.text("⚡ Final Video Rendering with VFX...")
        progress_bar.progress(85)
        
        vf_filters = []
        af_filters = []

        if "0.75x" in slowmo_option:
            vf_filters.append("setpts=1.333*PTS")
            af_filters.append("atempo=0.75")
        elif "0.5x" in slowmo_option:
            vf_filters.append("setpts=2.0*PTS")
            af_filters.append("atempo=0.5")

        if enable_enhancer:
            vf_filters.append("unsharp=5:5:0.8:5:5:0.0,eq=contrast=1.08:saturation=1.15")

        vf_filters.append("ass=subtitles.ass")
        
        vf_str = ",".join(vf_filters)
        af_str = f'-af "{",".join(af_filters)}"' if af_filters else "-c:a copy"

        cmd_render = f'ffmpeg -y -i temp_input.mp4 -vf "{vf_str}" {af_str} -c:v libx264 -preset ultrafast -pix_fmt yuv420p output.mp4'
        subprocess.run(cmd_render, shell=True, capture_output=True)

        progress_bar.progress(100)
        status_text.empty()

        # 5. Output Video Display & Download Button
        if os.path.exists("output.mp4") and os.path.getsize("output.mp4") > 1000:
            st.success("✅ Reel Successfully Rendered with Effects!")
            with open("output.mp4", "rb") as vid_file:
                video_bytes = vid_file.read()
                st.video(video_bytes)
                st.download_button(
                    label="📥 Download Subtitled Reel (MP4)",
                    data=video_bytes,
                    file_name="viral_caption_reel.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )
        else:
            st.error("Rendering issue detected. Please check your video format.")

        cleanup_files(["temp_input.mp4", "temp_audio.wav", "subtitles.ass", "output.mp4"])
        gc.collect()
            
