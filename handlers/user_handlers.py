import os
import re
import tempfile

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, FSInputFile, InlineKeyboardButton,
                           InlineKeyboardMarkup, KeyboardButton, Message,
                           ReplyKeyboardMarkup, ReplyKeyboardRemove)

import database
from pdf_generator import create_resume_pdf, create_template_pdf

router = Router()

user_states = {}


class ResumeForm(StatesGroup):
    full_name = State()
    phone = State()
    university = State()
    desired_salary = State()
    skills = State()
    schedule = State()
    working_hours = State()
    age = State()
    business_trips = State()
    commute_time = State()
    work_format = State()
    employment_type = State()


SALARY_OPTIONS = {
    "20-50 тыс.": (20000, 50000),
    "50-100 тыс.": (50000, 100000),
    "100-150 тыс.": (100000, 150000),
    "150-200 тыс.": (150000, 200000),
}

SCHEDULE_OPTIONS = [
    "2/2",
    "5/2",
    "3/3",
    "Гибкий график"
]

BUSINESS_TRIPS_OPTIONS = ["Не могу", "Могу", "Могу иногда"]
COMMUTE_TIME_OPTIONS = ["Не имеет значения", "Не дольше 1 часа", "Не дольше 1.5 часов"]
WORK_FORMAT_OPTIONS = ["На месте работодателя", "Удаленно", "Гибрид", "Разъездная", "Вахта"]
EMPLOYMENT_TYPE_OPTIONS = ["Постоянная работа", "Подработка", "Стажировка", "Волонтерство"]


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я HR-бот.\n\n"
        "Используйте /anketa для заполнения резюме\n"
        "/template для шаблона PDF\n"
        "/help для помощи\n"
        "/memorandum - памятка для кандидата"
    )


@router.message(Command("anketa"))
async def cmd_anketa(message: Message, state: FSMContext):
    await message.answer("Введите ваше ФИО:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ResumeForm.full_name)


@router.message(ResumeForm.full_name)
async def process_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Введите ваш телефон в формате 89123456789:")
    await state.set_state(ResumeForm.phone)


@router.message(ResumeForm.phone)
async def process_phone(message: Message, state: FSMContext):
    phone_number = message.text.strip()
    pattern = r'^89\d{9}$'
    if re.match(pattern, phone_number):
        await state.update_data(phone=phone_number)
        await message.answer("Введите ваш ВУЗ:")
        await state.set_state(ResumeForm.university)
    else:
        await message.answer(
            "❌ Неверный формат номера!\n"
            "Пожалуйста, введите номер в формате: 89xxxxxxxxx (11 цифр)\n"
            "Например: 89123456789\n\n"
            "Введите ваш телефон еще раз:"
        )


@router.message(ResumeForm.university)
async def process_university(message: Message, state: FSMContext):
    await state.update_data(university=message.text)

    salary_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text="20-50 тыс."), KeyboardButton(text="50-100 тыс.")],
            [KeyboardButton(
                text="100-150 тыс."), KeyboardButton(text="150-200 тыс.")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        "Выберите желаемую зарплату из предложенных вариантов:",
        reply_markup=salary_keyboard
    )
    await state.set_state(ResumeForm.desired_salary)


@router.message(ResumeForm.desired_salary)
async def process_salary(message: Message, state: FSMContext):
    if message.text not in SALARY_OPTIONS:
        await message.answer(
            "❌ Пожалуйста, выберите один из предложенных вариантов зарплаты:\n"
            "20-50 тыс., 50-100 тыс., 100-150 тыс., 150-200 тыс."
        )
        return

    min_salary, max_salary = SALARY_OPTIONS[message.text]
    avg_salary = (min_salary + max_salary) // 2

    await state.update_data(
        desired_salary=avg_salary, salary_text=message.text)
    await message.answer("Введите ваши навыки (через запятую):")
    await state.set_state(ResumeForm.skills)


@router.message(ResumeForm.skills)
async def process_skills(message: Message, state: FSMContext):
    await state.update_data(skills=message.text)

    schedule_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="2/2"), KeyboardButton(text="5/2")],
            [KeyboardButton(text="3/3"), KeyboardButton(text="Гибкий график")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        "Выберите график работы из предложенных вариантов:",
        reply_markup=schedule_keyboard
    )
    await state.set_state(ResumeForm.schedule)


@router.message(ResumeForm.schedule)
async def process_schedule(message: Message, state: FSMContext):
    if message.text not in SCHEDULE_OPTIONS:
        await message.answer(
            "❌ Пожалуйста, выберите один из предложенных вариантов графика:\n"
            "2/2, 5/2, 3/3, Гибкий график"
        )
        return

    await state.update_data(schedule=message.text)

    time_options = {
        "2/2": ["09:00-21:00", "21:00-09:00"],
        "5/2": ["09:00-18:00", "10:00-19:00", "11:00-20:00"],
        "3/3": ["09:00-21:00", "21:00-9:00"],
        "Гибкий график": ["По договоренности"]
    }

    time_buttons = []
    current_row = []

    for time_option in time_options.get(message.text, ["9:00-18:00"]):
        current_row.append(KeyboardButton(text=time_option))
        if len(current_row) == 2:
            time_buttons.append(current_row)
            current_row = []

    if current_row:
        time_buttons.append(current_row)

    working_hours_keyboard = ReplyKeyboardMarkup(
        keyboard=time_buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        f"Выберите время работы для графика '{message.text}':",
        reply_markup=working_hours_keyboard
    )
    await state.set_state(ResumeForm.working_hours)


@router.message(ResumeForm.working_hours)
async def process_working_hours(message: Message, state: FSMContext):
    time_pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]-([01]?[0-9]|2[0-3]):[0-5][0-9]$|^По договоренности$'

    if re.match(time_pattern, message.text):
        await state.update_data(working_hours=message.text)

        age_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="18"), KeyboardButton(text="19"), KeyboardButton(text="20")],
                [KeyboardButton(text="21"), KeyboardButton(text="22"), KeyboardButton(text="23")],
                [KeyboardButton(text="24"), KeyboardButton(text="25"), KeyboardButton(text="26")],
                [KeyboardButton(text="27"), KeyboardButton(text="28"), KeyboardButton(text="29")],
                [KeyboardButton(text="30"), KeyboardButton(text="Другой возраст")],
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await message.answer("Выберите ваш возраст или введите другой:")
        await state.set_state(ResumeForm.age)
    else:
        await message.answer(
            "❌ Неверный формат времени. Введите время в формате ЧЧ:ММ-ЧЧ:ММ\n"
            "Например: 9:00-18:00 или выберите из предложенных вариантов."
        )


@router.message(ResumeForm.age)
async def process_age(message: Message, state: FSMContext, db: database.Database):
    if message.text.isdigit():
        age = int(message.text)
        if 18 <= age <= 65:
            await state.update_data(age=age)

            keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=opt)] for opt in BUSINESS_TRIPS_OPTIONS],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            await message.answer(
                "🚗 *Командировки:*\nГотовы ли вы к командировкам?",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await state.set_state(ResumeForm.business_trips)
        else:
            await message.answer("❌ Возраст должен быть от 18 до 65 лет. Введите корректный возраст:")
    else:
        await message.answer("❌ Пожалуйста, введите число (возраст от 18 до 65 лет):")


@router.message(ResumeForm.business_trips)
async def process_business_trips(message: Message, state: FSMContext):
    if message.text not in BUSINESS_TRIPS_OPTIONS:
        await message.answer(
            "❌ Пожалуйста, выберите один из предложенных вариантов:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=opt)] for opt in BUSINESS_TRIPS_OPTIONS],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return

    await state.update_data(business_trips=message.text)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=opt)] for opt in COMMUTE_TIME_OPTIONS],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "⏱ *Время в пути до работы:*\nКакое время в пути вас устраивает?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(ResumeForm.commute_time)


@router.message(ResumeForm.commute_time)
async def process_commute_time(message: Message, state: FSMContext):
    if message.text not in COMMUTE_TIME_OPTIONS:
        await message.answer(
            "❌ Пожалуйста, выберите один из предложенных вариантов:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=opt)] for opt in COMMUTE_TIME_OPTIONS],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return

    await state.update_data(commute_time=message.text)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=opt)] for opt in WORK_FORMAT_OPTIONS],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "🏢 *Формат работы:*\nКакой формат работы предпочитаете?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(ResumeForm.work_format)


@router.message(ResumeForm.work_format)
async def process_work_format(message: Message, state: FSMContext):
    if message.text not in WORK_FORMAT_OPTIONS:
        await message.answer(
            "❌ Пожалуйста, выберите один из предложенных вариантов:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=opt)] for opt in WORK_FORMAT_OPTIONS],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return

    await state.update_data(work_format=message.text)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=opt)] for opt in EMPLOYMENT_TYPE_OPTIONS],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "📋 *Тип занятости:*\nКакой тип занятости вас интересует?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(ResumeForm.employment_type)


@router.message(ResumeForm.employment_type)
async def process_employment_type(message: Message, state: FSMContext, db: database.Database):
    if message.text not in EMPLOYMENT_TYPE_OPTIONS:
        await message.answer(
            "❌ Пожалуйста, выберите один из предложенных вариантов:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=opt)] for opt in EMPLOYMENT_TYPE_OPTIONS],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return

    await state.update_data(employment_type=message.text)

    data = await state.get_data()

    resume_id = db.add_resume(
        user_id=message.from_user.id,
        full_name=data['full_name'],
        phone=data['phone'],
        university=data['university'],
        desired_salary=data['desired_salary'],
        skills=data['skills'],
        schedule=data['schedule'],
        working_hours=data.get('working_hours', 'Не указано'),
        age=data['age'],
        business_trips=data['business_trips'],
        commute_time=data['commute_time'],
        work_format=data['work_format'],
        employment_type=data['employment_type']
    )

    resume = db.get_resume(resume_id)
    if resume:
        user_data = {
            'full_name': resume['full_name'],
            'phone': resume['phone'],
            'university': resume['university'],
            'desired_salary': resume['desired_salary'],
            'skills': resume['skills'],
            'schedule': resume['schedule'],
            'working_hours': resume['working_hours'] if resume['working_hours'] else 'Не указано',
            'age': resume['age'],
            'status': resume['status'],
            'created_at': resume['created_at'],
            'business_trips': resume['business_trips'],
            'commute_time': resume['commute_time'],
            'work_format': resume['work_format'],
            'employment_type': resume['employment_type'],
            'resume_id': resume_id,
        }

        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                pdf_path = tmp_file.name

            create_resume_pdf(user_data, pdf_path)

            await message.answer_document(
                FSInputFile(pdf_path, filename=f"Резюме_{resume_id}.pdf"),
                caption=f"✅ Резюме #{resume_id} готово!\n\n"
                        f"👤 {data['full_name']}\n"
                        f"📞 {data['phone']}\n"
                        f"💰 {data.get('salary_text', str(data['desired_salary']) + ' руб.')}\n"
                        f"⏰ График: {data['schedule']} ({data.get('working_hours', '')})"
            )

            confirmation_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Всё заполнено правильно",
                            callback_data=f"confirm_correct_{resume_id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🔄 Начать заново",
                            callback_data=f"restart_form_{resume_id}"
                        )
                    ]
                ]
            )

            summary_text = (
                "📋 *Сверьте ваши данные:*\n\n"
                f"👤 ФИО: {data['full_name']}\n"
                f"📞 Телефон: {data['phone']}\n"
                f"🎓 ВУЗ: {data['university']}\n"
                f"💰 Зарплата: {data.get('salary_text', str(data['desired_salary']) + ' руб.')}\n"
                f"💼 Навыки: {data['skills']}\n"
                f"📅 График: {data['schedule']}\n"
                f"⏰ Время работы: {data.get('working_hours', 'Не указано')}\n"
                f"🎂 Возраст: {data['age']} \n"
                f"🚗 Командировки: {data['business_trips']}\n"
                f"⏱ Время в пути: {data['commute_time']}\n"
                f"🏢 Формат работы: {data['work_format']}\n"
                f"📋 Тип занятости: {data['employment_type']}\n\n"
                "Если все верно, подтвердите данные. Если нужно исправить - начните заново."
            )

            await message.answer(
                summary_text,
                reply_markup=confirmation_keyboard,
                parse_mode="Markdown"
            )

        except Exception as e:
            await message.answer(f"❌ Ошибка создания PDF: {e}")
        finally:
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    else:
        await message.answer(f"✅ Анкета сохранена! Номер: #{resume_id}")

    await state.clear()


@router.callback_query(F.data.startswith("confirm_correct_"))
async def confirm_data_correct(callback: CallbackQuery, db: database.Database):
    """Обработка подтверждения правильности данных."""
    resume_id = callback.data.split("_")[2]

    db.update_status(resume_id, "confirmed")

    await callback.message.answer(
        "✅ Спасибо! Ваши данные подтверждены.\n\n"
        "Ваше резюме будет рассмотрено в ближайшее время.\n"
        "Вы получите уведомление о статусе рассмотрения.\n\n"
        "📞 По вопросам: @hr_support",
    )

    await callback.message.delete()
    await callback.answer("✅ Данные подтверждены!")


@router.callback_query(F.data.startswith("restart_form_"))
async def restart_form(
    callback: CallbackQuery, state: FSMContext, db: database.Database
):
    """Обработка начала заполнения заново."""
    await callback.message.answer(
        "🔄 Начинаем заполнение заново.\n\n"
        "Введите ваше ФИО:",
        reply_markup=ReplyKeyboardRemove()
    )

    await state.set_state(ResumeForm.full_name)
    await callback.answer()


@router.message(Command("pdf"))
async def download_pdf_command(message: Message, db: database.Database):
    await message.answer(
        "Введите номер вашей заявки (например: 1) или отправьте #1"
    )


@router.message(F.text.regexp(r'^#?\d+$'))
async def download_pdf_by_number(message: Message, db: database.Database):
    resume_id = message.text.replace('#', '')
    resume = db.get_resume(resume_id)

    if not resume:
        await message.answer("Заявка не найдена")
        return

    user_data = {
        'full_name': resume['full_name'],
        'phone': resume['phone'],
        'university': resume['university'],
        'desired_salary': resume['desired_salary'],
        'skills': resume['skills'],
        'schedule': resume['schedule'],
        'working_hours': resume['working_hours'] if resume['working_hours'] else 'Не указано',
        'age': resume['age'],
        'status': resume['status'],
        'created_at': resume['created_at'],
        'business_trips': resume['business_trips'],
        'commute_time': resume['commute_time'],
        'work_format': resume['work_format'],
        'employment_type': resume['employment_type'],
        'resume_id': resume_id,
    }

    try:
        with tempfile.NamedTemporaryFile(
            suffix='.pdf', delete=False
        ) as tmp_file:
            pdf_path = tmp_file.name

        create_resume_pdf(user_data, pdf_path)

        await message.answer_document(
            FSInputFile(pdf_path, filename=f"Резюме_{resume_id}.pdf"),
            caption=f"📄 Резюме #{resume_id}"
        )

    except Exception as e:
        await message.answer(f"Ошибка: {e}")
    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)


@router.message(Command("template"))
async def cmd_template(message: Message):
    try:
        with tempfile.NamedTemporaryFile(
            suffix='.pdf', delete=False
        ) as tmp_file:
            pdf_path = tmp_file.name

        create_template_pdf(pdf_path)

        await message.answer_document(
            FSInputFile(pdf_path, filename="Шаблон_резюме.pdf"),
            caption="Шаблон резюме"
        )
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)


@router.message(Command("status"))
async def check_status_command(message: Message):
    await message.answer("Введите номер заявки (например: 1)")


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "/anketa - заполнить резюме\n"
        "/template - шаблон PDF\n"
        "/pdf - скачать PDF по номеру\n"
        "/status - проверить статус\n"
        "/admin - админка\n"
        "/memorandum - памятка для кандидатов\n"
    )


@router.message(Command("memorandum"))
async def cmd_memorandum(message: Message):
    memorandum_text = (
        "📋 *ПАМЯТКА ДЛЯ КАНДИДАТА*\n\n"
        "После прохождения отбора:\n\n"
        "✅ 1. Подготовьте документы:*\n"
        "   • Паспорт\n"
        "   • ИНН\n"
        "   • СНИЛС\n"
        "   • Документы об образовании\n"
        "   • Трудовая книжка (при наличии)\n\n"
        "✅ 2. Этапы оформления:*\n"
        "   День 1-2: Проверка документов\n"
        "   День 3: Заключение договора\n"
        "   День 4: Выход на стажировку\n\n"
        "✅ 3. Что нужно знать:*\n"
        "   • Рабочий день с 9:00 до 18:00\n"
        "   • Обед с 13:00 до 14:00\n"
        "   • Дресс-код: business casual\n"
        "   • Первые 2 недели - испытательный срок\n\n"
        "📞 Контакты HR-отдела:*\n"
        "   • Телефон: +7 (495) 123-45-67\n"
        "   • Email: hr@company.com\n"
        "   • Telegram: @hr_manager\n\n"
        "Желаем успехов в работе! 🚀"
    )
    await message.answer(memorandum_text)
