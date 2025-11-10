import requests
from bs4 import BeautifulSoup

BASE = "https://weworkremotely.com"

def _normalize_text(value, max_len=300):
    if value is None: return "—"
    s = str(value).replace("\r"," ").replace("\n"," ").replace("\t"," ").strip()
    return s[:max_len] + ("…" if len(s) > max_len else "")

def search_weworkremotely(query="", limit=100):
    """
    Простой парсер: возвращает список dict {title, company, salary, link}
    """
    url = f"{BASE}/remote-jobs/search?term={requests.utils.quote(query)}" if query else f"{BASE}/remote-jobs"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"[wework] network error: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    # примерная структура: секции с классом 'jobs' -> li > a
    jobs = soup.select("section.jobs article ul li") or soup.select("li.feature") or []
    for li in jobs:
        a = li.find("a", href=True)
        if not a: continue
        link = BASE + a["href"] if a["href"].startswith("/") else a["href"]
        title_el = li.select_one(".title") or li.find("span", class_="title")
        company_el = li.select_one(".company") or li.find("span", class_="company")
        title = _normalize_text(title_el.get_text() if title_el else a.get_text())
        company = _normalize_text(company_el.get_text() if company_el else "")
        salary = "—"
        results.append({"title": title, "company": company, "salary": salary, "link": link})
        if len(results) >= limit:
            break
    return results
