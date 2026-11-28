"""Title page templates — the only place that knows how a title page looks.

A template is data, not code: the .docx, PDF and LaTeX builders (and the browser preview,
which gets the same JSON from GET /templates) draw it with one small set of elements:

    {"t": "line",  "text": "Кафедра {department}", "align": "center", "size": 14, "bold": False,
                   "optional": True}          # optional: dropped when its placeholders are empty
    {"t": "blank", "n": 2}
    {"t": "field", "label": "на тему:", "value": "{title}", "hint": "(тема реферату)",
                   "repeat": "students"}      # underlined to the right margin; repeat: one per student
                                              # ({student}) or per supervisor ({supervisor});
                                              # "repeat_label": the label on every row
    {"t": "columns", "left": [...lines], "right": [...lines]}   # "{students}" = one line per student
    {"t": "push"}                             # what follows goes to the bottom of the page

Placeholders are report fields ({title}, {institution}, {group}, ...) plus words that depend
on gender / number, defined per template in "words" ({did} -> Виконав / Виконала / Виконали).
A new institution type or language (e.g. English) is a new entry here."""
import re
from datetime import datetime

from app.services.course_pages import course_words, report_meta_value, supervisors

MINISTRY_UA = "Міністерство освіти і науки України"

# Report fields a title page may show (the browser preview makes them editable in place)
FIELDS = ("ministry", "institution", "city", "faculty", "department", "discipline", "title",
          "group", "teacher", "teacher_position", "work_date")

_UNI_WORDS = {
    "did":     {"of": "student", "m": "Виконав:", "f": "Виконала:", "pl": "Виконали:"},
    "took":    {"of": "teacher", "m": "Прийняв:", "f": "Прийняла:"},
    "did_lc":  {"of": "student", "m": "виконав:", "f": "виконала:", "pl": "виконали:"},
    "checked": {"of": "teacher", "m": "перевірив", "f": "перевірила"},
}
_SCHOOL_WORDS = {
    "did":     {"of": "student", "m": "Виконав:", "f": "Виконала:", "pl": "Виконали:"},
    "pupil":   {"of": "student", "m": "учень", "f": "учениця", "pl": "учні"},
    "checked": {"of": "teacher", "m": "Перевірив:", "f": "Перевірила:"},
}

TEMPLATES = {
    "university_lab": {
        "name": "Університет / коледж — лабораторна, практична",
        "level": "university", "kind": "lab", "words": _UNI_WORDS,
        "title_page": [
            {"t": "line", "text": "{ministry}", "optional": True},
            {"t": "line", "text": "{institution}"},
            {"t": "blank", "n": 1},
            {"t": "line", "text": "Кафедра {department}", "optional": True},
            {"t": "blank", "n": 4},
            {"t": "line", "text": "Дисципліна «{discipline}»"},
            {"t": "line", "text": "{title}"},
            {"t": "blank", "n": 5},
            {"t": "columns",
             "left": ["{did}", {"text": "ст. гр. {group}", "optional": True}, "{students}"],
             "right": ["{took}", "{teacher}"]},
            {"t": "push"},
            {"t": "line", "text": "{city_dash_year}"},
        ],
    },
    "university_essay": {
        "name": "Університет / коледж — реферат",
        "level": "university", "kind": "essay", "words": _UNI_WORDS,
        "title_page": [
            {"t": "line", "text": "{ministry}", "optional": True},
            {"t": "line", "text": "{institution}"},
            {"t": "blank", "n": 2},
            {"t": "field", "label": "Факультет", "value": "{faculty}", "optional": True},
            {"t": "field", "label": "Кафедра", "value": "{department}", "optional": True},
            {"t": "blank", "n": 3},
            {"t": "line", "text": "РЕФЕРАТ", "size": 16, "bold": True},
            {"t": "blank", "n": 1},
            {"t": "field", "label": "на тему:", "value": "{title}", "hint": "(тема реферату)"},
            {"t": "blank", "n": 1},
            {"t": "field", "label": "", "value": "{discipline}", "hint": "(дисципліна)"},
            {"t": "blank", "n": 2},
            {"t": "field", "label": "{did_lc}", "value": "{work_date}   студент гр. {group}   {student}",
             "hint": "(дата, група, прізвище, ініціали)", "repeat": "students"},
            {"t": "blank", "n": 1},
            {"t": "field", "label": "{checked}", "value": "{teacher_position} {teacher}",
             "hint": "(посада, прізвище, ініціали)"},
            {"t": "push"},
            {"t": "line", "text": "{city_year_r}"},
        ],
    },
    "university_course": {
        "name": "Університет / коледж — курсова робота, курсовий проєкт",
        "level": "university", "kind": "course", "words": _UNI_WORDS,
        "title_page": [
            {"t": "line", "text": "{ministry}", "optional": True},
            {"t": "line", "text": "{institution}"},
            {"t": "blank", "n": 1},
            {"t": "field", "label": "Факультет", "value": "{faculty}", "optional": True},
            {"t": "field", "label": "Кафедра", "value": "{department}", "optional": True},
            {"t": "blank", "n": 3},
            {"t": "line", "text": "{course_title}", "bold": True},
            {"t": "line", "text": "ПОЯСНЮВАЛЬНА ЗАПИСКА", "bold": True},
            {"t": "field", "label": "", "value": "{doc_code}", "hint": "(позначення документа в разі необхідності)",
             "optional": True},
            {"t": "blank", "n": 1},
            {"t": "field", "label": "", "value": "{title}", "hint": "{topic_hint}"},
            {"t": "blank", "n": 1},
            {"t": "field", "label": "", "value": "{discipline}", "hint": "(дисципліна)"},
            {"t": "blank", "n": 2},
            {"t": "field", "label": "Керівник", "value": "{supervisor}", "hint": "(підпис, дата, посада, прізвище, ініціали)",
             "repeat": "teachers", "repeat_label": True},
            {"t": "blank", "n": 1},
            {"t": "field", "label": "Студент", "value": "{group}   {student}", "hint": "(група, підпис, дата, прізвище, ініціали)",
             "repeat": "students", "repeat_label": True},
            {"t": "push"},
            {"t": "line", "text": "{city_year}"},
        ],
    },
    "school_lab": {
        "name": "Школа, ліцей, гімназія — лабораторна, практична",
        "level": "school", "kind": "lab", "words": _SCHOOL_WORDS,
        "title_page": [
            {"t": "line", "text": "{ministry}", "optional": True},
            {"t": "line", "text": "{institution}"},
            {"t": "blank", "n": 6},
            {"t": "line", "text": "{title}", "bold": True},
            {"t": "line", "text": "з предмета «{discipline}»"},
            {"t": "blank", "n": 6},
            {"t": "columns", "left": [],
             "right": ["{did}", {"text": "{pupil} {group} класу", "optional": True}, "{students}",
                       "", "{checked}", {"text": "{teacher_position}", "optional": True}, "{teacher}"]},
            {"t": "push"},
            {"t": "line", "text": "{city_dash_year}"},
        ],
    },
    "school_essay": {
        "name": "Школа, ліцей, гімназія — реферат",
        "level": "school", "kind": "essay", "words": _SCHOOL_WORDS,
        "title_page": [
            {"t": "line", "text": "{ministry}", "optional": True},
            {"t": "line", "text": "{institution}"},
            {"t": "blank", "n": 6},
            {"t": "line", "text": "РЕФЕРАТ", "size": 16, "bold": True},
            {"t": "line", "text": "з предмета «{discipline}»"},
            {"t": "line", "text": "на тему: «{title}»"},
            {"t": "blank", "n": 6},
            {"t": "columns", "left": [],
             "right": ["{did}", {"text": "{pupil} {group} класу", "optional": True}, "{students}",
                       "", "{checked}", {"text": "{teacher_position}", "optional": True}, "{teacher}"]},
            {"t": "push"},
            {"t": "line", "text": "{city_dash_year}"},
        ],
    },
}

# Suggestions for the "institution" field; it stays free text
INSTITUTIONS = [
    ("Харківський національний університет радіоелектроніки", "Харків"),
    ("Харківський національний університет імені В. Н. Каразіна", "Харків"),
    ("Національний технічний університет «Харківський політехнічний інститут»", "Харків"),
    ("Харківський національний економічний університет імені Семена Кузнеця", "Харків"),
    ("Національний технічний університет України «Київський політехнічний інститут імені Ігоря Сікорського»", "Київ"),
    ("Київський національний університет імені Тараса Шевченка", "Київ"),
    ("Національний університет «Києво-Могилянська академія»", "Київ"),
    ("Національний авіаційний університет", "Київ"),
    ("Київський національний економічний університет імені Вадима Гетьмана", "Київ"),
    ("Національний університет біоресурсів і природокористування України", "Київ"),
    ("Національний університет «Львівська політехніка»", "Львів"),
    ("Львівський національний університет імені Івана Франка", "Львів"),
    ("Одеський національний університет імені І. І. Мечникова", "Одеса"),
    ("Національний університет «Одеська політехніка»", "Одеса"),
    ("Дніпровський національний університет імені Олеся Гончара", "Дніпро"),
    ("Сумський державний університет", "Суми"),
    ("Чернівецький національний університет імені Юрія Федьковича", "Чернівці"),
    ("Вінницький національний технічний університет", "Вінниця"),
    ("Запорізький національний університет", "Запоріжжя"),
    ("Національний університет «Запорізька політехніка»", "Запоріжжя"),
    ("Ужгородський національний університет", "Ужгород"),
    ("Тернопільський національний технічний університет імені Івана Пулюя", "Тернопіль"),
    ("Прикарпатський національний університет імені Василя Стефаника", "Івано-Франківськ"),
    ("Черкаський національний університет імені Богдана Хмельницького", "Черкаси"),
    ("Хмельницький національний університет", "Хмельницький"),
    ("Державний університет «Житомирська політехніка»", "Житомир"),
    ("Національний університет «Полтавська політехніка імені Юрія Кондратюка»", "Полтава"),
]


def template_id(report) -> str:
    level = getattr(report, "level", "university") or "university"
    kind = getattr(report, "kind", "lab") or "lab"
    tid = f"{level}_{kind}"
    return tid if tid in TEMPLATES else f"university_{kind}"


def public_templates() -> dict:
    """What GET /templates returns to the browser."""
    return {
        "templates": {tid: {k: v for k, v in tpl.items()} for tid, tpl in TEMPLATES.items()},
        "fields": list(FIELDS),
        "institutions": [{"name": n, "city": c} for n, c in INSTITUTIONS],
        "ministry_default": MINISTRY_UA,
    }


# ── resolving a template for a report ────────────────────────────────────────

def student_names(report) -> list[str]:
    text = getattr(report, "student_name", "") or ""
    return [line.strip() for line in text.replace("\r\n", "\n").split("\n") if line.strip()]


def _year(report) -> str:
    digits = (getattr(report, "work_date", "") or "").strip()[-4:]
    return digits if digits.isdigit() else str(datetime.now().year)


def _variables(report, template) -> dict:
    names = student_names(report)
    values = {f: (getattr(report, f, "") or "").strip() for f in FIELDS}
    year = _year(report)
    city = values["city"]
    words = course_words(report)
    values.update(
        year=year,
        city_dash_year=f"{city} – {year}" if city else year,
        city_year_r=f"{city} {year} р." if city else f"{year} р.",
        city_year=f"{city} {year}" if city else year,
        course_title=words["title"],
        topic_hint=words["topic_hint"],
        doc_code=report_meta_value(report, "doc_code"),
    )
    for word, forms in template["words"].items():
        if forms["of"] == "student":
            key = "pl" if len(names) > 1 else ("f" if getattr(report, "student_gender", "m") == "f" else "m")
        else:
            key = "f" if getattr(report, "teacher_gender", "f") == "f" else "m"
        values[word] = forms.get(key, forms["m"])
    return values


_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _fill(text: str, values: dict) -> tuple[str, bool]:
    """(filled text, whether any placeholder had a value)."""
    found = False

    def sub(m):
        nonlocal found
        value = values.get(m.group(1), "")
        found = found or bool(value)
        return value

    filled = _PLACEHOLDER.sub(sub, text)
    return " ".join(filled.split()), found


def _line_spec(item) -> dict:
    return item if isinstance(item, dict) else {"text": item}


def resolve_title_page(report) -> list[dict]:
    """The template with the report's values filled in, ready to draw."""
    template = TEMPLATES[template_id(report)]
    values = _variables(report, template)
    names = student_names(report) or [""]
    repeats = {"students": ("student", names), "teachers": ("supervisor", supervisors(report) or [""])}

    def lines(items):
        out = []
        for item in items:
            spec = _line_spec(item)
            if spec["text"] == "{students}":
                out += names
                continue
            text, found = _fill(spec["text"], values)
            has_placeholders = bool(_PLACEHOLDER.search(spec["text"]))
            if spec.get("optional") and has_placeholders and not found:
                continue
            out.append(text)
        return out

    resolved = []
    for el in template["title_page"]:
        kind = el["t"]
        if kind == "line":
            text, found = _fill(el["text"], values)
            if el.get("optional") and not found:
                continue
            resolved.append({"t": "line", "text": text, "align": el.get("align", "center"),
                             "size": el.get("size", 14), "bold": el.get("bold", False)})
        elif kind == "field":
            if el.get("optional") and not _fill(el["value"], values)[1]:
                continue
            var, items = repeats.get(el.get("repeat"), (None, [None]))
            for n, item in enumerate(items):
                label = _fill(el["label"], values)[0] if n == 0 or el.get("repeat_label") else ""
                value = _fill(el["value"], {**values, var: item or ""} if var else values)[0]
                resolved.append({"t": "field", "label": label, "value": value,
                                 "hint": _fill(el.get("hint", ""), values)[0],
                                 "indent": n > 0 and not el.get("repeat_label")})
        elif kind == "columns":
            resolved.append({"t": "columns", "left": lines(el["left"]), "right": lines(el["right"])})
        else:
            resolved.append(dict(el))
    return resolved
