import os
import requests
import streamlit as st
from dotenv import load_dotenv
import random

load_dotenv()

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
BASE_ID = os.getenv("BASE_ID")

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

ARTICLES_URL = f"https://api.airtable.com/v0/{BASE_ID}/Articles"
REVIEWS_URL = f"https://api.airtable.com/v0/{BASE_ID}/Human Reviews"

# ---------- HELPERS ----------

def get_all_articles():
    res = requests.get(ARTICLES_URL, headers=HEADERS).json()
    return res.get("records", [])

def get_reviews_by_user(reviewer_id):
    formula = f"{{Reviewer ID}}='{reviewer_id}'"
    url = f"{REVIEWS_URL}?filterByFormula={formula}"
    res = requests.get(url, headers=HEADERS).json()
    return res.get("records", [])

def save_review(data):
    requests.post(REVIEWS_URL, headers=HEADERS, json={"fields": data})

# ---------- SESSION STATE ----------

if "reviewer_id" not in st.session_state:
    st.session_state.reviewer_id = ""

if "reviewed_articles" not in st.session_state:
    st.session_state.reviewed_articles = set()

if "current_article" not in st.session_state:
    st.session_state.current_article = None

# ---------- UI ----------

st.set_page_config(layout="wide")
st.title("🧠 News Article Review")

# Auto-save reviewer ID
reviewer_input = st.text_input("Reviewer ID", value=st.session_state.reviewer_id)
if reviewer_input:
    st.session_state.reviewer_id = reviewer_input
else:
    st.stop()

# Load data
all_articles = get_all_articles()
user_reviews = get_reviews_by_user(st.session_state.reviewer_id)

st.session_state.reviewed_articles = {
    r["fields"]["Article ID"] for r in user_reviews if "Article ID" in r["fields"]
}

available_articles = [
    a for a in all_articles
    if a["fields"].get("Article ID") not in st.session_state.reviewed_articles
]

total_articles = len(all_articles)
reviewed_count = len(st.session_state.reviewed_articles)

# ---------- SIDEBAR STATS ----------
st.sidebar.metric("Articles remaining", len(available_articles))
st.sidebar.metric("You have reviewed", reviewed_count)

progress = reviewed_count / total_articles if total_articles else 0
st.sidebar.progress(progress, text=f"Progress: {reviewed_count}/{total_articles}")

# ---------- NO MORE ARTICLES ----------
if not available_articles:
    st.success("You have reviewed all available articles. Thank you!")
    st.stop()

# Pick article
if st.session_state.current_article is None:
    st.session_state.current_article = random.choice(available_articles)

fields = st.session_state.current_article["fields"]

# ---------- LAYOUT ----------
col1, col2 = st.columns([2, 1])

with col1:
    st.header(fields.get("Headline"))
    st.write(fields.get("Content"))

with col2:
    st.subheader("Your Review")

    political = st.slider("Political Leaning", 1, 5)
    intensity = st.slider("Language Intensity", 1, 5)
    sensational = st.slider("Sensationalism", 1, 5)
    threat = st.slider("Threat/Alarm Level", 1, 5)
    group = st.slider("Us vs Them Tone", 1, 5)

    emotions = st.text_input("Emotions felt")
    highlight = st.text_area("Sentence that shaped your impression")

    colA, colB = st.columns(2)

    with colA:
        if st.button("Submit Review"):
            save_review({
                "Reviewer ID": st.session_state.reviewer_id,
                "Article ID": fields.get("Article ID"),
                "Political": political,
                "Intensity": intensity,
                "Sensational": sensational,
                "Threat": threat,
                "GroupConflict": group,
                "Emotions": emotions,
                "Highlight": highlight
            })

            st.success("Review submitted!")

            st.session_state.reviewed_articles.add(fields.get("Article ID"))
            st.session_state.current_article = None
            st.rerun()

    with colB:
        if st.button("Skip Article"):
            st.session_state.current_article = random.choice(available_articles)
            st.rerun()
