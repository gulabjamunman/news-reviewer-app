import os
import random
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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

# ---------- LOAD DATA FROM SUPABASE ----------
def get_review_queue():
    queue = supabase.table("review_articles").select("article_id").eq("active", True).execute().data
    return [q["article_id"] for q in queue]

def get_articles(article_ids):
    return supabase.table("articles").select("id, headline, content").in_("id", article_ids).execute().data

def get_reviews_by_user(reviewer_id):
    return supabase.table("human_reviews").select("article_id").eq("reviewer_id", reviewer_id).execute().data

def save_review(data):
    supabase.table("human_reviews").insert(data).execute()

queue_ids = get_review_queue()
all_articles = get_articles(queue_ids)
user_reviews = get_reviews_by_user(st.session_state.reviewer_id)

reviewed_ids = {r["article_id"] for r in user_reviews}
available_articles = [a for a in all_articles if a["id"] not in reviewed_ids]

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
1 = Left-leaning  
5 = Right-leaning  

**Language Intensity**  
1 = Calm  
5 = Emotional  

**Sensationalism**  
1 = Measured  
5 = Dramatic  

**Threat Level**  
1 = No threat  
5 = Alarmist  

**Us vs Them Tone**  
1 = No division  
5 = Strong division
""")

# ---------- FINISHED ----------
if not available_articles:
    st.success("🎉 You’ve reviewed all available articles. You are officially a news-sensei. Thank you!")
    st.stop()

# ---------- LOAD ARTICLE ----------
if st.session_state.current_article is None:
    st.session_state.current_article = random.choice(available_articles)

article = st.session_state.current_article
article_id = article["id"]
key_suffix = f"_{article_id}"

# ---------- LAYOUT ----------
col1, col2 = st.columns([2, 1])

with col1:
    st.header(article.get("headline", "No headline"))
    st.write(article.get("content", "No content available"))

with col2:
    st.subheader("Your Review")

    st.markdown("### 💭 Emotional Reaction Guide")
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
        political = st.slider("Left ← → Right", 1, 5, key=f"political{key_suffix}")

        st.markdown("### 🌡 Language Intensity")
        intensity = st.slider("Calm ← → Emotional", 1, 5, key=f"intensity{key_suffix}")

        st.markdown("### 🎬 Sensationalism")
        sensational = st.slider("Measured ← → Dramatic", 1, 5, key=f"sensational{key_suffix}")

        st.markdown("### 🚨 Threat Level")
        threat = st.slider("Low ← → High", 1, 5, key=f"threat{key_suffix}")

        st.markdown("### 👥 Us vs Them Tone")
        group = st.slider("None ← → Strong", 1, 5, key=f"group{key_suffix}")

        emotions = st.text_input("Emotions you felt", key=f"emotions{key_suffix}")

        highlight = st.text_area(
            "Sentence that shaped your impression",
            key=f"highlight{key_suffix}"
        )

        submit = st.form_submit_button("Submit Review")

    if submit:
        save_review({
            "reviewer_id": st.session_state.reviewer_id,
            "article_id": article_id,
            "political": political,
            "intensity": intensity,
            "sensational": sensational,
            "threat": threat,
            "group_conflict": group,
            "emotions": emotions,
            "highlight": highlight
        })

        st.success("🌟 Thank you for lending your brainpower! The algorithm just got smarter thanks to you 🤖💛")

        st.session_state.current_article = None
        st.rerun()

    if st.button("Skip Article"):
        st.session_state.current_article = random.choice(available_articles)
        st.rerun()
