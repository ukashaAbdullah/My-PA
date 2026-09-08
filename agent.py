import os
import re
import json
import hashlib
import requests
from datetime import datetime
from urllib.parse import quote_plus

try:
    from ddgs import DDGS
except Exception:
    DDGS = None

try:
    from groq import Groq
except Exception:
    Groq = None

CATEGORY_QUERIES = {
    "Everything": [
        "AI undergraduate scholarship Pakistan international",
        "AI machine learning internship undergraduate students",
        "AI hackathon university students",
        "AI research internship undergraduate students",
        "AI summer school undergraduate students",
    ],
    "Scholarships": [
        "AI undergraduate scholarship Pakistan international",
        "fully funded undergraduate scholarship computer science artificial intelligence",
    ],
    "Internships": [
        "AI machine learning internship undergraduate students",
        "artificial intelligence summer internship students",
    ],
    "Hackathons": [
        "AI hackathon university students 2026 2027",
        "machine learning hackathon students",
    ],
    "Research": [
        "AI research internship undergraduate students",
        "artificial intelligence undergraduate research opportunity",
    ],
    "Summer Schools": [
        "AI machine learning summer school undergraduate",
        "artificial intelligence summer program students",
    ],
    "Competitions": [
        "AI machine learning competition students",
        "AI coding competition university students",
    ],
}

def _id(title, url):
    return hashlib.sha1((title + url).encode()).hexdigest()[:12]


def send_ntfy(topic, title, message, click_url=None, priority="default", tags=None):
    """Send one push notification through ntfy."""
    topic = (topic or "").strip()
    if not topic:
        return False, "NTFY_TOPIC is not configured."

    # HTTP header values used by requests/http.client must be Latin-1
    # compatible. Keep the message body UTF-8, but sanitize the Title header.
    safe_title = str(title).encode("latin-1", "ignore").decode("latin-1")[:250]
    headers = {
        "Title": safe_title,
        "Priority": str(priority),
    }
    if tags:
        headers["Tags"] = str(tags).encode("latin-1", "ignore").decode("latin-1")
    if click_url:
        headers["Click"] = click_url

    try:
        response = requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode("utf-8"),
            headers=headers,
            timeout=15,
        )
        if 200 <= response.status_code < 300:
            return True, "Notification sent."
        return False, f"ntfy returned HTTP {response.status_code}: {response.text[:300]}"
    except requests.RequestException as exc:
        return False, f"Could not reach ntfy: {exc}"


def _search_web(queries, max_results=20):
    if DDGS is None:
        return []
    found = []
    seen = set()
    try:
        with DDGS() as ddgs:
            for q in queries:
                try:
                    rows = ddgs.text(q, max_results=max_results)
                    for r in rows:
                        title = (r.get("title") or "").strip()
                        url = (r.get("href") or r.get("url") or "").strip()
                        body = (r.get("body") or "").strip()
                        if not title or not url or url in seen:
                            continue
                        seen.add(url)
                        found.append({"title": title, "url": url, "body": body})
                except Exception:
                    continue
    except Exception:
        return []
    return found

def _rule_rank(item, profile):
    text = (item["title"] + " " + item["body"]).lower()
    score = 35
    degree_terms = ["artificial intelligence", "machine learning", "computer science", "data science", "software"]
    if any(x in text for x in degree_terms):
        score += 20
    if any(x in text for x in ["undergraduate", "student", "bachelor", "university"]):
        score += 15
    if any(x in text for x in ["internship", "hackathon", "scholarship", "research", "summer"]):
        score += 10
    for term in re.split(r"[,;/\n]+", profile.get("interests","")):
        term = term.strip().lower()
        if len(term) > 3 and term in text:
            score += 4
    if "pakistan" in text:
        score += 3
    return min(score, 99)

def _groq_rank(items, profile):
    key = os.getenv("GROQ_API_KEY")
    if not key or Groq is None or not items:
        return None

    client = Groq(api_key=key)
    compact = []
    for i, x in enumerate(items[:30]):
        compact.append({
            "index": i,
            "title": x["title"],
            "url": x["url"],
            "snippet": x["body"][:700]
        })

    prompt = f"""
You are a careful career opportunity ranking assistant.

Student:
- Degree: {profile['degree']}
- University: {profile['university']}
- Semester: {profile['semester']}
- GPA: {profile['gpa']}
- Interests: {profile['interests']}
- Skills: {profile['skills']}
- Projects: {profile['projects']}

Rank these opportunities for this student. Do not invent eligibility, deadlines, funding,
or facts not present in the supplied text. Prefer official-looking sources and direct
opportunity pages. Return ONLY a valid JSON object with a key called "results". "results" must be an array. Each object must have:
index, match_score (0-100), type, summary, why_match, eligibility, deadline, location.
Keep summary and why_match concise. If a field is unknown, use "Not found".

Opportunities:
{json.dumps(compact, ensure_ascii=False)}
"""
    try:
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        if isinstance(data, dict):
            for key in ("results", "opportunities", "ranked"):
                if isinstance(data.get(key), list):
                    return data[key]
        if isinstance(data, list):
            return data
    except Exception:
        return None
    return None

def search_and_rank(profile, category, region, custom_query, max_results=10):
    queries = list(CATEGORY_QUERIES.get(category, CATEGORY_QUERIES["Everything"]))
    if custom_query.strip():
        queries.insert(0, custom_query.strip())

    if region == "Pakistan":
        queries = [q + " Pakistan" for q in queries]
    elif region == "International":
        queries = [q + " international" for q in queries]
    elif region == "Remote":
        queries = [q + " remote online" for q in queries]

    raw = _search_web(queries, max_results=max_results * 2)
    if not raw:
        return [{
            "id": _id("No results", "https://duckduckgo.com/"),
            "title": "No live results found",
            "url": "https://duckduckgo.com/",
            "summary": "The search provider returned no results. Try again or add a more specific search focus.",
            "why_match": "No opportunity could be evaluated.",
            "eligibility": "Not found",
            "deadline": "Not found",
            "location": "Not found",
            "type": category,
            "match_score": 0,
        }]

    for x in raw:
        x["id"] = _id(x["title"], x["url"])
        x["match_score"] = _rule_rank(x, profile)

    ai = _groq_rank(raw, profile)
    if ai:
        for a in ai:
            try:
                idx = int(a.get("index", -1))
            except Exception:
                continue
            if 0 <= idx < len(raw):
                raw[idx].update({
                    "match_score": int(a.get("match_score", raw[idx]["match_score"])),
                    "type": a.get("type", category),
                    "summary": a.get("summary", raw[idx]["body"][:300]),
                    "why_match": a.get("why_match", "Relevant to your profile."),
                    "eligibility": a.get("eligibility", "Not found"),
                    "deadline": a.get("deadline", "Not found"),
                    "location": a.get("location", "Not found"),
                })
    else:
        for x in raw:
            x.update({
                "type": category,
                "summary": x["body"][:350] if x["body"] else "Open the opportunity page for details.",
                "why_match": "Rule-based relevance score; add GROQ_API_KEY for AI ranking.",
                "eligibility": "Open official page to verify.",
                "deadline": "Open official page to verify.",
                "location": "See official page.",
            })

    # Remove obvious search/social pages when a direct-looking result exists.
    raw.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return raw[:max_results]
