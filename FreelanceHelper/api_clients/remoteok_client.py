import requests
import re

API_URL = "https://remoteok.com/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

_nonprint_re = re.compile(r'[\r\n\t]+')

def _normalize_text(value, max_len=500):
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        s = " ".join(map(str, value))
    else:
        s = str(value)
    s = _nonprint_re.sub(" ", s).strip()
    if len(s) > max_len:
        s = s[:max_len] + "…"
    return s

def _safe_url(u):
    if not u:
        return "-"
    u = str(u).strip()
    if u.startswith("//"):
        u = "https:" + u
    if u.startswith("/"):
        u = "https://remoteok.com" + u
    if not (u.startswith("http://") or u.startswith("https://")):
        return "-"
    return u

def _matches_query(job_dict, q):
    if not q:
        return True
    q = q.lower()
    # проверяем в title, company, tags, description
    title = _normalize_text(job_dict.get("position") or job_dict.get("title") or "")
    company = _normalize_text(job_dict.get("company") or "")
    tags = job_dict.get("tags") or job_dict.get("tag") or job_dict.get("keywords") or ""
    # tags могут быть списком или строкой
    if isinstance(tags, (list, tuple)):
        tags = " ".join(map(str, tags))
    tags = _normalize_text(tags)
    description = _normalize_text(job_dict.get("description") or "")
    combined = f"{title} {company} {tags} {description}".lower()
    return q in combined

def search_remoteok(query=""):
    try:
        resp = requests.get(API_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[remoteok] network error: {e}")
        return []

    # лог типа контента для диагностики
    content_type = resp.headers.get("Content-Type", "")
    if "application/json" not in content_type.lower():
        print(f"[remoteok] warning: Content-Type={content_type}")

    try:
        data = resp.json()
    except Exception as e:
        print(f"[remoteok] json decode error: {e}")
        return []

    if not isinstance(data, list):
        print("[remoteok] unexpected json structure (expected list)")
        return []

    print(f"[remoteok] raw items count: {len(data)}")

    results = []
    for i, job in enumerate(data[1:], start=1):
        if not isinstance(job, dict):
            continue

        # фильтр: включаем запись, если query пустой или найдено в ключевых полях
        if not _matches_query(job, query):
            continue

        title = _normalize_text(job.get("position") or job.get("title") or "—", max_len=300) or "—"
        company = _normalize_text(job.get("company") or "—", max_len=200) or "—"
        salary = _normalize_text(job.get("salary") or job.get("payment") or "—", max_len=200) or "—"
        link = _safe_url(job.get("url") or job.get("apply_url") or job.get("company_url"))

        results.append({
            "title": title,
            "company": company,
            "salary": salary,
            "link": link,
            "raw": {k: _normalize_text(v, max_len=200) for k, v in list(job.items())[:10]}
        })

    print(f"[remoteok] parsed results count: {len(results)}")
    # для отладки: показать первые пару заголовков если query пустой
    if not query and results:
        print("[remoteok] sample titles:", [r["title"] for r in results[:5]])
    return results
