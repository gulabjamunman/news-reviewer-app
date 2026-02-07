import os
import requests
import streamlit as st
from dotenv import load_dotenv
import random
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
REVIEWERS_URL = f"https://api.airtable.com/v0/{BASE_ID}/Reviewers"

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

# ================== REVIEWER AUTH ==================
@st.cache_data(ttl=300)
def get_valid_reviewer_ids():
    records = fetch_all_records(REVIEWERS_URL)
    return {
        normalize_reviewer_id(r["fields"].get("Reviewer ID"))
        for r in records
        if r.get("fields", {}).get("Reviewer ID")
    }

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
        stats.append((rid, info["count"], calculate_streak(info["dates"])))

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
    st.session_state.reviewer_id = None

if "current_article" not in st.session_state:
    st.session_state.current_article = None

# ================== PAGE ==================
st.set_page_config(layout="wide")
st.title("News Article Review")

st.markdown(
    """
    Read the article once like a normal reader.  
    Then rate how it *felt* to you as a reader.

    There are no right or wrong answers.
    """
)

# ================== AUTH GATE ==================
valid_reviewers = get_valid_reviewer_ids()

reviewer_input = st.text_input("Reviewer ID")

if not reviewer_input:
    st.stop()

current_id = normalize_reviewer_id(reviewer_input)

if current_id not in valid_reviewers:
    st.error("Invalid User ID, Contact Devayani in the WhatsApp group to get an ID assigned")
    st.stop()

st.session_state.reviewer_id = current_id

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
st.sidebar.markdown("### Your Progress")
st.sidebar.metric("Articles reviewed", reviewed_count)
st.sidebar.metric("Articles remaining", remaining_count)

progress = reviewed_count / total_articles if total_articles else 0
st.sidebar.progress(progress, text=f"{reviewed_count} / {total_articles}")

st.sidebar.markdown("### Top Reviewers")
for rank, (rid, count, streak) in enumerate(get_reviewer_stats()[:10], start=1):
    tag = " (you)" if rid == current_id else ""
    st.sidebar.markdown(f"{rank}. {rid}{tag}  \n{count} reviews · {streak}-day streak")

# ================== NO ARTICLES LEFT ==================
if not available_articles:
    st.success("You have reviewed all available articles. Thank you.")
    st.stop()

# ================== LOAD ARTICLE ==================
if st.session_state.current_article is None:
    st.session_state.current_article = random.choice(available_articles)

fields = st.session_state.current_article["fields"]
article_id = fields.get("Article ID")
key_suffix = f"_{article_id}"

# ================== LAYOUT ==================
col1, col2 = st.columns([2.2, 1])

with col1:
    st.subheader(fields.get("Headline", "No headline"))
    st.write(fields.get("Content", "No content available"))

with col2:
    st.subheader("Your Assessment")

    with st.form(f"review_form_{article_id}"):

        st.markdown("**Political framing**")
        st.caption("1 = Left-leaning | 3 = Neutral | 5 = Right-leaning")
        political = st.slider(
            " ",
            1, 5,
            key=f"political{key_suffix}"
        )

        st.markdown("**Language intensity**")
        st.caption("1 = Calm, factual | 5 = Highly emotional or charged")
        intensity = st.slider(
            "  ",
            1, 5,
            key=f"intensity{key_suffix}"
        )

        st.markdown("**Sensationalism**")
        st.caption("1 = Straight reporting | 5 = Dramatic or exaggerated")
        sensational = st.slider(
            "   ",
            1, 5,
            key=f"sensational{key_suffix}"
        )

        st.markdown("**Perceived threat level**")
        st.caption("1 = No alarm | 5 = Urgent or alarming")
        threat = st.slider(
            "    ",
            1, 5,
            key=f"threat{key_suffix}"
        )

        st.markdown("**Us vs them tone**")
        st.caption("1 = No division | 5 = Strong in-group vs out-group framing")
        group = st.slider(
            "     ",
            1, 5,
            key=f"group{key_suffix}"
        )

        st.markdown("---")

        emotions = st.text_input("Emotions felt (optional)")
        highlight = st.text_area("Sentence that shaped your impression")

        submit = st.form_submit_button("Submit review")

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

        st.success("Review submitted.")
        st.session_state.current_article = None
        st.rerun()

    if st.button("Skip article"):
        st.session_state.current_article = random.choice(available_articles)
        st.rerun()
