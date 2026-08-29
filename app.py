import streamlit as st
import subprocess
import os
from faster_whisper import WhisperModel
import vfx_engine as fx

st.set_page_config(page_title="CaptionVFX Studio AI", page_icon="🎬", layout="wide")

@st.cache_resource
def load_whisper_models():
    tiny = WhisperModel("tiny", device="cpu", compute_type="int8", cpu_threads=4)
    base = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=4)
    return tiny, base

tiny_model, base_model = load_whisper_models()

# ==================== SIDEBAR CONTROLS ====================
st.sidebar.markdown("## ⚙️ Settings")
perf_mode = st.sidebar.radio("⚡ Speed Mode", ["🚀 Turbo Fast (5x Speed)", "🎯 Ultra Precision"])
auto_vibe = st.sidebar.checkbox("🤖 AI Auto-Detect Reel Type (Vlog/Intro/Podcast)", value=True)

# 1. Emoji Toggle Switch (Step 2 Feature)
enable_emojis = st.sidebar.checkbox("😍 Auto-Add Smart Emojis to Captions", value=True)

preset_style = st.sidebar.selectbox(
    "🎨 Manual VFX Style",
    ["🔥 Hormozi Pop-Bounce", "🎤 CapCut Karaoke", "⚡ Neon Glow", "🧊 3D Deep Shadow", "✨ Fade-In Up", "🎯 Clean Minimal"]
)
words_layout = st.sidebar.radio("📝 Layout Flow", ["1 Word", "2-3 Words", "Full Sentence"])
language_choice = st.sidebar.selectbox(
    "🌐 Audio Language",
    ["Pure Hinglish / Roman Hindi", "Auto-Detect Language", "English", "Hindi (हिन्दी)", "Spanish (Español)", "French (Français)", "German (Deutsch)", "Russian (Русский)"]
)
translate_to_en = st.sidebar.checkbox("🔄 Translate to English", value=False)
all_uppercase = st.sidebar.checkbox("🔠 Convert to UPPERCASE", value=True)

enable_slowmo = st.sidebar.checkbox("⏱️ Enable Slow Motion", value=False)
speed_rate = "0.5x"
if enable_slowmo:
    speed_rate = st.sidebar.selectbox("Speed Rate", ["0.75x", "0.5x", "0.25x"])

enable_enhancer = st.sidebar.checkbox("✨ 4K Quality Boost", value=False)

# ==================== MAIN WORKSPACE ====================
st.title("🎬 CaptionVFX AI Studio")
uploaded_file = st.file_uploader("Upload Reel / Short Video (MP4/MOV)", type=["mp4", "mov"])

if uploaded_file:
    col1, col2 = st.columns(2)
    with col1:
        st.video(uploaded_file)
    with col2:
        if st.button("🚀 Render Subtitled Video", type="primary", use_container_width=True):
            with st.spinner("Processing AI Video with Smart Emojis..."):
                with open("temp_input.mp4", "wb") as f:
                    f.write(uploaded_file.read())

                subprocess.run("ffmpeg -y -i temp_input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 temp_audio.wav", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                active_model = tiny_model if "Turbo Fast" in perf_mode else base_model
                active_color = fx.detect_best_contrast_color("temp_input.mp4")

                lang_map = {"English": "en", "Hindi (हिन्दी)": "hi", "Spanish (Español)": "es", "French (Français)": "fr", "German (Deutsch)": "de", "Russian (Русский)": "ru"}
                convert_to_roman = False
                task_type = "translate" if translate_to_en else "transcribe"

                if language_choice == "Pure Hinglish / Roman Hindi":
                    segments_gen, _ = active_model.transcribe("temp_audio.wav", word_timestamps=True, language="hi", initial_prompt="यह हिंदी में है।")
                    convert_to_roman = True
                elif language_choice in lang_map:
                    segments_gen, _ = active_model.transcribe("temp_audio.wav", word_timestamps=True, language=lang_map[language_choice], task=task_type)
                else:
                    segments_gen, _ = active_model.transcribe("temp_audio.wav", word_timestamps=True, task=task_type)

                segments = list(segments_gen)
                full_text = " ".join([seg.text for seg in segments])

                if auto_vibe:
                    vibe = fx.classify_reel_vibe(full_text)
                    st.success(f"🎯 AI Detected: **{vibe['name']}**")
                    effect_tag = f"{{\\c{active_color}" + vibe["tag"][1:]
                    font_family, chosen_layout, outline_s, shadow_s = vibe["font"], vibe["words"], vibe["outline"], vibe["shadow"]
                else:
                    font_family, chosen_layout, outline_s, shadow_s = "Arial Black", words_layout, 8, 4
                    if "Hormozi" in preset_style:
                        effect_tag = f"{{\\c{active_color}\\t(0,70,\\fscx125\\fscy125)\\t(70,140,\\fscx100\\fscy100)\\shad5}}"
                    elif "Karaoke" in preset_style:
                        effect_tag = f"{{\\c{active_color}\\2c&H00FFFFFF&\\k50}}"
                    else:
                        effect_tag = f"{{\\c{active_color}}}"

                speed_factor = 1.0
                if enable_slowmo:
                    speed_factor = 1.0 / float(speed_rate.replace("x", ""))

                ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ReelStyle,{font_family},80,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,{outline_s},{shadow_s},2,20,20,450,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
                events = []
                if "1 Word" in chosen_layout:
                    for segment in segments:
                        for word in segment.words:
                            start = fx.format_ass_time(word.start * speed_factor)
                            end = fx.format_ass_time(word.end * speed_factor)
                            raw_word = word.word.strip()
                            # 2. Emoji Insertion Logic
                            if enable_emojis:
                                raw_word = fx.attach_smart_emoji(raw_word)
                            text = fx.clean_to_roman_text(raw_word) if convert_to_roman else raw_word
                            if all_uppercase: text = text.upper()
                            if text: events.append(f"Dialogue: 0,{start},{end},ReelStyle,,0,0,0,,{effect_tag}{text}")
                elif "2-3 Words" in chosen_layout:
                    for segment in segments:
                        words = segment.words
                        for i in range(0, len(words), 3):
                            chunk = words[i:i + 3]
                            if not chunk: continue
                            start = fx.format_ass_time(chunk[0].start * speed_factor)
                            end = fx.format_ass_time(chunk[-1].end * speed_factor)
                            parts = []
                            for w in chunk:
                                raw_w = w.word.strip()
                                if enable_emojis:
                                    raw_w = fx.attach_smart_emoji(raw_w)
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
                        if enable_emojis:
                            raw_seg_words = [fx.attach_smart_emoji(w) for w in raw_seg_words]
                        raw_seg = " ".join(raw_seg_words)
                        text = fx.clean_to_roman_text(raw_seg) if convert_to_roman else raw_seg
                        if all_uppercase: text = text.upper()
                        if text: events.append(f"Dialogue: 0,{start},{end},ReelStyle,,0,0,0,,{effect_tag}{text}")

                with open("subtitles.ass", "w", encoding="utf-8") as f:
                    f.write(ass_header + "\n".join(events))

                vf_filters = ["ass=subtitles.ass"]
                af_filters = []

                if enable_slowmo:
                    val = float(speed_rate.replace("x", ""))
                    vf_filters.insert(0, f"setpts={1.0/val}*PTS")
                    af_filters.append(f"atempo={val}")

                if enable_enhancer:
                    vf_filters.append("unsharp=7:7:1.4:7:7:0.0,eq=contrast=1.1:saturation=1.15")

                vf_str = ",".join(vf_filters)
                af_str = f'-af "{",".join(af_filters)}"' if af_filters else '-c:a aac'

                cmd = f'ffmpeg -y -i temp_input.mp4 -vf "{vf_str}" {af_str} -c:v libx264 -pix_fmt yuv420p -preset ultrafast -threads 4 output.mp4'
                subprocess.run(cmd, shell=True)

                st.success("🎉 Video Ready with Smart Emojis!")
                st.video("output.mp4")
                with open("output.mp4", "rb") as file:
                    st.download_button("📥 Download Reel", data=file, file_name="caption_vfx_reel.mp4", mime="video/mp4", use_container_width=True)
                                        
