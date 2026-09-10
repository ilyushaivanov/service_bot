import os
import tempfile

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def register_font():
    """Пробуем зарегистрировать русский шрифт."""
    try:
        font_paths = [
            ("arial.ttf", "Arial", "Arial-Bold"),
            ("C:/Windows/Fonts/arial.ttf", "Arial", "Arial-Bold"),
            ("C:/Windows/Fonts/times.ttf", "Times", "Times-Bold"),
            ("C:/Windows/Fonts/calibri.ttf", "Calibri", "Calibri-Bold"),
            (
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "DejaVuSans", "DejaVuSans-Bold"
            ),
            ("/System/Library/Fonts/Arial.ttf", "Arial", "Arial-Bold"),
        ]

        for font_path, font_name, font_bold_name in font_paths:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                pdfmetrics.registerFont(TTFont(font_bold_name, font_path))
                print(f"✅ Зарегистрирован шрифт: {font_name} из {font_path}")
                return font_name, font_bold_name

        print("⚠️ Русский шрифт не найден, используется Helvetica")
        return "Helvetica", "Helvetica-Bold"
    except Exception as e:
        print(f"⚠️ Ошибка регистрации шрифта: {e}")
        return "Helvetica", "Helvetica-Bold"


font_normal, font_bold = register_font()


def create_resume_pdf(user_data, output_path=None):
    """Создает простой PDF с резюме."""
    if output_path is None:
        temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        output_path = temp_file.name

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    try:
        c.setFont(font_bold, 16)
    except:
        c.setFont(font_normal, 16)

    c.drawString(50, height - 50, "РЕЗЮМЕ")

    c.line(50, height - 60, width - 50, height - 60)

    y = height - 80

    try:
        c.setFont(font_bold, 14)
    except:
        c.setFont(font_normal, 14)

    full_name = str(user_data.get('full_name', 'Не указано'))
    if len(full_name) > 50:
        full_name = full_name[:47] + "..."
    c.drawString(50, y, full_name)
    y -= 25

    c.setFont(font_normal, 10)

    info = [
        f"Телефон: {user_data.get('phone', 'Не указано')}",
        f"Возраст: {user_data.get('age', 'Не указано')} лет",
        f"Желаемая зарплата: {user_data.get(
            'desired_salary', 'Не указано')} руб.",
        f"График работы: {user_data.get('schedule', 'Не указано')}",
        f"Время работы: {user_data.get('working_hours', 'Не указано')}",
        f"Образование: {user_data.get('university', 'Не указано')}",
    ]

    for line in info:
        c.drawString(50, y, str(line))
        y -= 15

    y -= 10

    c.setFont(font_bold, 11)
    c.drawString(50, y, "Дополнительная информация:")
    y -= 18
    c.setFont(font_normal, 10)

    extra = [
        f"Командировки: {user_data.get('business_trips', 'Не указано')}",
        f"Время в пути: {user_data.get('commute_time', 'Не указано')}",
        f"Формат работы: {user_data.get('work_format', 'Не указано')}",
        f"Тип занятости: {user_data.get('employment_type', 'Не указано')}",
    ]
    for line in extra:
        c.drawString(60, y, line)
        y -= 15

    y -= 5

    try:
        c.setFont(font_bold, 11)
    except:
        c.setFont(font_normal, 11)
    c.drawString(50, y, "Ключевые навыки:")
    y -= 15

    c.setFont(font_normal, 10)
    skills = user_data.get('skills', '')
    if skills:
        words = str(skills).split()
        lines = []
        current_line = ""

        for word in words:
            if len(current_line) + len(word) < 60:
                current_line += word + " "
            else:
                lines.append(current_line)
                current_line = word + " "

        if current_line:
            lines.append(current_line)

        for line in lines[:5]:
            c.drawString(60, y, line)
            y -= 15
    else:
        c.drawString(60, y, "Не указаны")
        y -= 15

    y -= 10

    c.setFont(font_normal, 9)
    c.drawString(50, y, f"Номер заявки: #{user_data.get('resume_id', '')}")
    y -= 12
    c.drawString(50, y, f"Дата: {user_data.get('created_at', '')}")
    y -= 12
    c.drawString(50, y, f"Статус: {user_data.get(
        'status', 'На рассмотрении')}")

    c.setFont(font_normal, 8)
    c.drawString(50, 30, "Сгенерировано HR Recruiter Bot")

    c.save()
    return output_path


def create_template_pdf(output_path=None):
    """Создает шаблон для заполнения."""
    if output_path is None:
        temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        output_path = temp_file.name

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    try:
        c.setFont(font_bold, 16)
    except:
        c.setFont(font_normal, 16)

    c.drawString(50, height - 50, "ШАБЛОН РЕЗЮМЕ")

    c.setFont(font_normal, 10)
    y = height - 80

    fields = [
        "ФИО: _______________________________________________________",
        "Телефон: _______________________ Email: ____________________",
        "ВУЗ: _______________________________________________________",
        "Желаемая зарплата: [ ] от 20 до 50тыс  [ ] от 50 до 100тыс",
        "                    [ ] от 100 до 150тыс  [ ] от 150 до 200тыс",
        "График работы: [ ] 2/2  [ ] 5/2  [ ] 3/3  [ ] гибкий график",
        "Время работы: ________ - ________ (например: 10:00-18:00)",
        "Навыки: ____________________________________________________",
        "____________________________________________________________",
        "Возраст: _______ лет",
        "Командировки: [ ] Не могу  [ ] Могу  [ ] Могу иногда",
        "Время в пути: [ ] Не имеет значения  [ ] Не дольше 1 часа  [ ] Не дольше 1.5 часов",
        "Формат работы: [ ] На месте работодателя  [ ] Удаленно  [ ] Гибрид  [ ] Разъездная  [ ] Вахта",
        "Тип занятости: [ ] Постоянная работа  [ ] Подработка  [ ] Стажировка  [ ] Волонтерство",
    ]

    for field in fields:
        c.drawString(50, y, field)
        y -= 20

    c.save()
    return output_path
