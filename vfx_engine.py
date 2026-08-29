def attach_smart_emoji(word):
    """
    Spoken words (Hindi, Hinglish, English) ke hisab se smart context emojis add karta hai.
    """
    clean_w = re.sub(r'[^\w\s]', '', word.lower()).strip()
    
    emoji_dict = {
        # Money / Business / Rich
        "money": " 💰", "paisa": " 💰", "paise": " 💰", "cash": " 💵", "rich": " 🤑",
        "ameer": " 🤑", "crore": " 💸", "lakh": " 💸", "profit": " 📈", "loss": " 📉",
        
        # Fire / Energy / Viral
        "fire": " 🔥", "viral": " 🚀", "super": " ⚡", "energy": " ⚡", "power": " 💥",
        "trending": " 📈", "boom": " 💥", "aag": " 🔥",
        
        # Fitness / Motivation / Hardwork
        "gym": " 🏋️", "workout": " 💪", "hardwork": " 💪", "mehnat": " 🦾",
        "strong": " 🥊", "body": " 🏋️", "focus": " 🎯", "target": " 🎯", "goal": " 🏆",
        
        # Love / Emotion / Happy / Sad
        "love": " ❤️", "pyar": " ❤️", "dil": " ❤️", "happy": " 😄", "khush": " 😊",
        "smile": " 😁", "sad": " 😢", "cry": " 😭", "alone": " 🥀", "pain": " 💔",
        
        # Travel / Food / Daily Life
        "travel": " ✈️", "trip": " 🧳", "car": " 🚗", "gaadi": " 🚘", "bike": " 🏍️",
        "flight": " ✈️", "food": " 🍕", "khana": " 🍔", "tea": " ☕", "chai": " ☕",
        "morning": " ☀️", "night": " 🌙", "vlog": " 📹", "camera": " 📸",
        
        # Social / Tech / Calls
        "phone": " 📱", "mobile": " 📱", "call": " 📞", "video": " 🎬",
        "subscribe": " 🔔", "follow": " 👉", "secret": " 🤫", "idea": " 💡",
        "mind": " 🧠", "brain": " 🧠", "stop": " 🛑", "wait": " ⏳", "time": " ⏰"
    }
    
    emoji = emoji_dict.get(clean_w, "")
    return word + emoji
  
