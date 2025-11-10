import csv
import json

def save_to_csv(vacancies, filename="vacancies.csv"):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "company", "salary", "link"])
        writer.writeheader()
        writer.writerows(vacancies)


def save_to_json(vacancies, filename="vacancies.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(vacancies, f, ensure_ascii=False, indent=2)