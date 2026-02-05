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

# ---------- AIRTABLE PAGINATION ----------
def fetch_all_records(url, params=None):
    records = []
    offset = None

    while True:
        query = params.copy() if params else {}
        if offset:
            query["offset"] = offset

        res = requests.get(url, headers=HEADERS, params=query).json()
        records.extend(res.get("records", []))
        offset = res.get("offset")

        if not offset:
            break

    return records


def get_all_articles():
    return fetch_all_records(ARTICLES_URL)


def get_reviews_by_user(reviewer_id):
    formula = f"{{Reviewer ID}}='{reviewer_id}'"
    return fetch_all_records(REVIEWS_URL, {"filterByFormula": formula})


def save_review(data):
    requests.post(REVIEWS_URL, headers=HEADERS, json={"fields": data})


# ---------- SESSION STATE ----------
if "reviewer_id" not in st.session_state:
    st.session_state.reviewer_id = ""

if "current_article" not in st.session_state:
    st.session_state.current_article = None


# ---------- PAGE SETUP ----------
st.set_page_config(layout="wide")
st.title("🧠 News Article Review")

st.info("""
**How to review:**  
Read the article once like a normal reader.  
Then rate how it *felt*, not whether you agree with it.

There are no right or wrong answers. We are comparing human perception with AI interpretation.
""")

reviewer_input = st.text_input("Reviewer ID", value=st.session_state.reviewer_id)

if reviewer_input:
    st.session_state.reviewer_id = reviewer_input
else:
    st.stop()

# ---------- LOAD DATA ----------
all_articles = get_all_articles()
user_reviews = get_reviews_by_user(st.session_state.reviewer_id)

reviewed_ids = {r["fields"].get("Article ID") for r in user_reviews}
available_articles = [a for a in all_articles if a["fields"].get("Article ID") not in reviewed_ids]

total_articles = len(all_articles)
reviewed_count = len(reviewed_ids)
remaining_count = len(available_articles)

# ---------- SIDEBAR ----------
st.sidebar.metric("Total articles in system", total_articles)
st.sidebar.metric("You have reviewed", reviewed_count)
st.sidebar.metric("Articles left for you", remaining_count)

progress = reviewed_count / total_articles if total_articles else 0
st.sidebar.progress(progress, text=f"Progress: {reviewed_count}/{total_articles}")

st.sidebar.markdown("### 🧭 Rating Guide")
st.sidebar.markdown("""
**Political Framing**  
1 = Left-leaning (justice, equality, welfare focus)  
5 = Right-leaning (nationalism, security, law & order)

**Language Intensity**  
1 = Calm and factual  
5 = Emotionally charged

**Sensationalism**  
1 = Straight reporting  
5 = Dramatic or exaggerated

**Threat Level**  
1 = No sense of danger  
5 = Strong sense of threat or alarm

**Us vs Them Tone**  
1 = No group division  
5 = Strong group conflict or identity framing
""")

# ---------- FINISHED ----------
if not available_articles:
    st.success("🎉 You’ve reviewed all available articles. You are officially a news-sensei. Thank you!")
    st.stop()

# ---------- LOAD ARTICLE ----------
if st.session_state.current_article is None:
    st.session_state.current_article = random.choice(available_articles)

fields = st.session_state.current_article["fields"]
article_id = fields.get("Article ID")
key_suffix = f"_{article_id}"

# ---------- LAYOUT ----------
col1, col2 = st.columns([2, 1])

with col1:
    st.header(fields.get("Headline", "No headline"))
    st.write(fields.get("Content", "No content available"))

with col2:
    st.subheader("Your Review")

    st.markdown("### 💭 Emotional Reaction Guide")
    st.caption("You don’t need to feel all of these — just notice what stood out.")
    st.markdown("""
    - Fear or anxiety  
    - Anger or outrage  
    - Pride or nationalism  
    - Sympathy or empathy  
    - Distrust or suspicion  
    - Hope or reassurance  
    """)

    with st.form(f"review_form_{article_id}"):

        st.markdown("### 🏛 Political Framing")
        political = st.slider("Left-leaning ← → Right-leaning", 1, 5, key=f"political{key_suffix}")

        st.markdown("### 🌡 Language Intensity")
        intensity = st.slider("Calm ← → Emotionally Charged", 1, 5, key=f"intensity{key_suffix}")

        st.markdown("### 🎬 Sensationalism")
        sensational = st.slider("Measured ← → Dramatic", 1, 5, key=f"sensational{key_suffix}")

        st.markdown("### 🚨 Threat / Alarm Level")
        threat = st.slider("Low Threat ← → High Threat", 1, 5, key=f"threat{key_suffix}")

        st.markdown("### 👥 Us vs Them Tone")
        group = st.slider("No Division ← → Strong Division", 1, 5, key=f"group{key_suffix}")

        st.markdown("### 💬 What emotions did you feel?")
        emotions = st.text_input("Optional", key=f"emotions{key_suffix}")

        st.markdown("### 🧩 What shaped your impression?")
        st.caption("Copy and paste a sentence from the article that influenced your ratings.")
        highlight = st.text_area("Paste sentence here", key=f"highlight{key_suffix}")

        submit = st.form_submit_button("Submit Review")

    if submit:
        save_review({
            "Reviewer ID": st.session_state.reviewer_id,
            "Article ID": article_id,
            "Political": political,
            "Intensity": intensity,
            "Sensational": sensational,
            "Threat": threat,
            "GroupConflict": group,
            "Emotions": emotions,
            "Highlight": highlight
        })

        st.success("🌟 Thank you for lending your brainpower! The algorithm just got smarter thanks to you 🤖💛")

        st.session_state.current_article = None
        st.rerun()

    if st.button("Skip Article"):
        st.session_state.current_article = random.choice(available_articles)
        st.rerun()
