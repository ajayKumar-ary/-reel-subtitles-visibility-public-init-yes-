import streamlit as st
import os
import subprocess
import requests
import json
import gc
import re
import io
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

# ----------------- HIGH-QUALITY FONT FETCHER -----------------
@st.cache_resource
def load_hd_font_bytes():
    urls = [
        "https://cdn.jsdelivr.net/gh/google/fonts/ofl/montserrat/Montserrat-Black.ttf",
        "https://cdn.jsdelivr.net/gh/google/fonts/apache/roboto/Roboto-Black.ttf"
    ]
    for url in urls:
        try:
            res = requests.get(url, timeout=6)
            if res.status_code == 200 and len(res.content) > 10000:
                return res.content
        except Exception:
            continue
    return None

FONT_BYTES = load_hd_font_bytes()

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
        'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
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

# ----------------- MASSIVE VIRAL OVERLAY GENERATOR -----------------
def create_subtitle_overlays(segments, position, color_name, preset_style, font_size_user, vw, vh, out_dir):
    color_dict = {
        "Yellow Highlight": (255, 230, 0),
        "Neon Cyan": (0, 245, 255),
        "Pure White": (255, 255, 255),
        "Vibrant Green": (0, 255, 128),
        "Hot Pink": (255, 30, 150)
    }
    fill_col = color_dict.get(color_name, (255, 230, 0))
    os.makedirs(out_dir, exist_ok=True)

    # 3X Scaled Font Size for full-screen readability
    font_size = max(55, int((vw / 1080.0) * font_size_user * 2.6))

    if FONT_BYTES:
        font = ImageFont.truetype(io.BytesIO(FONT_BYTES), font_size)
    else:
        font = ImageFont.load_default()

    overlay_files = []
    for idx, seg in enumerate(segments):
        img = Image.new("RGBA", (vw, vh), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        text = seg['text'].strip().upper()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        x = (vw - text_w) // 2
        
        if position == "Top":
            y = int(vh * 0.16)
        elif position == "Middle":
            y = (vh - text_h) // 2
        else:
            y = int(vh * 0.74)

        if preset_style == "Modern Pill Badge":
            pad_x = int(vw * 0.04)
            pad_y = int(vh * 0.015)
            badge_rect = [x - pad_x, y - pad_y, x + text_w + pad_x, y + text_h + pad_y]
            draw.rounded_rectangle(badge_rect, radius=int(vh*0.02), fill=(0, 0, 0, 215))
            draw.text((x, y), text, font=font, fill=fill_col, stroke_width=3, stroke_fill=(0, 0, 0, 255))
        
        elif preset_style == "Neon Glow & Shadow":
            glow_col = (fill_col[0], fill_col[1], fill_col[2], 140)
            for offset in [(5,5), (-5,-5), (5,-5), (-5,5), (0,6), (6,0)]:
                draw.text((x + offset[0], y + offset[1]), text, font=font, fill=glow_col, stroke_width=10, stroke_fill=(0,0,0,180))
            draw.text((x, y), text, font=font, fill=(255, 255, 255), stroke_width=5, stroke_fill=(0, 0, 0, 255))

        elif preset_style == "Clean Minimalist":
            draw.text((x + 4, y + 4), text, font=font, fill=(0, 0, 0, 180))
            draw.text((x, y), text, font=font, fill=fill_col)

        else:  # Hormozi Viral Pop
            stroke_width = max(8, int(font_size * 0.14))
            shadow_offset = max(6, int(font_size * 0.09))
            draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, 210), stroke_width=stroke_width, stroke_fill=(0, 0, 0, 210))
            draw.text((x, y), text, font=font, fill=fill_col, stroke_width=stroke_width, stroke_fill=(0, 0, 0, 255))

        filename = os.path.join(out_dir, f"sub_{idx}.png")
        img.save(filename, "PNG")
        overlay_files.append((filename, seg['start'], seg['end']))
        
    return overlay_files

# ----------------- UI WORKSPACE -----------------
st.title("🎬 CaptionVFX AI Studio Pro")
st.caption("Massive Viral Typography • Hormozi 1-2 Word Pop • 4K Visual Boost")

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
            ⚡ <b>Canvas:</b> {vw}x{vh} HD<br>
            ⏱️ <b>Duration:</b> {video_duration:.1f}s | Hormozi Fast-Cut Sync
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
            preset_style = st.selectbox(
                "✨ Subtitle VFX Style",
                [
                    "Hormozi Viral Pop",
                    "Neon Glow & Shadow",
                    "Modern Pill Badge",
                    "Clean Minimalist"
                ]
            )
            primary_color = st.selectbox(
                "🎯 Highlight Color",
                [
                    "Yellow Highlight",
                    "Neon Cyan",
                    "Pure White",
                    "Vibrant Green",
                    "Hot Pink"
                ]
            )
        
        with c2:
            position = st.selectbox("📍 Subtitle Position", ["Bottom", "Middle", "Top"])
            font_size_user = st.slider("🔤 Font Size", 40, 100, 70)

        st.markdown("---")
        st.subheader("🚀 Video Enhancements")
        e1, e2 = st.columns(2)
        with e1:
            enable_enhancer = st.checkbox("✨ 4K Clarity & Color Boost", value=True)
        with e2:
            slowmo_option = st.selectbox(
                "⏱️ Speed / Slow-Motion",
                [
                    "Normal Speed (1.0x)",
                    "Smooth Slow-Mo (0.75x)",
                    "Dramatic Slow-Mo (0.5x)"
                ]
            )

        custom_override = st.text_input("✍️ Manual Subtitle Override (Optional)", placeholder="Khaali chhoden agar auto audio detect chahiye")

    if st.button("🚀 Render Subtitled Video", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 1. Clean Audio Track
        status_text.text("🎙️ Extracting Clean Audio Track...")
        progress_bar.progress(25)
        cmd_extract = f'"{FFMPEG_EXE}" -y -i "{input_path}" -vn -acodec pcm_s16le -ar 16000 -ac 1 "{audio_path}"'
        subprocess.run(cmd_extract, shell=True, capture_output=True)

        # 2. Voice AI Transcription
        status_text.text("🤖 Transcribing Real Spoken Words...")
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

        # Divide into Fast 1 to 2 word punchy chunks (Real Viral Reel Format)
        segments = []
        if recognized_text:
            words = recognized_text.split()
            chunk_size = 2  # Max 2 words per screen
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

        # 3. Clean Massive HD Overlays
        status_text.text("🎨 Generating Large Viral Typography...")
        progress_bar.progress(70)
        overlays = create_subtitle_overlays(segments, position, primary_color, preset_style, font_size_user, vw, vh, overlays_dir)

        # 4. Multi-Overlay + Enhancements Burn
        status_text.text("⚡ Applying Enhancements & Merging...")
        progress_bar.progress(85)
        
        input_args = [f'-i "{input_path}"']
        filter_chains = []
        
        base_v_filters = []
        if enable_enhancer:
            base_v_filters.append("unsharp=5:5:0.8:5:5:0.0,eq=contrast=1.08:saturation=1.15")
        
        if "0.75x" in slowmo_option:
            base_v_filters.append("setpts=1.333*PTS")
        elif "0.5x" in slowmo_option:
            base_v_filters.append("setpts=2.0*PTS")

        if base_v_filters:
            filter_chains.append(f"[0:v]{','.join(base_v_filters)}[v_base]")
            last_v = "v_base"
        else:
            last_v = "0:v"

        for i, (ov_file, st_t, en_t) in enumerate(overlays, 1):
            input_args.append(f'-i "{ov_file}"')
            next_v = f"v{i}"
            mult = 1.333 if "0.75x" in slowmo_option else (2.0 if "0.5x" in slowmo_option else 1.0)
            adj_st = st_t * mult
            adj_en = en_t * mult
            filter_chains.append(f"[{last_v}][{i}:v]overlay=0:0:enable='between(t,{adj_st:.2f},{adj_en:.2f})'[{next_v}]")
            last_v = next_v

        af_filters = []
        if "0.75x" in slowmo_option:
            af_filters.append("atempo=0.75")
        elif "0.5x" in slowmo_option:
            af_filters.append("atempo=0.5")

        filter_complex_str = ";".join(filter_chains)
        input_args_str = " ".join(input_args)
        af_str = f'-af "{",".join(af_filters)}"' if af_filters else ""

        cmd_render = f'"{FFMPEG_EXE}" -y {input_args_str} -filter_complex "{filter_complex_str}" -map "[{last_v}]" -map 0:a? {af_str} -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac "{output_path}"'
        subprocess.run(cmd_render, shell=True, capture_output=True)

        progress_bar.progress(100)
        status_text.empty()

        # 5. Output Display & Download
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            st.success("✅ Massive Viral Reel Ready!")
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
    
