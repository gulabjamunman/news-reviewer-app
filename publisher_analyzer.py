import re

def clean_generic(text):
    return re.sub(r"\s+", " ", text).strip()

def clean_live_style(text):
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "Updated:" in line or "LIVE" in line:
            continue
        if len(line.split()) < 3:
            continue
        cleaned.append(line)
    return " ".join(cleaned)

def clean_hindi_shortform(text):
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "विज्ञापन" in line:
            continue
        cleaned.append(line)
    return " ".join(cleaned)
