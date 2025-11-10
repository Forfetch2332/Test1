from hh_api import search_vacancies
from storage import save_to_csv, save_to_json

if __name__ == "__main__":
    query = input("Введите поисковый запрос: ")
    area = input("Введите код региона (1 - Москва, 2 - СПб, 16 - Беларусь): ")
    area = int(area) if area.isdigit() else 1

    vacancies = search_vacancies(query, area=area, pages=2)
    print(f"Найдено {len(vacancies)} вакансий.")
    for v in vacancies:
        print(f"- {v['title']} | {v['company']} | {v['salary']}")
        print(f"  {v['link']}")

    save_to_csv(vacancies)
    save_to_json(vacancies)
    print("Результаты сохранены в vacancies.csv и vacancies.json")