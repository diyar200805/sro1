
import json
from pathlib import Path
from datetime import date, datetime

DATA_FILE = Path("attendance.json")

STATUSES = {
    "1": "present",
    "2": "absent",
    "3": "late",
    "4": "excused",
}

STATUS_NAMES = {
    "present": "Присутствовал",
    "absent": "Отсутствовал",
    "late": "Опоздал",
    "excused": "Освобожден",
}

DEFAULT_DATA = {
    "students": [
        {"id": 1, "name": "Иванов Иван", "group": "ИС-101"},
        {"id": 2, "name": "Петрова Анна", "group": "ИС-101"},
        {"id": 3, "name": "Сидоров Максим", "group": "ИС-101"},
        {"id": 4, "name": "Ким Алия", "group": "ИС-101"},
    ],
    "attendance": []
}


def load_data():
    if not DATA_FILE.exists():
        save_data(DEFAULT_DATA)
        return json.loads(json.dumps(DEFAULT_DATA))

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Корневой объект должен быть словарем")

        if not isinstance(data.get("students"), list):
            raise ValueError("Некорректный список студентов")

        if not isinstance(data.get("attendance"), list):
            raise ValueError("Некорректный журнал посещаемости")

        student_ids = set()
        for student in data["students"]:
            if not isinstance(student, dict):
                raise ValueError("Некорректная запись студента")
            sid = student.get("id")
            name = student.get("name")
            group = student.get("group")
            if (type(sid) is not int or sid <= 0
                    or sid in student_ids
                    or not isinstance(name, str) or not name.strip()
                    or not isinstance(group, str) or not group.strip()):
                raise ValueError("Ошибка данных студента")
            student_ids.add(sid)

        seen = set()
        for record in data["attendance"]:
            if not isinstance(record, dict):
                raise ValueError("Некорректная запись посещения")
            sid = record.get("student_id")
            day = record.get("date")
            status = record.get("status")
            if (type(sid) is not int or sid not in student_ids
                    or not isinstance(day, str)
                    or not isinstance(status, str)
                    or status not in STATUS_NAMES):
                raise ValueError("Ошибка записи посещаемости")
            date.fromisoformat(day)
            key = (sid, day)
            if key in seen:
                raise ValueError("Обнаружены дубликаты посещаемости")
            seen.add(key)

        return data

    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Ошибка чтения данных: {error}")
        print("Создан новый журнал. Старый файл сохраните отдельно.")
        return json.loads(json.dumps(DEFAULT_DATA))


def save_data(data):
    temp_file = DATA_FILE.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    temp_file.replace(DATA_FILE)


def read_date():
    raw = input("Дата занятия (ГГГГ-ММ-ДД): ").strip()
    try:
        parsed = date.fromisoformat(raw)
        if parsed.isoformat() != raw:
            raise ValueError
        if parsed > date.today():
            raise ValueError("Будущая дата недопустима")
        return raw
    except ValueError as error:
        print(f"Некорректная дата: {error}")
        return None


def find_student(data, student_id):
    for student in data["students"]:
        if student["id"] == student_id:
            return student
    return None


def show_students(data):
    print("\n--- Список студентов ---")
    for student in data["students"]:
        print(
            f'{student["id"]}: {student["name"]} '
            f'({student["group"]})'
        )


def register_attendance(data):
    day = read_date()
    if day is None:
        return

    show_students(data)

    try:
        student_id = int(input("ID студента: ").strip())
    except ValueError:
        print("Ошибка: ID должен быть целым числом.")
        return

    student = find_student(data, student_id)
    if student is None:
        print("Студент не найден.")
        return

    print("1 — присутствовал")
    print("2 — отсутствовал")
    print("3 — опоздал")
    print("4 — освобожден")

    choice = input("Выберите статус: ").strip()
    if choice not in STATUSES:
        print("Ошибка: неизвестный статус.")
        return

    existing = next(
        (r for r in data["attendance"]
         if r["student_id"] == student_id
         and r["date"] == day),
        None
    )

    if existing:
        confirm = input(
            "Запись существует. Изменить статус? (д/н): "
        ).strip().lower()
        if confirm != "д":
            print("Изменение отменено.")
            return
        existing["status"] = STATUSES[choice]
    else:
        data["attendance"].append({
            "student_id": student_id,
            "date": day,
            "status": STATUSES[choice]
        })

    save_data(data)
    print("Посещаемость сохранена.")


def search_student(data):
    query = input("Введите ID или часть имени: ").strip().lower()
    if not query:
        print("Поисковый запрос не может быть пустым.")
        return

    results = [
        s for s in data["students"]
        if query == str(s["id"]) or query in s["name"].lower()
    ]

    if not results:
        print("Совпадений не найдено.")
        return

    for student in results:
        print(f'\n{student["id"]}: {student["name"]}')
        history = [
            r for r in data["attendance"]
            if r["student_id"] == student["id"]
        ]
        history.sort(key=lambda r: r["date"])

        if not history:
            print("Записей пока нет.")
        for record in history:
            print(
                f'{record["date"]}: '
                f'{STATUS_NAMES[record["status"]]}'
            )


def calculate_stats(data, student=None):
    records = data["attendance"]
    if student is not None:
        records = [
            r for r in records
            if r["student_id"] == student["id"]
        ]

    eligible = [
        r for r in records if r["status"] != "excused"
    ]
    attended = sum(
        r["status"] in ("present", "late")
        for r in eligible
    )
    absent = sum(r["status"] == "absent" for r in eligible)
    late = sum(r["status"] == "late" for r in eligible)

    percent = (
        attended / len(eligible) * 100
        if eligible else None
    )

    return len(eligible), attended, absent, late, percent


def show_statistics(data):
    print("\n--- Статистика ---")
    print("1 — вся группа")
    print("2 — отдельный студент")
    choice = input("Выбор: ").strip()

    if choice == "1":
        for student in data["students"]:
            total, attended, absent, late, percent = (
                calculate_stats(data, student)
            )
            value = f"{percent:.1f}%" if percent is not None else "нет данных"
            print(
                f'{student["name"]}: занятий {total}, '
                f'посещено {attended}, пропусков {absent}, '
                f'опозданий {late}, посещаемость {value}'
            )
    elif choice == "2":
        try:
            sid = int(input("ID студента: ").strip())
        except ValueError:
            print("ID должен быть целым числом.")
            return

        student = find_student(data, sid)
        if student is None:
            print("Студент не найден.")
            return

        total, attended, absent, late, percent = (
            calculate_stats(data, student)
        )
        value = f"{percent:.1f}%" if percent is not None else "нет данных"
        print(f'Студент: {student["name"]}')
        print(f"Занятий: {total}")
        print(f"Посещено: {attended}")
        print(f"Пропусков: {absent}")
        print(f"Опозданий: {late}")
        print(f"Посещаемость: {value}")
    else:
        print("Неизвестный пункт меню.")


def main():
    data = load_data()

    while True:
        print("\n=== Учет посещаемости студентов ===")
        print("1. Список студентов")
        print("2. Регистрация посещаемости")
        print("3. Поиск и история посещений")
        print("4. Статистика")
        print("0. Выход")

        choice = input("Выберите действие: ").strip()

        try:
            if choice == "1":
                show_students(data)
            elif choice == "2":
                register_attendance(data)
            elif choice == "3":
                search_student(data)
            elif choice == "4":
                show_statistics(data)
            elif choice == "0":
                print("Работа завершена.")
                break
            else:
                print("Введите номер пункта меню от 0 до 4.")
        except (OSError, ValueError, KeyError) as error:
            print(f"Операция не выполнена: {error}")


if __name__ == "__main__":
    main()
