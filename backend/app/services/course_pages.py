"""Course work (курсова робота / курсовий проєкт): the task sheet (ЗАВДАННЯ) and the
calendar plan (КАЛЕНДАРНИЙ ПЛАН) that follow the title page, as data — the .docx and
PDF builders only draw it. Everything comes from report.meta:

    course_type      "project" (курсовий проєкт, default) | "work" (курсова робота)
    task_sheet       include the task sheet and the calendar plan
    doc_code         позначення документа (title page, optional)
    specialty, year_of_study, semester, student_full_dative ("Петренку Олегу Олеговичу"),
    deadline, input_data, contents, graphics, issue_date
    calendar         [{"stage": "...", "deadline": "...", "note": "...", "sub": false}]
    abbreviations    "Термін – пояснення" lines (СКОРОЧЕННЯ ТА УМОВНІ ПОЗНАКИ)"""

SUB_LETTERS = "абвгдежиклмнпрстуфхцшщюя"


def report_meta(report) -> dict:
    meta = getattr(report, "meta", None)
    return meta if isinstance(meta, dict) else {}


def report_meta_value(report, key) -> str:
    value = report_meta(report).get(key)
    return str(value).strip() if value not in (None, False) else ""


def is_course(report) -> bool:
    return (getattr(report, "kind", "") or "") == "course"


def wants_task_sheet(report) -> bool:
    return is_course(report) and bool(report_meta(report).get("task_sheet"))


def course_words(report) -> dict:
    if report_meta(report).get("course_type") == "work":
        return {"title": "КУРСОВА РОБОТА", "task_title": "НА КУРСОВУ РОБОТУ", "genitive": "курсової роботи",
                "noun": "роботи", "finished": "закінченої роботи", "topic_hint": "(тема роботи)"}
    return {"title": "КУРСОВИЙ ПРОЄКТ", "task_title": "НА КУРСОВИЙ ПРОЄКТ", "genitive": "курсового проєкту",
            "noun": "проєкту", "finished": "закінченого проєкту", "topic_hint": "(тема проєкту)"}


def supervisors(report) -> list[str]:
    """Керівники: one per line of the teacher field, "посада Прізвище І. Б."; a single
    supervisor without a position line gets teacher_position in front."""
    lines = [l.strip() for l in (getattr(report, "teacher", "") or "").replace("\r\n", "\n").split("\n") if l.strip()]
    position = (getattr(report, "teacher_position", "") or "").strip()
    if len(lines) == 1 and position and not lines[0].startswith(position):
        lines = [f"{position} {lines[0]}"]
    return lines


def task_heading_lines(report) -> dict:
    m = report_meta(report)
    female = getattr(report, "student_gender", "m") == "f"
    student_name = (getattr(report, "student_name", "") or "").split("\n")[0].strip()
    return {
        "institution": (getattr(report, "institution", "") or "").upper(),
        "fields": [
            ("Факультет:", (getattr(report, "faculty", "") or "").strip()),
            ("Кафедра:", (getattr(report, "department", "") or "").strip()),
            ("Спеціальність:", str(m.get("specialty") or "").strip()),
        ],
        "course_line": [
            ("Курс ", False), (f"  {str(m.get('year_of_study') or '').strip()}  ", True),
            ("   група ", False), (f"  {(getattr(report, 'group', '') or '').strip()}  ", True),
            ("   семестр ", False), (f"  {str(m.get('semester') or '').strip()}  ", True),
        ],
        "student_label": "Студентці" if female else "Студентові",
        "student_full": str(m.get("student_full_dative") or "").strip() or student_name,
    }


def task_fields(report) -> list[tuple[str, str]]:
    m = report_meta(report)
    w = course_words(report)
    get = lambda k: str(m.get(k) or "").strip()
    return [
        (f"Тема {w['noun']}:", (getattr(report, "title", "") or "").strip()),
        (f"Термін здачі студентом {w['finished']}:", get("deadline")),
        (f"Вхідні дані до {w['noun']}:", get("input_data")),
        ("Зміст розрахунково-пояснювальної записки (перелік питань, які підлягають розробці):", get("contents")),
        ("Перелік графічного матеріалу (з точним визначенням обов’язкових креслень):", get("graphics")),
        ("Дата видачі завдання:", get("issue_date")),
    ]


def calendar_rows(report) -> list[dict]:
    """Stages numbered 1, 2, ...; sub-stages under a stage get "а)", "б)" and no number."""
    rows, n, sub = [], 0, 0
    for item in report_meta(report).get("calendar") or []:
        if not isinstance(item, dict) or not str(item.get("stage") or "").strip():
            continue
        stage = str(item["stage"]).strip()
        if item.get("sub"):
            letter = SUB_LETTERS[sub % len(SUB_LETTERS)]
            sub += 1
            if not stage[:2].rstrip().endswith(")"):
                stage = f"{letter}) {stage}"
            no = ""
        else:
            n += 1
            sub = 0
            no = str(n)
        rows.append({"no": no, "stage": stage, "sub": bool(item.get("sub")),
                     "deadline": str(item.get("deadline") or "").strip(), "note": str(item.get("note") or "").strip()})
    return rows


DEFAULT_CALENDAR = [
    {"stage": "Отримання завдання, вибір і узгодження теми", "sub": False},
    {"stage": "Аналіз предметної області та джерел", "sub": False},
    {"stage": "Основна частина: розробка, розрахунки, дослідження", "sub": False},
    {"stage": "Оформлення пояснювальної записки", "sub": False},
    {"stage": "Захист курсового проєкту", "sub": False},
]
