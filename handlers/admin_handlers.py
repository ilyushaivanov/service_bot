import os
import tempfile

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, FSInputFile, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

import database
from config import ADMIN_ID, ADMIN_PASSWORD, ZOOM_LINK
from dashboard_generator import create_statistics_dashboard
from pdf_generator import create_resume_pdf

router = Router()

active_admins = []


class EditCriteria(StatesGroup):
    waiting_for_universities = State()
    waiting_for_skills = State()


def is_admin(user_id):
    return user_id == ADMIN_ID or user_id in active_admins


async def send_zoom_invitation(resume, bot):
    """Отправляет приглашение на Zoom кандидату."""
    if not ZOOM_LINK:
        print("⚠️ ZOOM_LINK не задан в .env файле")
        return

    invitation_text = f"""
🎉 *Поздравляем, {resume['full_name']}!*

Вы успешно прошли первый этап собеседования! 🚀

*Приглашаем вас на второй этап — онлайн-собеседование:*

🔗 *Ссылка на конференцию:* {ZOOM_LINK}

*Подготовка к собеседованию:*
1. Установите приложение Zoom
2. Проверьте камеру и микрофон
3. Подключитесь за 5-10 минут до начала

Удачи на собеседовании! ✨
    """.strip()

    try:
        await bot.send_message(
            chat_id=resume['user_id'],
            text=invitation_text,
            parse_mode="Markdown"
        )
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки приглашения: {e}")
        return False


async def send_rejection_notification(resume, bot):
    """Отправляет уведомление об отклонении заявки кандидату."""
    rejection_text = f"""
😔 *Уважаемый(ая) {resume['full_name']}!*

Мы рассмотрели вашу заявку #{resume['id']} и, к сожалению, на данном этапе не можем предложить вам участие в следующем этапе собеседования.

📋 Рекомендации для улучшения:

1️⃣ 🎓 Образование и ВУЗ
   • Рассмотрите возможность получения образования в топовых ВУЗах
   • Или пройдите профильные курсы с сертификацией

2️⃣ 💼 Навыки и компетенции
   • Развивайте ключевые навыки: Python, SQL, Git, Docker, Linux
   • Изучите английский язык (минимум Intermediate)
   • Пройдите курсы на платформах: Coursera, Stepik, Яндекс.Практикум

3️⃣ 📈 Опыт работы
   • Получите опыт работы в интересующей сфере (стажировки, проекты)
   • Участвуйте в хакатонах и открытых проектах

4️⃣ 📄 Резюме
   • Обновите резюме с акцентом на ключевые навыки
   • Добавьте портфолио проектов (GitHub, Behance и т.д.)

🔄 Что дальше?
Вы можете подать заявку повторно через *3 месяца*, предварительно улучшив свои компетенции.

📞 Контакты HR-отдела:
• Телефон: +7 (495) 123-45-67
• Email: hr@company.com
• Telegram: @hr_support

Желаем успехов в профессиональном развитии! 💪

P.S. Не расстраивайтесь! Каждый отказ — это шаг к успеху.
    """.strip()

    try:
        await bot.send_message(
            chat_id=resume[1],
            text=rejection_text,
        )
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления об отклонении: {e}")
        return False


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if is_admin(message.from_user.id):
        await show_admin_menu(message)
    else:
        await message.answer("🔐 Введите пароль для доступа к админке:")


@router.message(F.text == ADMIN_PASSWORD)
async def check_password(message: Message):
    active_admins.append(message.from_user.id)
    await show_admin_menu(message)


async def show_admin_menu(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Все заявки", callback_data="admin_all")],
        [InlineKeyboardButton(text="🆕 Новые заявки", callback_data="admin_new")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📈 Дашборд", callback_data="admin_dashboard")],
        [InlineKeyboardButton(text="⚙️ Критерии анализа", callback_data="admin_criteria")],
    ])
    await message.answer("Админ-панель:", reply_markup=keyboard)


@router.callback_query(F.data == "admin_all")
async def show_all(callback: CallbackQuery, db: database.Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    resumes = db.get_all_resumes()

    if not resumes:
        await callback.message.edit_text("📭 Заявок пока нет")
        return

    try:
        stats = db.get_candidate_statistics()
        candidates_by_id = {candidate['id']: candidate for candidate in stats['classified']}
    except:
        candidates_by_id = {}

    text = "📋 Все заявки:\n\n"
    for resume in resumes[:15]:
        category_icon = ""
        if resume['id'] in candidates_by_id:
            category = candidates_by_id[resume['id']]['category']
            category_icon = {
                'green': '🟢',
                'yellow': '🟡',
                'red': '🔴'
            }.get(category, '⚪')

        status_icon = {
            'new': '🆕',
            'review': '🔍',
            'accepted': '✅',
            'rejected': '❌',
            'confirmed': '✅',
            'canceled': '❌'
        }.get(resume['status'], '📄')

        text += f"{category_icon}{status_icon} #{resume['id']} - {resume['full_name']}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for resume in resumes[:5]:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"👁 #{resume['id']}",
                callback_data=f"admin_view_{resume['id']}"
            ),
            InlineKeyboardButton(
                text="📥 PDF",
                callback_data=f"admin_pdf_{resume['id']}"
            )
        ])

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="📊 Дашборд", callback_data="admin_dashboard"),
        InlineKeyboardButton(text="📈 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admin_new")
async def show_new(callback: CallbackQuery, db: database.Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    resumes = db.get_all_resumes(status='new')

    if not resumes:
        await callback.message.edit_text("🎉 Все заявки обработаны! Новых нет.")
        return

    text = "🆕 Новые заявки:\n\n"
    for resume in resumes:
        text += f"#{resume['id']} - {resume['full_name']}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for resume in resumes[:5]:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"✅ #{resume['id']}",
                callback_data=f"admin_accept_{resume['id']}"
            ),
            InlineKeyboardButton(
                text=f"❌ #{resume[0]}",
                callback_data=f"admin_reject_{resume['id']}"
            ),
            InlineKeyboardButton(
                text="👁",
                callback_data=f"admin_view_{resume['id']}"
            )
        ])

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_view_"))
async def view_resume(callback: CallbackQuery, db: database.Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    resume_id = callback.data.split("_")[2]
    resume = db.get_resume(resume_id)

    if not resume:
        await callback.answer("Заявка не найдена")
        return

    try:
        stats = db.get_candidate_statistics()
        candidate_info = None
        for candidate in stats['classified']:
            if candidate['id'] == int(resume_id):
                candidate_info = candidate
                break

        category_text = ""
        if candidate_info:
            category_icon = {
                'green': '🟢',
                'yellow': '🟡',
                'red': '🔴'
            }.get(candidate_info['category'], '⚪')
            category_name = {
                'green': 'Подходящий',
                'yellow': 'Резерв',
                'red': 'Неподходящий'
            }.get(candidate_info['category'], 'Неизвестно')
            category_text = f"\n🎯 Категория: {category_icon} {category_name}\n"
            category_text += f"   Совпадений: {candidate_info['matches']}/3\n"
    except:
        category_text = ""

    status_text = {
        'new': '🆕 На рассмотрении',
        'review': '🔍 Рассматривается',
        'accepted': '✅ Принято',
        'rejected': '❌ Отклонено',
        'confirmed': '✅ Подтверждено кандидатом'
    }.get(resume[10], resume[10])

    text = f"""📄 *Заявка #{resume['id']}*{category_text}

👤 ФИО: {resume['full_name']}
📞 Телефон: {resume['phone']}
🎓 ВУЗ: {resume['university']}
💰 Зарплата: {resume['desired_salary']} руб.
💼 Навыки: {resume['skills']}
⏰ График: {resume['schedule']}
🕐 Время работы: {resume['working_hours'] if resume['working_hours'] else 'Не указано'}
🎂 Возраст: {resume['age']}
🚗 Командировки: {resume['business_trips']}
⏱ Время в пути: {resume['commute_time']}
🏢 Формат работы: {resume['work_format']}
📋 Тип занятости: {resume['employment_type']}
📅 Дата: {resume['created_at']}
📊 Статус: {status_text}"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Принять",
                callback_data=f"admin_accept_{resume_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"admin_reject_{resume_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📥 Скачать PDF",
                callback_data=f"admin_pdf_{resume_id}"
            ),
            InlineKeyboardButton(
                text="📊 Анализ",
                callback_data=f"admin_analyze_{resume_id}"
            )
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="admin_all")
        ]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_pdf_"))
async def admin_pdf(callback: CallbackQuery, db: database.Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    resume_id = callback.data.split("_")[2]
    resume = db.get_resume(resume_id)

    if not resume:
        await callback.answer("Заявка не найдена")
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

    pdf_path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix='.pdf', delete=False
        ) as tmp_file:
            pdf_path = tmp_file.name

        create_resume_pdf(user_data, pdf_path)

        await callback.message.answer_document(
            FSInputFile(pdf_path, filename=f"Резюме_#{resume_id}.pdf"),
            caption=f"📄 Резюме #{resume_id}"
        )
        await callback.answer("✅ PDF отправлен")

    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}")
        await callback.answer("❌ Ошибка")
    finally:
        if pdf_path and os.path.exists(pdf_path):
            os.unlink(pdf_path)


@router.callback_query(F.data.startswith("admin_accept_"))
async def accept_resume(callback: CallbackQuery, db: database.Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    resume_id = callback.data.split("_")[2]
    db.update_status(resume_id, "accepted")
    resume = db.get_resume(resume_id)

    if resume:
        try:
            success = await send_zoom_invitation(resume, callback.bot)

            if success:
                await callback.answer("✅ Принято и отправлено приглашение на Zoom")
            else:
                await callback.answer("✅ Принято, но не удалось отправить приглашение")
        except Exception as e:
            await callback.answer("✅ Принято, но ошибка отправки приглашения")
            print(f"❌ Ошибка: {e}")
    else:
        await callback.answer("✅ Принято")

    await view_resume(callback, db)


@router.callback_query(F.data.startswith("admin_reject_"))
async def reject_resume(callback: CallbackQuery, db: database.Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    resume_id = callback.data.split("_")[2]
    db.update_status(resume_id, "rejected")

    resume = db.get_resume(resume_id)

    if resume:
        try:
            success = await send_rejection_notification(resume, callback.bot)

            if success:
                await callback.answer("❌ Отклонено и отправлено уведомление кандидату")
            else:
                await callback.answer("❌ Отклонено, но не удалось отправить уведомление")
        except Exception as e:
            await callback.answer("❌ Отклонено, но ошибка отправки уведомления")
            print(f"❌ Ошибка отправки уведомления: {e}")
    else:
        await callback.answer("❌ Отклонено")

    await view_resume(callback, db)


@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery, db: database.Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    stats = db.get_statistics()
    try:
        candidate_stats = db.get_candidate_statistics()
        summary = candidate_stats['summary']

        text = "📊 *Расширенная статистика:*\n\n"
        text += f"📈 Всего заявок: {stats['total']}\n\n"

        text += "📋 *Классификация кандидатов:*\n"
        text += f"✅ Подходящие: {summary['green']} ({summary.get('green_percent', 0)}%)\n"
        text += f"⚠️ Резерв: {summary['yellow']} ({summary.get('yellow_percent', 0)}%)\n"
        text += f"❌ Неподходящие: {summary['red']} ({summary.get('red_percent', 0)}%)\n\n"

    except Exception as e:
        text = "📊 Статистика:\n\n"
        text += f"📈 Всего заявок: {stats['total']}\n\n"

    if stats['by_status']:
        text += "По статусам:\n"
        for status, count in stats['by_status'].items():
            status_name = {
                'new': '🆕 Новые',
                'review': '🔍 На рассмотрении',
                'accepted': '✅ Принятые',
                'rejected': '❌ Отклоненные',
                'confirmed': '✅ Подтвержденные'
            }.get(status, status)
            percent = (count / stats['total']) * 100 if stats['total'] > 0 else 0
            text += f"{status_name}: {count}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Подробный дашборд", callback_data="admin_dashboard")],
        [InlineKeyboardButton(text="⚙️ Критерии анализа", callback_data="admin_criteria")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard,  parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def back_to_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    await show_admin_menu(callback.message)
    await callback.answer()


@router.callback_query(F.data == "admin_dashboard")
async def show_dashboard(callback: CallbackQuery, db: database.Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    await callback.answer("📊 Формирую дашборд...")

    try:
        statistics_data = db.get_candidate_statistics()

        if statistics_data['summary']['total'] == 0:
            await callback.message.answer("📭 Нет данных для построения дашборда.")
            return

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name

        create_statistics_dashboard(statistics_data, pdf_path)

        summary = statistics_data['summary']
        caption = (
            f"📊 ДАШБОРд КАНДИДАТОВ\n\n"
            f"📈 Общая статистика:\n"
            f"• Всего кандидатов: {summary['total']}\n"
            f"• ✅ Подходящие: {summary.get('green', 0)} ({summary.get('green_percent', 0)}%)\n"
            f"• ⚠️ Резерв: {summary.get('yellow', 0)} ({summary.get('yellow_percent', 0)}%)\n"
            f"• ❌ Неподходящие: {summary.get('red', 0)} ({summary.get('red_percent', 0)}%)\n\n"
            f"Критерии анализа:\n"
            f"• Топ ВУЗы: {len(statistics_data['criteria'].get('top_universities', []))}\n"
            f"• Ключевые навыки: {len(statistics_data['criteria'].get('key_skills', []))}\n"
            f"• Возрастные диапазоны: {len(statistics_data['criteria'].get('experience_ranges', []))}"
        )

        await callback.message.answer_document(
            FSInputFile(pdf_path, filename="Дашборд_кандидатов.pdf"),
            caption=caption,
        )

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при создании дашборда: {e}")
    finally:
        if 'pdf_path' in locals() and os.path.exists(pdf_path):
            os.unlink(pdf_path)

    await callback.answer()


@router.callback_query(F.data == "admin_criteria")
async def show_criteria(callback: CallbackQuery, db: database.Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    try:
        criteria = db.get_stats_criteria() or db.get_default_criteria()

        response = "⚙️ *Критерии анализа кандидатов*\n\n"

        response += "*🎓 Топ ВУЗы:*\n"
        universities = criteria.get('top_universities', [])
        for i, univ in enumerate(universities[:5], 1):
            response += f"{i}. {univ}\n"
        if len(universities) > 5:
            response += f"... и еще {len(universities) - 5}\n"

        response += "\n*💻 Ключевые навыки:*\n"
        skills = criteria.get('key_skills', [])
        for i, skill in enumerate(skills[:5], 1):
            response += f"{i}. {skill}\n"
        if len(skills) > 5:
            response += f"... и еще {len(skills) - 5}\n"

        response += "\n*📈 Опыт работы (возраст):*\n"
        for exp in criteria.get('experience_ranges', []):
            response += f"• {exp['min_age']}-{exp['max_age']} лет: {exp.get('label', '')}\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Изменить ВУЗы", callback_data="admin_edit_univ"),
                InlineKeyboardButton(text="✏️ Изменить навыки", callback_data="admin_edit_skills")
            ],
            [
                InlineKeyboardButton(text="📊 Обновить дашборд", callback_data="admin_dashboard"),
                InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")
            ]
        ])

        await callback.message.edit_text(response, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {str(e)}")

    await callback.answer()


@router.callback_query(F.data == "admin_edit_univ")
async def edit_universities_start(callback: CallbackQuery, state: FSMContext, db: database.Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    criteria = db.get_stats_criteria() or db.get_default_criteria()
    current_universities = criteria.get('top_universities', [])

    await state.set_state(EditCriteria.waiting_for_universities)
    await state.update_data(current_criteria=criteria)

    await callback.message.edit_text(
        "✏️ *Редактирование списка ТОП ВУЗов*\n\n"
        f"Текущий список ({len(current_universities)} ВУЗов):\n"
        f"{', '.join(current_universities)}\n\n"
        "Отправьте новый список ВУЗов через запятую:\n"
        "Пример: МГУ, СПбГУ, МФТИ, ВШЭ, МИФИ",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(EditCriteria.waiting_for_universities)
async def edit_universities_process(message: Message, state: FSMContext, db: database.Database):
    data = await state.get_data()
    criteria = data.get('current_criteria', db.get_default_criteria())

    new_universities = [uni.strip() for uni in message.text.split(',') if uni.strip()]
    criteria['top_universities'] = new_universities

    db.save_stats_criteria(criteria)

    await state.clear()

    await message.answer(
        f"✅ Список ВУЗов обновлен!\n"
        f"Добавлено: {len(new_universities)} ВУЗов\n\n"
        f"Для применения изменений обновите дашборд.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Обновить дашборд", callback_data="admin_dashboard")]
        ])
    )


@router.callback_query(F.data == "admin_edit_skills")
async def edit_skills_start(callback: CallbackQuery, state: FSMContext, db: database.Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    criteria = db.get_stats_criteria() or db.get_default_criteria()
    current_skills = criteria.get('key_skills', [])

    await state.set_state(EditCriteria.waiting_for_skills)
    await state.update_data(current_criteria=criteria)

    await callback.message.edit_text(
        "✏️ *Редактирование списка ключевых навыков*\n\n"
        f"Текущий список ({len(current_skills)} навыков):\n"
        f"{', '.join(current_skills)}\n\n"
        "Отправьте новый список навыков через запятую:\n"
        "Пример: python, java, sql, git, docker, linux, английский",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(EditCriteria.waiting_for_skills)
async def edit_skills_process(message: Message, state: FSMContext, db: database.Database):
    data = await state.get_data()
    criteria = data.get('current_criteria', db.get_default_criteria())

    new_skills = [skill.strip().lower() for skill in message.text.split(',') if skill.strip()]
    criteria['key_skills'] = new_skills

    db.save_stats_criteria(criteria)

    await state.clear()

    await message.answer(
        f"✅ Список навыков обновлен!\n"
        f"Добавлено: {len(new_skills)} навыков\n\n"
        f"Для применения изменений обновите дашборд.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Обновить дашборд", callback_data="admin_dashboard")]
        ])
    )


@router.callback_query(F.data.startswith("admin_analyze_"))
async def analyze_resume(callback: CallbackQuery, db: database.Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    resume_id = callback.data.split("_")[2]
    resume = db.get_resume(resume_id)

    if not resume:
        await callback.answer("Заявка не найдена")
        return

    try:
        stats = db.get_candidate_statistics()
        candidate_info = None
        for candidate in stats['classified']:
            if candidate['id'] == int(resume_id):
                candidate_info = candidate
                break

        if not candidate_info:
            await callback.answer("Данные анализа не найдены")
            return

        criteria = stats['criteria']

        text = f"🔍 *Анализ заявки #{resume_id}*\n\n"

        in_top_univ = candidate_info['in_top_university']
        text += f"🎓 *ВУЗ ({resume['university']}):*\n"
        text += f"   {'✅ Входит в топ ВУЗы' if in_top_univ else '❌ Не входит в топ ВУЗы'}\n"
        text += f"   Топ ВУЗы: {', '.join(criteria['top_universities'][:3])}...\n\n"

        skills_list = [s.strip().lower() for s in resume['skills'].split(',')] if resume['skills'] else []
        matching_skills = []
        for skill in skills_list:
            if skill in [s.lower() for s in criteria['key_skills']]:
                matching_skills.append(skill)

        text += "💼 *Навыки:*\n"
        text += f"   Найдено ключевых: {len(matching_skills)} из {len(criteria['key_skills'])}\n"
        if matching_skills:
            text += f"   Совпавшие: {', '.join(matching_skills[:3])}"
            if len(matching_skills) > 3:
                text += "..."
        text += "\n\n"

        age = resume['age']
        has_experience = candidate_info['has_experience']
        text += f"📈 *Возраст/Опыт ({age}):*\n"
        text += f"   {'✅ Попадает в диапазон' if has_experience else '❌ Не попадает в диапазон'}\n"
        for exp in criteria['experience_ranges']:
            text += f"   {exp['min_age']}-{exp['max_age']} лет: {exp.get('label', '')}\n"
        text += "\n"

        matches = candidate_info['matches']
        category = candidate_info['category']
        category_name = {
            'green': '🟢 Подходящий',
            'yellow': '🟡 Резерв',
            'red': '🔴 Неподходящий'
        }.get(category, '⚪ Неизвестно')

        text += f"🎯 *Итог:* {matches}/3 совпадений\n"
        text += f"   Категория: {category_name}\n\n"

        if matches == 3:
            text += "💡 *Рекомендация:* Высокий приоритет, рекомендуется к собеседованию"
        elif matches >= 1:
            text += "💡 *Рекомендация:* Средний приоритет, рассмотреть при наличии вакансий"
        else:
            text += "💡 *Рекомендация:* Низкий приоритет, рассмотреть в последнюю очередь"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Общий дашборд", callback_data="admin_dashboard"),
                InlineKeyboardButton(text="🔙 К заявке", callback_data=f"admin_view_{resume_id}")
            ]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка анализа: {str(e)}")

    await callback.answer()
