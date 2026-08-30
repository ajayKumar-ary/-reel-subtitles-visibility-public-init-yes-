import streamlit as st
import os
import subprocess
import requests
import json
import gc
import re
import imageio_ffmpeg
import speech_recognition as sr
from PIL import Image, ImageDraw, ImageFont

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

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

# ----------------- BULLETPROOF LOCAL FONT LOADER -----------------
def get_font_handle(size_px):
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for p in font_candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size_px)
            except Exception:
                pass
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size_px)
    except Exception:
        return ImageFont.load_default()

# ----------------- ACCURATE HINGLISH TRANSLITERATOR -----------------
def devanagari_to_hinglish(text: str) -> str:
    matras = {
        'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'ृ': 'ri',
        'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'n', '्': '', 'ः': 'h',
        'ँ': 'n', '़': ''
    }
    vowels = {
        'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
        'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au'
    }
    consonants = {
        'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
        'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
        'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
        'त': 't', 'थ': 'th', 'द': 'd', 'dh': 'dh', 'न': 'n',
        'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
        'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh',
        'ष': 'sh', 'स': 's', 'ह': 'h', 'ड़': 'd', 'ढ़': 'dh',
        'ज़': 'z', 'फ़': 'f', 'ग़': 'g', 'ख़': 'kh', 'क़': 'q'
    }

    words = text.split()
    output_words = []
    
    for word in words:
        if not re.search(r'[\u0900-\u097F]', word):
            output_words.append(word.upper())
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
        
        word_hinglish = "".join(res).upper()
        word_hinglish = re.sub(r'AA$', 'A', word_hinglish)
        output_words.append(word_hinglish if word_hinglish else word)

    return " ".join(output_words)

# ----------------- BIG AESTHETIC OVERLAY ENGINE -----------------
def create_subtitle_overlays(segments, position, color_name, font_scale_val, vw, vh, out_dir):
    color_dict = {
        "Hormozi Yellow": (255, 230, 0),
        "Neon Cyan": (0, 245, 255),
        "Pure White": (255, 255, 255),
        "Emerald Green": (0, 255, 128),
        "Hot Pink": (255, 20, 147)
    }
    fill_col = color_dict.get(color_name, (255, 230, 0))
    os.makedirs(out_dir, exist_ok=True)

    # Calculate actual font size: font_scale_val (e.g. 100 = 10% video width)
    actual_font_size = max(40, int(vw * (font_scale_val / 1000.0)))
    font = get_font_handle(actual_font_size)

    overlay_files = []
    for idx, seg in enumerate(segments):
        img = Image.new("RGBA", (vw, vh), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        text = seg['text'].strip().upper()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # Centered X position
        x = (vw - text_w) // 2
        
        # Position mapping
        if position == "Top":
            y = int(vh * 0.16)
        elif position == "Middle":
            y = (vh - text_h) // 2
        else:
            y = int(vh * 0.74)  # Perfect aesthetic lower area

        # Viral thick black outline
        stroke_val = max(5, int(actual_font_size * 0.14))
        
        # Shadow glow
        s_off = max(3, int(actual_font_size * 0.06))
        draw.text((x + s_off, y + s_off), text, font=font, fill=(0, 0, 0, 220), stroke_width=stroke_val, stroke_fill=(0, 0, 0, 220))
        
        # Crisp Main Text
        draw.text((x, y), text, font=font, fill=fill_col, stroke_width=stroke_val, stroke_fill=(0, 0, 0, 255))

        filename = os.path.join(out_dir, f"sub_{idx}.png")
        img.save(filename, "PNG")
        overlay_files.append((filename, seg['start'], seg['end']))
        
    return overlay_files

# ----------------- UI WORKSPACE -----------------
st.title("🎬 CaptionVFX AI Studio Pro")
st.caption("Bold Viral Subtitles • CapCut & Hormozi Aesthetic • Dynamic Scaling")

uploaded_file = st.file_uploader("📤 Upload Video (MP4/MOV)", type=["mp4", "mov"])

if uploaded_file:
    work_dir = "/tmp/caption_job"
    os.makedirs(work_dir, exist_ok=True)

    input_path = os.path.join(work_dir, "input.mp4")
    audio_path = os.path.join(work_dir, "audio.wav")
    output_path = os.path.join(work_dir, "output.mp4")
    overlays_dir = os.path.join(work_dir, "overlays")

    with open(input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Get Duration & Dimensions
    video_duration = 10.0
    vw, vh = 1080, 1920
    try:
        dur_cmd = f'"{FFMPEG_EXE}" -i "{input_path}" 2>&1'
        dur_proc = subprocess.run(dur_cmd, shell=True, capture_output=True, text=True)
        out_str = dur_proc.stdout + dur_proc.stderr

        match_dur = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)', out_str)
        if match_dur:
            video_duration = int(match_dur.group(1))*3600 + int(match_dur.group(2))*60 + float(match_dur.group(3))

        match_res = re.search(r'Stream.*Video:.*,\s*(\d+)x(\d+)', out_str)
        if match_res:
            vw = int(match_res.group(1))
            vh = int(match_res.group(2))
    except:
        pass

    col_preview, col_settings = st.columns([1, 1.2])

    with col_preview:
        st.video(input_path)
        st.markdown(f"""
        <div class="metric-card">
            ⚡ <b>Resolution:</b> {vw}x{vh} Native<br>
            ⏱️ <b>Duration:</b> {video_duration:.1f}s | Auto Speech Sync
        </div>
        """, unsafe_allow_html=True)

    with col_settings:
        st.subheader("⚙️ Style & Subtitle Controls")
        
        c1, c2 = st.columns(2)
        with c1:
            lang_mode = st.selectbox(
                "🌐 Subtitle Output Language",
                [
                    "Hinglish (Aap Kaise Ho)",
                    "Pure Hindi (आप कैसे हैं)",
                    "English"
                ]
            )
            primary_color = st.selectbox("🎯 Highlight Color", ["Hormozi Yellow", "Neon Cyan", "Pure White", "Emerald Green", "Hot Pink"])
        
        with c2:
            position = st.selectbox("📍 Subtitle Position", ["Bottom", "Middle", "Top"])
            font_scale = st.slider("🔤 Subtitle Size (Bada / Chota)", 60, 180, 120)

        custom_override = st.text_input("✍️ Manual Subtitle Override (Optional)", placeholder="Khaali chhoden agar auto audio detect chahiye")

    if st.button("🚀 Render Subtitled Video", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 1. Audio Extraction
        status_text.text("🎙️ Extracting Audio...")
        progress_bar.progress(25)
        cmd_extract = f'"{FFMPEG_EXE}" -y -i "{input_path}" -vn -acodec pcm_s16le -ar 16000 -ac 1 "{audio_path}"'
        subprocess.run(cmd_extract, shell=True, capture_output=True)

        # 2. Voice AI Transcription
        status_text.text("🤖 Transcribing Spoken Audio...")
        progress_bar.progress(50)
        
        recognized_text = custom_override.strip()
        if not recognized_text:
            r = sr.Recognizer()
            try:
                with sr.AudioFile(audio_path) as src:
                    audio_data = r.record(src)
                    target_lang = "en-US" if "English" in lang_mode else "hi-IN"
                    recognized_text = r.recognize_google(audio_data, language=target_lang)
            except Exception:
                recognized_text = ""

        # Divide into punchy 2-word chunks
        segments = []
        if recognized_text:
            words = recognized_text.split()
            chunk_size = 2
            word_chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
            time_per_chunk = float(video_duration) / max(1, len(word_chunks))
            
            for idx, chunk in enumerate(word_chunks):
                raw_s = " ".join(chunk)
                if "Hinglish" in lang_mode:
                    display_s = devanagari_to_hinglish(raw_s)
                elif "Pure Hindi" in lang_mode:
                    display_s = raw_s
                else:
                    display_s = raw_s.upper()

                segments.append({
                    'start': idx * time_per_chunk,
                    'end': min(video_duration, (idx + 1) * time_per_chunk),
                    'text': display_s
                })

        if not segments:
            segments = [
                {'start': 0.0, 'end': video_duration/2, 'text': 'HELLO DOSTO'},
                {'start': video_duration/2, 'end': video_duration, 'text': 'VIRAL REEL'}
            ]

        # 3. Clean HD Large Overlays
        status_text.text("🎨 Generating Large Aesthetic Captions...")
        progress_bar.progress(70)
        overlays = create_subtitle_overlays(segments, position, primary_color, font_scale, vw, vh, overlays_dir)

        # 4. Multi-Overlay Filter Burn
        status_text.text("⚡ Merging Subtitles...")
        progress_bar.progress(85)
        
        input_args = [f'-i "{input_path}"']
        filter_chains = []
        last_v = "0:v"

        for i, (ov_file, st_t, en_t) in enumerate(overlays, 1):
            input_args.append(f'-i "{ov_file}"')
            next_v = f"v{i}"
            filter_chains.append(f"[{last_v}][{i}:v]overlay=0:0:enable='between(t,{st_t:.2f},{en_t:.2f})'[{next_v}]")
            last_v = next_v

        filter_complex_str = ";".join(filter_chains)
        input_args_str = " ".join(input_args)

        cmd_render = f'"{FFMPEG_EXE}" -y {input_args_str} -filter_complex "{filter_complex_str}" -map "[{last_v}]" -map 0:a? -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac "{output_path}"'
        subprocess.run(cmd_render, shell=True, capture_output=True)

        progress_bar.progress(100)
        status_text.empty()

        # 5. Output Video Display & Download
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            st.success("✅ Viral Subtitled Reel Ready!")
            with open(output_path, "rb") as vid_file:
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
            st.error("Render issue. Please try again.")

        gc.collect()
    
