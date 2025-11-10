import requests

def search_vacancies(query, area=1, pages=1):
    results = []
    for page in range(pages):
        url = f"https://api.hh.ru/vacancies?text={query}&area={area}&page={page}"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("items", []):
            title = item.get("name")
            company = item.get("employer", {}).get("name")
            salary = item.get("salary", {})
            if salary:
                salary_text = f"{salary.get('from', '')}–{salary.get('to', '')} {salary.get('currency', '')}"
            else:
                salary_text = "—"
            link = item.get("alternate_url")

            results.append({
                "title": title,
                "company": company,
                "salary": salary_text,
                "link": link
            })
    return results