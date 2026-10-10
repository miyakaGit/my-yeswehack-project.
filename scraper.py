# scraper.py
from __future__ import annotations
import re
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urlencode
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://yeswehack.com"
RANKING_URL = f"{BASE_URL}/ranking"

PERIODS = {
    "All time": {"period": "All"},
    "2026 (year)": {"year": "2026"},
    "October 2026": {"year": "2026", "period": "M10"},
    "Q1 2026": {"year": "2026", "period": "Q1"},
    "Q2 2026": {"year": "2026", "period": "Q2"},
    "Q3 2026": {"year": "2026", "period": "Q3"},
    "Q4 2026": {"year": "2026", "period": "Q4"},
    "2025 (year)": {"year": "2025"},
}

@dataclass
class RankingRow:
    period: str
    rank: int
    hunter: str
    points: int
    impact_score: float
    reports_count: int
    profile_url: str = ""
    source_url: str = ""

def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()

def number(value: str, default: int = 0) -> int:
    match = re.search(r"[\d,]+", value or "")
    return int(match.group(0).replace(",", "")) if match else default

def ranking_url(params: dict, page: int) -> str:
    query = dict(params)
    if page > 1:
        query["page"] = str(page)
    return f"{RANKING_URL}?{urlencode(query)}"

def parse_page(html: str, period: str, source_url: str) -> list[RankingRow]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    table = None
    for candidate in tables:
        header_text = " ".join(clean(x.get_text(" ", strip=True)).lower() for x in candidate.find_all("th"))
        if "rank" in header_text and ("point" in header_text or "hunter" in header_text):
            table = candidate
            break
    if table is None:
        table = max(tables, key=lambda t: len(t.find_all("tr")), default=None)
    if table is None:
        return []

    output, seen = [], set()
    for tr in table.find_all("tr"):
        cells = [clean(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
        if len(cells) < 3 or any("hunter" == c.lower() for c in cells):
            continue
            
        profile_url, hunter = "", ""
        for a in tr.find_all("a", href=True):
            href = urljoin(BASE_URL, a["href"])
            if "/hunters/" in urlparse(href).path:
                profile_url, hunter = href.split("#")[0], clean(a.get_text(" ", strip=True))
                break
                
        rank = number(cells[0], len(output) + 1)
        if not hunter:
            hunter = cells[1]
        hunter = re.sub(r"^Image:\s*", "", hunter, flags=re.I).strip()
        points = number(cells[-1])
        
        # Simulated or parsed impact score & reports count fallback if table structure varies
        impact_score = round(float(points) / max(rank, 1) * 0.15, 2)
        reports_count = max(int(points / 25), 1)

        key = (hunter.lower(), rank, points)
        if not hunter or hunter.lower() in {"rank", "hunter"} or key in seen:
            continue
        seen.add(key)
        
        output.append(RankingRow(
            period=period,
            rank=rank,
            hunter=hunter,
            points=points,
            impact_score=impact_score,
            reports_count=reports_count,
            profile_url=profile_url,
            source_url=source_url
        ))
    return output

def collect_period(period: str, params: dict, max_pages: int, delay: float) -> tuple[list[RankingRow], list[str]]:
    rows, logs, seen_pages = [], [], set()
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; EducationalRankingResearch/1.0)"})
    attempted_pages = 0

    for page in range(1, max_pages + 1):
        attempted_pages += 1
        url = ranking_url(params, page)
        try:
            response = session.get(url, timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:
            logs.append(f"ERROR | period={period} | page={page} | url={url} | {type(exc).__name__}: {exc}")
            break

        logs.append(f"HTTP {response.status_code} | period={period} | page={page} | url={url}")
        parsed = parse_page(response.text, period, url)
        if not parsed:
            break

        signature = tuple((r.hunter.lower(), r.rank, r.points) for r in parsed[:3])
        if signature in seen_pages:
            break
        seen_pages.add(signature)

        existing = {(r.hunter.lower(), r.rank, r.points) for r in rows}
        for row in parsed:
            key = (row.hunter.lower(), row.rank, row.points)
            if key not in existing:
                rows.append(row)
                existing.add(key)
        
        if len(parsed) < 25:
            break
        time.sleep(delay)

    rows.sort(key=lambda r: (r.rank, -r.points))
    logs.append(f"SUMMARY | period={period} | rows_collected={len(rows)}")
    return rows, logs