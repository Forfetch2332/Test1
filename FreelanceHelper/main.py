from api_clients.hh_client import search_vacancies
from storage import save_to_csv, save_to_json

def main():
    query = input("Enter search query: ")
    area = int(input("Enter area (1 - Moscow, 2 - Spb, 16 - Belarus): "))

    vacancies = search_vacancies(query, area=area, pages=2)
    print(f"Found {len(vacancies)} vacancies")
    for v in vacancies:
        print(f"- {v['title']} | {v['company']} | {v['salary']}")
        print(f"{v['link']}")

    save_to_json(vacancies)
    save_to_csv(vacancies)
    print("Save results to results.csv and results.json")

if __name__ == "__main__":
    main()