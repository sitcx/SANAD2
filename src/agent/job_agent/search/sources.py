"""Job sources that work without any AI key: public job-search and career-board APIs that allow automated access.

Each CV gets its own search plan (its roles and skills in English, its level); every result is mapped to Sanad's
job shape, filtered and ranked for the CV. Not used: LinkedIn / SmartRecruiters (robots.txt forbids automated
access) and Jadarat / Qiwa (no public API; we do not bypass protections).
"""
from __future__ import annotations

import html
import os
import re
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from src.agent.job_agent.ats.experience import piece_kind
from src.agent.job_agent.ats.matching import match_job, title_tokens
from src.agent.job_agent.ats.skills import canonical_skill, find_skills, skill_group
from src.agent.text.arabic import normalize_arabic, tokenize, unique_strings
from src.logger import get_logger

log = get_logger("job_agent.search.sources")
USER_AGENT = "SanadJobsAgent/1.0"
MAX_AGE_DAYS = 120
Fetch = Callable[[str, dict], object]   # (url, headers) -> parsed JSON; tests inject a fake

_cache: dict[str, tuple[float, object]] = {}


def _http_json(url: str, headers: dict) -> object:
    response = httpx.get(url, headers={"user-agent": USER_AGENT, "accept": "application/json", **headers}, timeout=12, follow_redirects=True)
    response.raise_for_status()
    return response.json()


def _get_json(url: str, fetch: Fetch, headers: dict | None = None, cache_hours: float = 0) -> object:
    hit = _cache.get(url)
    if hit and cache_hours and time.time() - hit[0] < cache_hours * 3600:
        return hit[1]
    body = fetch(url, headers or {})
    if cache_hours:
        _cache[url] = (time.time(), body)
    return body


def strip_html(text: str) -> str:
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    text = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", ". ", text, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", re.sub(r"\s*\.\s*\.+", ".", text)).strip()


def _clip(text: str, limit: int) -> str:
    return f"{re.sub(r'\s\S*$', '', text[:limit - 1])}…" if len(text) > limit else text


_CITIES_AR = [(r"riyadh", "الرياض"), (r"jedd?ah|jiddah", "جدة"), (r"dammam", "الدمام"), (r"khobar", "الخبر"), (r"dhahran", "الظهران"),
              (r"makkah|mecca", "مكة"), (r"madinah|medina", "المدينة"), (r"taif", "الطائف"), (r"tabuk", "تبوك"), (r"abha", "أبها"),
              (r"buraid|buraydah|qassim", "بريدة"), (r"\bhail\b|ha'il", "حائل"), (r"jazan|jizan", "جازان"), (r"najran", "نجران"),
              (r"hofuf|ahsa", "الأحساء"), (r"jubail", "الجبيل"), (r"yanbu", "ينبع"), (r"neom", "نيوم"), (r"khamis", "خميس مشيط"),
              (r"qatif", "القطيف"), (r"kharj", "الخرج"), (r"sakaka|jouf", "سكاكا"), (r"arar", "عرعر"), (r"baha", "الباحة"), (r"ula\b", "العلا")]


def city_ar(place: str) -> str:
    for pattern, name in _CITIES_AR:
        if re.search(pattern, place, re.I | re.ASCII):
            return name
    return "السعودية" if re.search(r"saudi|ksa", place, re.I) else (place.strip() or "السعودية")


# Phone or call-centre work depends on hearing: left out for sign-language candidates (blind candidates can do it).
VOICE_HEAVY = re.compile(r"(call cent(er|re)|telesales|tele-?marketing|cold call|phone support|phone sales|voice process|inbound calls|outbound calls"
                         r"|answering calls|switchboard|radio operator|مركز اتصال|مركز الاتصال|مبيعات هاتفية|الرد على المكالمات|تسويق هاتفي)", re.I)
_WRITTEN_WORK = re.compile(r"(data|analyst|developer|engineer|designer|accountant|software|it |cyber|ai |machine learning|content|writer|editor|research"
                           r"|finance|audit|admin|hr |marketing|bi |quality|tester|qa |محلل|مطور|مهندس|مصمم|محاسب|مدقق|باحث|كاتب|مسوق)", re.I)


def _accessibility_reason(remote: bool, title: str) -> str:
    if remote:
        return "عمل عن بُعد يُنجز بالتواصل الكتابي والأدوات الرقمية، ولا يشترط الإعلان مكالمات هاتفية."
    if _WRITTEN_WORK.search(f"{title} "):
        return ("مهام الدور مكتبية ورقمية يمكن أداؤها بالتواصل الكتابي أو الصوتي. اطلب التسهيلات (مترجم لغة إشارة أو قارئ شاشة) عند التقديم.")
    return "لا يشترط الإعلان عملًا يعتمد على حاسة واحدة. اطلب التسهيلات (مترجم لغة إشارة أو قارئ شاشة) عند التقديم."


def posting(*, title: str, company: str, place: str, remote: bool, description: str, url: str, source_name: str,
            posted_at: str | None, hybrid: bool = False, requirements: str = "", salary: str = "") -> dict:
    """One result in Sanad's job shape. Required skills come from the title and requirements, not the company blurb."""
    text = f"{title}. {requirements}" if len(requirements) > 80 else f"{title}. {description}"
    summary, reqs = _clip(description, 330), (_clip(requirements, 240) if requirements else "")
    latin = bool(re.search("[a-z]", title, re.I)) and not re.search("[ء-ي]", title)
    return {
        "title": _clip(title.strip(), 120), "english": _clip(title.strip(), 120) if latin else "", "company": company.strip(),
        "location": "عن بُعد" if remote else city_ar(place), "mode": "عن بُعد" if remote else "هجين" if hybrid else "حضوري",
        "salary": salary, "description": f"{summary} المتطلبات: {reqs}" if reqs else summary,
        "skills": find_skills(text)[:10], "sourceUrl": url, "sourceName": source_name, "postedAt": posted_at, "deadline": None,
        "deafFriendlyReason": _accessibility_reason(remote, title), "accommodations": [],
    }


_SAUDI = re.compile(r"(saudi|ksa|riyadh|jedd?ah|dammam|khobar|dhahran|makkah|madinah|jubail|yanbu|neom|السعودية|الرياض)", re.I)
_OPEN_TO_SAUDI = re.compile(r"(worldwide|anywhere|global|saudi|ksa|middle east|mena|gcc|emea|gulf)", re.I)


class NeedsKey(Exception):
    pass


def _workable(plan: dict, fetch: Fetch) -> list[dict]:
    out = []
    for query in plan["queries"][:5]:
        body = _get_json(f"https://jobs.workable.com/api/v1/jobs?query={quote(query)}&location={quote('Saudi Arabia')}", fetch, cache_hours=3)
        for job in (body or {}).get("jobs", []):
            if job.get("state") and job["state"] != "published":
                continue
            remote = job.get("workplace") == "remote"
            if not remote and not _SAUDI.search((job.get("location") or {}).get("countryName") or ""):
                continue
            out.append(posting(title=job.get("title", ""), company=(job.get("company") or {}).get("title", ""), place=(job.get("location") or {}).get("city", ""),
                               remote=remote, hybrid=job.get("workplace") == "hybrid", url=job.get("url", ""), source_name="Workable",
                               description=strip_html(job.get("description") or job.get("socialSharingDescription") or ""),
                               requirements=strip_html(job.get("requirementsSection") or ""), posted_at=job.get("created")))
    return out


DEFAULT_JOB_BOARDS = "greenhouse:tamara:Tamara,greenhouse:careem:Careem,ashby:leantech:Lean Technologies"


def _job_boards() -> list[dict]:
    """JOB_BOARDS=greenhouse:slug:Company,ashby:slug:Company (official company career boards)."""
    boards = []
    for item in (os.getenv("JOB_BOARDS") or DEFAULT_JOB_BOARDS).split(","):
        parts = [p.strip() for p in item.split(":")]
        if len(parts) >= 3 and parts[0] in ("greenhouse", "ashby"):
            boards.append({"platform": parts[0], "slug": parts[1], "company": ":".join(parts[2:])})
    return boards


def _career_boards(plan: dict, fetch: Fetch) -> list[dict]:
    out = []
    for board in _job_boards():
        if board["platform"] == "greenhouse":
            body = _get_json(f"https://boards-api.greenhouse.io/v1/boards/{quote(board['slug'])}/jobs?content=true", fetch, cache_hours=6)
            for job in (body or {}).get("jobs", []):
                place = (job.get("location") or {}).get("name", "")
                remote = bool(re.search("remote", place, re.I)) and bool(_OPEN_TO_SAUDI.search(place))
                if not _SAUDI.search(place) and not remote:
                    continue
                out.append(posting(title=job.get("title", ""), company=board["company"], place=place, remote=remote, url=job.get("absolute_url", ""),
                                   description=strip_html(job.get("content") or ""), source_name=f"صفحة توظيف {board['company']}",
                                   posted_at=job.get("first_published") or job.get("updated_at")))
        else:
            body = _get_json(f"https://api.ashbyhq.com/posting-api/job-board/{quote(board['slug'])}", fetch, cache_hours=6)
            for job in (body or {}).get("jobs", []):
                places = " · ".join([job.get("location") or "", *((s or {}).get("location") or "" for s in job.get("secondaryLocations") or [])])
                remote = bool(job.get("isRemote")) and bool(_OPEN_TO_SAUDI.search(places))
                if not _SAUDI.search(places) and not remote:
                    continue
                out.append(posting(title=job.get("title", ""), company=board["company"], place=places, remote=remote, hybrid=job.get("workplaceType") == "Hybrid",
                                   description=job.get("descriptionPlain") or "", url=job.get("jobUrl") or job.get("applyUrl") or "",
                                   source_name=f"صفحة توظيف {board['company']}", posted_at=job.get("publishedAt")))
    return out


def _remotive(plan: dict, fetch: Fetch) -> list[dict]:
    out = []
    for query in plan["queries"][:2]:   # Remotive asks for few requests a day: results are cached
        body = _get_json(f"https://remotive.com/api/remote-jobs?search={quote(query)}", fetch, cache_hours=6)
        for job in (body or {}).get("jobs", []):
            if not _OPEN_TO_SAUDI.search(job.get("candidate_required_location") or ""):
                continue
            out.append(posting(title=job.get("title", ""), company=job.get("company_name", ""), place="", remote=True, url=job.get("url", ""),
                               description=strip_html(job.get("description") or ""), source_name="Remotive", posted_at=job.get("publication_date"),
                               salary=job.get("salary") or ""))
    return out


def _jobicy(plan: dict, fetch: Fetch) -> list[dict]:
    out = []
    for query in plan["queries"][:2]:
        body = _get_json(f"https://jobicy.com/api/v2/remote-jobs?count=30&tag={quote(query)}", fetch, cache_hours=6)
        for job in (body or {}).get("jobs", []):
            if not _OPEN_TO_SAUDI.search(job.get("jobGeo") or ""):
                continue
            out.append(posting(title=job.get("jobTitle", ""), company=job.get("companyName", ""), place="", remote=True, url=job.get("url", ""),
                               description=strip_html(job.get("jobDescription") or job.get("jobExcerpt") or ""), source_name="Jobicy",
                               posted_at=job.get("pubDate")))
    return out


def _himalayas(plan: dict, fetch: Fetch) -> list[dict]:
    out = []
    for query in plan["queries"][:2]:
        body = _get_json(f"https://himalayas.app/jobs/api/search?q={quote(query)}&limit=20", fetch, cache_hours=6)
        for job in (body or {}).get("jobs", []):
            allowed = job.get("locationRestrictions") or []
            if allowed and not any(re.search("saudi", c, re.I) for c in allowed):
                continue
            pub = job.get("pubDate")
            out.append(posting(title=job.get("title", ""), company=job.get("companyName", ""), place="", remote=True,
                               url=job.get("applicationLink") or job.get("guid") or "", description=strip_html(job.get("description") or job.get("excerpt") or ""),
                               source_name="Himalayas", posted_at=datetime.fromtimestamp(pub, timezone.utc).isoformat() if pub else None))
    return out


def _remote_ok(plan: dict, fetch: Fetch) -> list[dict]:
    body = _get_json("https://remoteok.com/api", fetch, cache_hours=6)
    words = {w for role in plan["roles"] for w in tokenize(role) if len(w) > 2}
    out = []
    for job in (body[1:] if isinstance(body, list) else []):
        location = (job.get("location") or "").strip()
        if not job.get("position") or not job.get("url"):
            continue
        if location and not re.fullmatch(r"remote|worldwide|anywhere", location, re.I) and not _OPEN_TO_SAUDI.search(location):
            continue
        if not any(w in words for w in tokenize(f"{job['position']} {' '.join(job.get('tags') or [])}")):
            continue
        # Remote OK's terms: link back to the job on Remote OK and name it as the source.
        out.append(posting(title=job["position"], company=job.get("company") or "", place="", remote=True, url=job["url"],
                           description=strip_html(job.get("description") or ""), source_name="Remote OK", posted_at=job.get("date")))
    return out


_HIRING = re.compile(r"(وظيف|وظائف|توظيف|مطلوب|نوظف|فرصة عمل|hiring|we are hiring|job opening|vacanc|join our team)", re.I)


def _x_search(plan: dict, fetch: Fetch) -> list[dict]:
    token = os.getenv("X_BEARER_TOKEN")
    if not token:
        raise NeedsKey()
    out = []
    for role in plan["roles"][:2]:
        query = f"({role}) (وظيفة OR وظائف OR توظيف OR hiring) (السعودية OR الرياض OR جدة OR الدمام OR Saudi OR KSA OR Riyadh) has:links -is:retweet"
        body = _get_json("https://api.x.com/2/tweets/search/recent?max_results=25&tweet.fields=created_at,entities,author_id&expansions=author_id"
                         f"&user.fields=name,username&query={quote(query)}", fetch, {"authorization": f"Bearer {token}"}, cache_hours=1) or {}
        users = {u["id"]: u for u in (body.get("includes") or {}).get("users", [])}
        for tweet in body.get("data", []):
            if not _HIRING.search(tweet.get("text", "")):
                continue
            user = users.get(tweet.get("author_id", ""), {})
            links = [u.get("expanded_url", "") for u in (tweet.get("entities") or {}).get("urls", [])]
            link = next((u for u in links if u and not re.search(r"(^https?://)?(www\.)?(x|twitter)\.com/", u, re.I)), None)
            first = re.sub(r"https?://\S+", "", re.split(r"[.!؟?|]", tweet["text"])[0]).replace("#", "").strip()
            out.append(posting(title=_clip(first or role, 90), company=user.get("name", "X"), place=tweet["text"],
                               remote=bool(re.search(r"(عن بعد|عن بُعد|remote)", tweet["text"], re.I)),
                               description=re.sub(r"https?://\S+", "", tweet["text"]).strip(),
                               url=link or f"https://x.com/{user.get('username', 'i')}/status/{tweet['id']}", source_name="X (تويتر)",
                               posted_at=tweet.get("created_at")))
    return out


CONNECTORS: list[tuple[str, Callable[[dict, Fetch], list[dict]]]] = [
    ("Workable", _workable), ("صفحات التوظيف الرسمية للشركات", _career_boards), ("X (تويتر)", _x_search),
    ("Remotive", _remotive), ("Jobicy", _jobicy), ("Himalayas", _himalayas), ("Remote OK", _remote_ok),
]

# ---------------------------------------------------------------- the search plan for one CV

_TITLES_EN = [
    (r"محلل بيانات", "Data Analyst"), (r"محاسب", "Accountant"), (r"مدقق|مراجع حسابات", "Auditor"), (r"موارد بشريه|توظيف", "HR Specialist"),
    (r"مدخل بيانات|ادخال بيانات", "Data Entry Clerk"), (r"سكرتير|مساعد اداري|منسق اداري|موظف اداري", "Administrative Assistant"),
    (r"تجربه مستخدم|واجهات", "UI/UX Designer"), (r"مصمم جرافيك", "Graphic Designer"), (r"مصمم", "Designer"), (r"مطور|مبرمج", "Software Developer"),
    (r"عمليات", "Operations Specialist"), (r"مهندس مدني", "Civil Engineer"), (r"مهندس كهرب", "Electrical Engineer"),
    (r"مهندس ميكانيك", "Mechanical Engineer"), (r"مهندس", "Engineer"), (r"ممرض", "Nurse"), (r"صيدل", "Pharmacist"), (r"طبيب", "Doctor"),
    (r"معلم|مدرس", "Teacher"), (r"مدرب", "Trainer"), (r"تسويق", "Marketing Specialist"), (r"خدمه العملاء|دعم العملاء", "Customer Support Specialist"),
    (r"مبيعات", "Sales Representative"), (r"امن سيبراني", "Cybersecurity Analyst"), (r"ذكاء اصطناعي", "AI Engineer"), (r"فني", "Technician"),
    (r"مشرف", "Supervisor"), (r"مستودع|مخازن|لوجست", "Logistics Coordinator"), (r"مشتريات", "Procurement Specialist"), (r"قانوني|محامي", "Legal Advisor"),
]
_CLEAN_TITLE = re.compile(r"\b(trainee|intern|internship|co-?op|apprentice|junior|senior|sr\.?|jr\.?)\b|\([^)]*\)|\s[-–—|]\s.*$|,.*$", re.I | re.ASCII)


def search_plan(profile: dict) -> dict:
    """Search phrases from the CV reading, in English (what job sites index), for any field and level."""
    def latin(value: str) -> bool:
        return bool(re.search("[a-z]", value, re.I)) and not re.search("[ء-ي]", value)

    def cleaned(value: str) -> str:
        return re.sub(r"\s+", " ", _CLEAN_TITLE.sub(" ", value)).strip()

    def english(value: str) -> str:
        if latin(value):
            return cleaned(value)
        key = normalize_arabic(value)
        return next((en for pattern, en in _TITLES_EN if re.search(pattern, key)), "")

    roles = unique_strings([r for r in [*map(english, profile.get("jobTitles", [])), *map(english, profile.get("suggestedRoles", [])),
                                        *(cleaned(k) for k in profile.get("searchKeywords", []) if latin(k) and piece_kind(k) == "title")]
                            if len(r) >= 3 and piece_kind(r) == "title"], 4)
    tools = [s for s in profile.get("skills", []) if latin(s) and skill_group(s) != "soft"][:2]
    years = profile.get("yearsExperience") or 0
    graduate = "حديث" in (profile.get("careerLevel") or "") or years < 1
    return {"roles": roles, "queries": unique_strings([*roles, *tools, *(["Graduate Program"] if graduate else [])], 7),
            "graduate": graduate, "senior": years >= 8}


def search_sources(plan: dict, *, fetch: Fetch | None = None, mode: str = "sign", now: datetime | None = None) -> dict:
    """Runs every connector in parallel; keeps fresh, unique postings with a valid link."""
    fetch = fetch or _http_json
    now = now or datetime.now(timezone.utc)

    def run(name: str, connector: Callable) -> tuple[list[dict], dict]:
        try:
            found = connector(plan, fetch)
            return found, {"source": name, "status": "results" if found else "no_results",
                           "note": f"{len(found)} إعلانًا" if found else "لا إعلانات مطابقة لعبارات البحث", "count": len(found)}
        except NeedsKey:
            return [], {"source": name, "status": "needs_key", "note": "منصة X لا تسمح بالبحث إلا بمفتاح X API (X_BEARER_TOKEN)", "count": 0}
        except Exception as exc:  # noqa: BLE001 - one source failing must not stop the others
            log.warning("[FAIL]  source %s -> %s", name, type(exc).__name__)
            return [], {"source": name, "status": "unreachable", "note": f"تعذّر الوصول ({type(exc).__name__})", "count": 0}

    with ThreadPoolExecutor(max_workers=len(CONNECTORS)) as pool:
        settled = list(pool.map(lambda item: run(*item), CONNECTORS))

    def fresh(posted_at: str | None) -> bool:
        try:
            when = datetime.fromisoformat((posted_at or "").replace("Z", "+00:00"))
        except ValueError:
            return True
        when = when if when.tzinfo else when.replace(tzinfo=timezone.utc)
        return (now - when).days <= MAX_AGE_DAYS

    seen: set[str] = set()
    postings = []
    for found, _ in settled:
        for item in found:
            if not (item["title"] and item["company"] and re.match(r"https?://", item["sourceUrl"]) and fresh(item["postedAt"])):
                continue
            if mode == "sign" and VOICE_HEAVY.search(f"{item['title']} {item['description']}"):
                continue
            keys = [item["sourceUrl"].split("?")[0].lower(), f"{normalize_arabic(item['title'])}|{normalize_arabic(item['company'])}"]
            if any(k in seen for k in keys):
                continue
            seen.update(keys)
            postings.append(item)
    return {"postings": postings, "reports": [report for _, report in settled], "fetched": sum(len(found) for found, _ in settled)}


_SENIOR_TITLE = re.compile(r"\b(senior|sr\.?|lead|principal|head|director|manager|chief|vp|vice president|staff)\b|مدير|رئيس", re.I | re.ASCII)
_ENTRY_TITLE = re.compile(r"\b(intern|internship|trainee|junior|entry[- ]level|graduate)\b|متدرب", re.I | re.ASCII)
_GENERIC = {"Excel", "Microsoft Office", "Word", "PowerPoint", "Outlook وTeams", "Google Workspace", "ERP", "إعداد التقارير", "الطباعة السريعة"}


def rank_for_candidate(postings: list[dict], profile: dict, cv_text: str, plan: dict, limit: int = 30) -> list[dict]:
    """Keeps postings that really fit: right level, a real skill in common (or the same kind of role), match >= 40%."""
    role_words = {t for title in [*plan["roles"], *profile.get("jobTitles", []), *profile.get("suggestedRoles", [])] for t in title_tokens(title)}
    ranked = []
    for item in postings:
        if (plan["graduate"] and _SENIOR_TITLE.search(item["title"])) or (plan["senior"] and _ENTRY_TITLE.search(item["title"])):
            continue
        match = match_job(profile, item, cv_text)
        same_role = any(t in role_words for t in title_tokens(item["title"]))
        real_skills = any(skill_group(s) != "soft" and canonical_skill(s) not in _GENERIC for s in match["matchedSkills"])
        if match["score"] >= 40 and (same_role or real_skills):
            ranked.append({"item": item, "match": match, "rank": match["score"] + (12 if same_role else 0)})
    return sorted(ranked, key=lambda e: -e["rank"])[:limit]
