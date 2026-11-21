"""Job feeds (JSON or RSS / Atom), configured in JOB_FEEDS (comma-separated URLs)."""
from __future__ import annotations

import html
import json
import os
import re
from urllib.parse import urlparse

import httpx

from src.logger import get_logger

log = get_logger("job_agent.search.feeds")
_CITY = re.compile(r"(الرياض|جدة|جده|الدمام|مكة|المدينة|الخبر|الظهران|الطائف|تبوك|أبها|ابها|بريدة|حائل|جازان|نجران|الأحساء|الجبيل|ينبع|riyadh|jeddah|dammam"
                   r"|makkah|madinah|khobar|dhahran|taif|tabuk|abha|jubail|yanbu)", re.I)
_REASON = "منشورة عبر مصدر وظائف ذوي الإعاقة المعتمد في سَند."


def _decode(value: str) -> str:
    value = re.sub(r"<!\[CDATA\[([\s\S]*?)\]\]>", r"\1", value)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _tag(xml: str, name: str) -> str:
    m = re.search(rf"<{name}[^>]*>([\s\S]*?)</{name}>", xml, re.I)
    return _decode(m.group(1)) if m else ""


def parse_feed(body: str, feed_url: str) -> list[dict]:
    host = urlparse(feed_url).hostname or "feed"
    trimmed = body.strip()
    if trimmed.startswith("<"):
        out = []
        for item in [m.group(0) for m in re.finditer(r"<(item|entry)\b[\s\S]*?</\1>", trimmed, re.I)][:200]:
            raw_title = _tag(item, "title")
            link = _tag(item, "link") or (m.group(1) if (m := re.search(r'<link[^>]*href="([^"]+)"', item, re.I)) else "")
            description = _tag(item, "description") or _tag(item, "summary") or _tag(item, "content")
            parts = re.split(r"\s+(?:-|–|—|\||at|لدى|في)\s+", raw_title, flags=re.I)
            title, company = parts[0], (parts[1] if len(parts) > 1 else "")
            where = m.group(0) if (m := _CITY.search(f"{raw_title} {description}")) else ""
            remote = bool(re.search(r"(عن بعد|عن بُعد|remote)", f"{raw_title} {description}", re.I))
            out.append({
                "title": title or raw_title, "english": "", "company": company or _tag(item, "author") or host,
                "location": "عن بُعد" if remote else (where or "غير محدد"), "mode": "عن بُعد" if remote else "حضوري", "salary": "",
                "description": description[:500], "skills": [], "sourceUrl": link, "sourceName": host,
                "postedAt": _tag(item, "pubDate") or _tag(item, "updated") or _tag(item, "published") or None, "deadline": None,
                "deafFriendlyReason": _REASON, "accommodations": [],
            })
        return out
    data = json.loads(trimmed)
    items = data if isinstance(data, list) else data.get("jobs", [])
    out = []
    for raw in items[:200]:
        def s(key: str) -> str:
            value = raw.get(key)
            return value if isinstance(value, str) else ""
        mode = s("mode")
        out.append({
            "title": s("title"), "english": s("english"), "company": s("company"), "location": s("location") or "غير محدد",
            "mode": "عن بُعد" if mode == "عن بُعد" or re.search("remote", mode, re.I) else "هجين" if mode == "هجين" or re.search("hybrid", mode, re.I) else "حضوري",
            "salary": s("salary"), "description": s("description"), "skills": [k for k in raw.get("skills", []) if isinstance(k, str)],
            "sourceUrl": s("url") or s("sourceUrl"), "sourceName": s("sourceName") or host, "postedAt": s("postedAt") or None,
            "deadline": s("deadline") or None, "deafFriendlyReason": s("deafFriendlyReason") or _REASON, "accommodations": [],
        })
    return out


def fetch_feeds() -> list[dict]:
    out = []
    for url in [u.strip() for u in (os.getenv("JOB_FEEDS") or "").split(",") if u.strip()]:
        try:
            response = httpx.get(url, timeout=20, headers={"user-agent": "SanadJobsAgent/1.0",
                                                           "accept": "application/json, application/rss+xml, application/atom+xml, text/xml"})
            response.raise_for_status()
            out.extend(parse_feed(response.text, url))
        except Exception as exc:  # noqa: BLE001 - one feed failing must not stop the others
            log.warning("[FAIL]  feed %s -> %s", urlparse(url).hostname, type(exc).__name__)
    return out
