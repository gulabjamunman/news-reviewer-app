import os
import requests
import streamlit as st
from dotenv import load_dotenv
import random
from collections import Counter
from datetime import datetime, timedelta

# ================== ENV ==================
load_dotenv()

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
BASE_ID = os.getenv("BASE_ID")

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

ARTICLES_URL = f"https://api.airtable.com/v0/{BASE_ID}/Articles"
REVIEWS_URL = f"https://api.airtable.com/v0/{BASE_ID}/Human Reviews"

# ================== NORMALIZATION ==================
def normalize_reviewer_id(rid):
    if not rid:
        return None
    return rid.strip().lower()

# ================== AIRTABLE HELPERS ==================
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

def save_review(data):
    requests.post(REVIEWS_URL, headers=HEADERS, json={"fields": data})

# ================== STREAK LOGIC ==================
def calculate_streak(dates):
    if not dates:
        return 0

    dates = sorted(set(dates))
    streak = 1

    for i in range(len(dates) - 1, 0, -1):
        if dates[i] - dates[i - 1] == timedelta(days=1):
            streak += 1
        else:
            break

    return streak

def get_reviewer_stats():
    reviews = fetch_all_records(REVIEWS_URL)

    data = {}
    for r in reviews:
        rid = normalize_reviewer_id(r.get("fields", {}).get("Reviewer ID"))
        if not rid:
            continue

        data.setdefault(rid, {"count": 0, "dates": []})
        data[rid]["count"] += 1

        created = r.get("createdTime")
        if created:
            date = datetime.fromisoformat(created.replace("Z", "")).date()
            data[rid]["dates"].append(date)

    stats = []
    for rid, info in data.items():
        streak = calculate_streak(info["dates"])
        stats.append((rid, info["count"], streak))

    return sorted(stats, key=lambda x: x[1], reverse=True)

def get_historical_review_count(reviewer_id):
    reviews = fetch_all_records(REVIEWS_URL)
    norm_id = normalize_reviewer_id(reviewer_id)

    return sum(
        1 for r in reviews
        if normalize_reviewer_id(r.get("fields", {}).get("Reviewer ID")) == norm_id
    )

# ================== SESSION ==================
if "reviewer_id" not in st.session_state:
    st.session_state.reviewer_id = ""

if "current_article" not in st.session_state:
    st.session_state.current_article = None

# ================== PAGE ==================
st.set_page_config(layout="wide")
st.title("🧠 News Article Review")

st.info("""
Read the article once like a normal reader.  
Then rate how it *felt*, not whether you agree with it.

There are no right or wrong answers.
""")

reviewer_input = st.text_input("Reviewer ID", value=st.session_state.reviewer_id)

if reviewer_input:
    st.session_state.reviewer_id = normalize_reviewer_id(reviewer_input)
else:
    st.stop()

current_id = st.session_state.reviewer_id

# ================== LOAD DATA ==================
all_articles = get_all_articles()
reviews = fetch_all_records(REVIEWS_URL)

reviewed_article_ids = {
    r["fields"].get("Article ID")
    for r in reviews
    if normalize_reviewer_id(r.get("fields", {}).get("Reviewer ID")) == current_id
}

available_articles = [
    a for a in all_articles
    if a["fields"].get("Article ID") not in reviewed_article_ids
]

total_articles = len(all_articles)
reviewed_count = get_historical_review_count(current_id)
remaining_count = total_articles - reviewed_count

# ================== SIDEBAR ==================
st.sidebar.markdown("### 📊 Your Momentum")
st.sidebar.metric("Total articles in system", total_articles)
st.sidebar.metric("You have reviewed", reviewed_count)
st.sidebar.metric("Articles left for you", remaining_count)

progress = reviewed_count / total_articles if total_articles else 0
st.sidebar.progress(progress, text=f"{reviewed_count}/{total_articles}")

st.sidebar.markdown("### 🏆 Top Reviewers")

leaderboard = get_reviewer_stats()[:10]

for rank, (rid, count, streak) in enumerate(leaderboard, start=1):
    badge = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "🔹"
    is_you = rid == current_id
    name = f"**{rid}**" if is_you else rid
    you_tag = " ← you" if is_you else ""

    st.sidebar.markdown(
        f"""
        {badge} **{rank}. {name}**  
        <span style="color:#666">
        {count} reviews · 🔥 {streak}-day streak
        </span>{you_tag}
        """,
        unsafe_allow_html=True
    )

st.sidebar.markdown("### 🧭 Rating Guide")
st.sidebar.markdown("""
**Political Framing**  
1 = Left-leaning  
5 = Right-leaning  

**Language Intensity**  
1 = Calm  
5 = Emotional  

**Sensationalism**  
1 = Straight reporting  
5 = Dramatic  

**Threat Level**  
1 = No alarm  
5 = High alarm  

**Us vs Them Tone**  
1 = No division  
5 = Strong division
""")

# ================== NO ARTICLES LEFT ==================
if not available_articles:
    st.success("🎉 You’ve reviewed all available articles. Thank you!")
    st.stop()

# ================== LOAD ARTICLE ==================
if st.session_state.current_article is None:
    st.session_state.current_article = random.choice(available_articles)

fields = st.session_state.current_article["fields"]
article_id = fields.get("Article ID")
key_suffix = f"_{article_id}"

# ================== LAYOUT ==================
col1, col2 = st.columns([2, 1])

with col1:
    st.header(fields.get("Headline", "No headline"))
    st.write(fields.get("Content", "No content available"))

with col2:
    st.subheader("Your Review")

    with st.form(f"review_form_{article_id}"):

        political = st.slider("Political framing", 1, 5, key=f"political{key_suffix}")
        intensity = st.slider("Language intensity", 1, 5, key=f"intensity{key_suffix}")
        sensational = st.slider("Sensationalism", 1, 5, key=f"sensational{key_suffix}")
        threat = st.slider("Threat level", 1, 5, key=f"threat{key_suffix}")
        group = st.slider("Us vs them tone", 1, 5, key=f"group{key_suffix}")

        emotions = st.text_input("Emotions felt (optional)", key=f"emotions{key_suffix}")
        highlight = st.text_area("Sentence that shaped your impression", key=f"highlight{key_suffix}")

        submit = st.form_submit_button("Submit Review")

    if submit:
        save_review({
            "Reviewer ID": current_id,
            "Article ID": article_id,
            "Political": political,
            "Intensity": intensity,
            "Sensational": sensational,
            "Threat": threat,
            "GroupConflict": group,
            "Emotions": emotions,
            "Highlight": highlight
        })

        st.success("🌟 Review submitted. Thank you!")
        st.session_state.current_article = None
        st.rerun()

    if st.button("Skip Article"):
        st.session_state.current_article = random.choice(available_articles)
        st.rerun()
