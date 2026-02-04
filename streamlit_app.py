import os
import requests
import streamlit as st
from dotenv import load_dotenv

# ------------------ LOAD ENV ------------------
load_dotenv()

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
BASE_ID = os.getenv("BASE_ID")

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

ARTICLES_URL = f"https://api.airtable.com/v0/{BASE_ID}/Articles"
REVIEWS_URL = f"https://api.airtable.com/v0/{BASE_ID}/Human Reviews"

# ------------------ HELPERS ------------------

def get_next_article():
    res = requests.get(ARTICLES_URL, headers=HEADERS).json()
    for record in res.get("records", []):
        fields = record["fields"]
        if fields.get("Review Count", 0) < fields.get("Max Reviews", 5):
            return record
    return None

def increment_review_count(record_id, current_count):
    url = f"{ARTICLES_URL}/{record_id}"
    requests.patch(url, headers=HEADERS, json={
        "fields": {"Review Count": current_count + 1}
    })

def save_review(data):
    requests.post(REVIEWS_URL, headers=HEADERS, json={"fields": data})

# ------------------ SESSION STATE ------------------

if "article" not in st.session_state:
    st.session_state.article = get_next_article()

# ------------------ UI ------------------

st.set_page_config(layout="wide")
st.title("🧠 News Article Review")

if not st.session_state.article:
    st.success("No articles left to review. Thank you!")
    st.stop()

fields = st.session_state.article["fields"]

# Layout columns
col1, col2 = st.columns([2, 1])

with col1:
    st.header(fields.get("Headline", "No headline"))
    st.write(fields.get("Content", "No content available"))

with col2:
    st.subheader("Your Review")

    reviewer_id = st.text_input("Reviewer ID")

    political = st.slider("Political Leaning", 1, 5)
    intensity = st.slider("Language Intensity", 1, 5)
    sensational = st.slider("Sensationalism", 1, 5)
    threat = st.slider("Threat/Alarm Level", 1, 5)
    group = st.slider("Us vs Them Tone", 1, 5)

    emotions = st.text_input("Emotions you felt (comma separated)")
    highlight = st.text_area("Sentence that shaped your impression (optional)")

    if st.button("Submit Review"):
        if not reviewer_id:
            st.warning("Please enter your Reviewer ID.")
        else:
            save_review({
                "Reviewer ID": reviewer_id,
                "Article ID": fields.get("Article ID"),
                "Political": political,
                "Intensity": intensity,
                "Sensational": sensational,
                "Threat": threat,
                "GroupConflict": group,
                "Emotions": emotions,
                "Highlight": highlight
            })

            increment_review_count(
                st.session_state.article["id"],
                fields.get("Review Count", 0)
            )

            st.success("Review submitted!")

            # Load next article
            st.session_state.article = get_next_article()
            st.rerun()
