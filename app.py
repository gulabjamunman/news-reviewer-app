import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env", override=True)

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
BASE_ID = os.getenv("BASE_ID")

print("RAW TOKEN repr:", repr(AIRTABLE_TOKEN))
print("BASE ID repr:", repr(BASE_ID))


HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

app = Flask(__name__, static_folder=".")
sessions = {}

# ---------------- Serve Frontend ----------------
@app.route("/")
def home():
    return app.send_static_file("index.html")

# ---------------- Airtable Helpers ----------------
def validate_reviewer(rid):
    url = f"https://api.airtable.com/v0/{BASE_ID}/Reviewers"
    res = requests.get(url, headers=HEADERS).json()
    print("Airtable reviewer response:", res)
    for r in res.get("records", []):
        fields = r.get("fields", {})
        if fields.get("Reviewer ID") == rid and fields.get("Active"):
            return True
    return False


def get_next_article():
    url = f"https://api.airtable.com/v0/{BASE_ID}/Articles"
    res = requests.get(url, headers=HEADERS).json()
    for r in res.get("records", []):
        count = r["fields"].get("Review Count", 0)
        maxr = r["fields"].get("Max Reviews", 5)
        if count < maxr:
            return r
    return None


def save_review(data):
    url = f"https://api.airtable.com/v0/{BASE_ID}/Human Reviews"
    requests.post(url, headers=HEADERS, json={"fields": data})


# ---------------- Chat Logic ----------------
@app.route("/chat", methods=["POST"])
def chat():
    user = request.json["user_id"]
    msg = request.json["message"]

    if user not in sessions:
        sessions[user] = {"stage": "ask_id"}

    s = sessions[user]

    if s["stage"] == "ask_id":
        if validate_reviewer(msg):
            s["reviewer_id"] = msg
            article = get_next_article()
            if not article:
                return jsonify({"reply": "No articles left to review. Thank you!"})
            s["article"] = article
            s["responses"] = {}
            s["stage"] = "ask_political"
            return jsonify({"reply": f"Headline: {article['fields']['Headline']}\n\n{article['fields']['Content']}\n\nOn a scale 1–5, how politically left/right did this feel?"})
        return jsonify({"reply": "Invalid ID. Try again."})

    elif s["stage"] == "ask_political":
        s["responses"]["Political"] = int(msg)
        s["stage"] = "ask_intensity"
        return jsonify({"reply": "How emotionally intense was the language? (1–5)"})

    elif s["stage"] == "ask_intensity":
        s["responses"]["Intensity"] = int(msg)
        s["stage"] = "ask_sensational"
        return jsonify({"reply": "How dramatic or sensational was it? (1–5)"})

    elif s["stage"] == "ask_sensational":
        s["responses"]["Sensational"] = int(msg)
        s["stage"] = "ask_threat"
        return jsonify({"reply": "How alarming or threatening did it feel? (1–5)"})

    elif s["stage"] == "ask_threat":
        s["responses"]["Threat"] = int(msg)
        s["stage"] = "ask_group"
        return jsonify({"reply": "Did it feel like an 'us vs them' conflict? (1–5)"})

    elif s["stage"] == "ask_group":
        s["responses"]["GroupConflict"] = int(msg)
        s["stage"] = "ask_emotions"
        return jsonify({"reply": "What emotions did you feel? (comma separated)"})

    elif s["stage"] == "ask_emotions":
        s["responses"]["Emotions"] = msg
        s["stage"] = "ask_highlight"
        return jsonify({"reply": "Paste a sentence that shaped your impression (optional)"})

    elif s["stage"] == "ask_highlight":
        s["responses"]["Highlight"] = msg
        save_review({
            "Reviewer ID": s["reviewer_id"],
            "Article ID": s["article"]["fields"]["Article ID"],
            **s["responses"]
        })
        s["stage"] = "ask_id"
        return jsonify({"reply": "Thanks! Send your ID again to review another article."})

    return jsonify({"reply": "Something went wrong."})


if __name__ == "__main__":
    app.run(debug=True)
