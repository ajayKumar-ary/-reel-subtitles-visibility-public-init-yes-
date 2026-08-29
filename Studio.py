def classify_reel_vibe(transcript_text, duration):
    """
    AI text analyze karke reel ka category aur motion animation decide karta hai.
    """
    text_lower = transcript_text.lower()
    
    # 1. Introduction / Hook (Short & Punchy intro words)
    if any(w in text_lower for w in ["welcome", "hello", "today", "aaj", "dekho", "listen", "secret", "kaise"]):
        return {
            "preset": "🔥 Hormozi Pop-Bounce",
            "font": "Impact",
            "words": "1 Word (Fast Reels)",
            "style_tag": r"{\t(0,70,\fscx130\fscy130)\t(70,140,\fscx100\fscy100)\shad6}"
        }
    
    # 2. Vlog Style (Travel, daily life, relaxed)
    elif any(w in text_lower for w in ["vlog", "travel", "ghumne", "morning", "life", "friends", "khana", "trip"]):
        return {
            "preset": "✨ Smooth Fade-In Up",
            "font": "Montserrat Black",
            "words": "2-3 Words (Natural)",
            "style_tag": r"{\fad(140,80)\blur2}"
        }
    
    # 3. Motivational / Energy / Workout
    elif any(w in text_lower for w in ["hardwork", "success", "mehnat", "gym", "money", "focus", "goal", "mindset"]):
        return {
            "preset": "⚡ Neon Cyberpunk Glow",
            "font": "Arial Black",
            "words": "1 Word (Fast Reels)",
            "style_tag": r"{\blur6\t(0,60,\fscx120\fscy120)\t(60,120,\fscx100\fscy100)}"
        }
    
    # 4. Podcast / Storytelling / Default
    else:
        return {
            "preset": "🎤 CapCut Karaoke Highlight",
            "font": "Trebuchet MS",
            "words": "2-3 Words (Natural)",
            "style_tag": r"{\2c&H00FFFFFF&\k45}"
        }
      
