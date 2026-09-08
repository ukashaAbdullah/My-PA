import streamlit as st
from agent import search_and_rank
from db import init_db, load_profile, save_profile, save_opportunities, load_saved, toggle_saved

st.set_page_config(
    page_title="CareerBuddy AI",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

st.markdown("""
<style>
.main {background: #fbfbfe;}
.block-container {padding-top: 1.5rem; max-width: 1200px;}
.hero {
    padding: 24px 28px; border-radius: 24px;
    background: linear-gradient(135deg, #f1edff, #eef9ff);
    border: 1px solid #e7e1ff; margin-bottom: 20px;
}
.card {
    padding: 18px; border-radius: 18px; border: 1px solid #e9e9ef;
    background: white; margin-bottom: 12px;
}
.score {font-size: 28px; font-weight: 800;}
.small {color:#666; font-size: 0.9rem;}
</style>
""", unsafe_allow_html=True)

profile = load_profile()

st.markdown("""
<div class="hero">
<h1>🌱 CareerBuddy AI</h1>
<p>Your personal opportunity finder for scholarships, internships, hackathons & AI career opportunities.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("👤 My Profile")
    degree = st.text_input("Degree", profile.get("degree", "BS Artificial Intelligence"))
    university = st.text_input("University", profile.get("university", "UET Lahore"))
    semester = st.number_input("Semester", 1, 16, int(profile.get("semester", 3)))
    gpa = st.number_input("CGPA / GPA", 0.0, 4.0, float(profile.get("gpa", 3.36)), step=0.01)

    interests = st.text_area(
        "Interests",
        profile.get("interests", "AI/ML, Generative AI, Agentic AI, Computer Vision, AI Research")
    )
    skills = st.text_area(
        "Current skills",
        profile.get(
            "skills",
            "Basic programming, C++, OOP, HTML, CSS, Python basics, NumPy basics, Pandas basics, OpenCV, GitHub basics"
        )
    )
    projects = st.text_area(
        "Projects / experience",
        profile.get(
            "projects",
            "OpenCV project; website; personal AI Python tutor; Google certificates; Agentic AI course"
        )
    )

    if st.button("💾 Save profile", use_container_width=True):
        save_profile({
            "degree": degree, "university": university, "semester": semester,
            "gpa": gpa, "interests": interests, "skills": skills, "projects": projects
        })
        st.success("Profile saved!")

st.subheader("🔎 Find opportunities")

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    category = st.selectbox(
        "What should I search for?",
        ["Everything", "Scholarships", "Internships", "Hackathons", "Research", "Summer Schools", "Competitions"]
    )
with col2:
    region = st.selectbox("Region", ["Pakistan + International", "Pakistan", "International", "Remote"])
with col3:
    max_results = st.slider("Results", 5, 20, 10)

query = st.text_input(
    "Optional search focus",
    placeholder="e.g. AI internship summer 2027, fully funded undergraduate scholarship"
)

if st.button("🚀 Search & rank opportunities", type="primary", use_container_width=True):
    with st.spinner("Searching the web, checking relevance and ranking opportunities..."):
        result = search_and_rank(
            profile={
                "degree": degree, "university": university, "semester": semester,
                "gpa": gpa, "interests": interests, "skills": skills, "projects": projects
            },
            category=category,
            region=region,
            custom_query=query,
            max_results=max_results,
        )
        st.session_state["results"] = result
        save_opportunities(result)

results = st.session_state.get("results", [])

if results:
    st.subheader(f"✨ Top matches ({len(results)})")

    for item in results:
        score = item.get("match_score", 0)
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"### {item.get('title','Opportunity')}")
                st.write(item.get("summary", ""))
                st.markdown(
                    f"**Type:** {item.get('type','Other')}  ·  "
                    f"**Deadline:** {item.get('deadline','Not found')}  ·  "
                    f"**Location:** {item.get('location','Not specified')}"
                )
                st.markdown(f"**Why it matches:** {item.get('why_match','')}")
                if item.get("eligibility"):
                    st.markdown(f"**Eligibility:** {item['eligibility']}")
                if item.get("url"):
                    st.link_button("🔗 Open official opportunity", item["url"])
            with c2:
                st.markdown(f'<div class="score">{score}%</div><div class="small">match</div>', unsafe_allow_html=True)
                if st.button("🔖 Save", key=f"save_{item.get('id')}"):
                    toggle_saved(item.get("id"), True)
                    st.toast("Saved!")
            st.markdown("</div>", unsafe_allow_html=True)

    st.info("Tip: open the official page before applying. The agent ranks opportunities but does not guarantee eligibility.")

st.divider()
st.subheader("🔖 Saved opportunities")
saved = load_saved()
if not saved:
    st.caption("No saved opportunities yet.")
else:
    for item in saved:
        st.markdown(f"- **{item['title']}** — {item.get('match_score',0)}% match — {item.get('url','')}")
