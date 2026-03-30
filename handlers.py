import json
import logging
from typing import Any, Dict, List, Tuple

from telegram import (
    CallbackQuery,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from db import (
    add_admin,
    add_admin_by_username,
    check_admin,
    create_test,
    deactivate_test,
    get_active_tests,
    get_active_tests_count,
    get_admin,
    get_admin_by_id,
    get_all_admins,
    get_results_by_test_code,
    get_test_by_code,
    get_user_result,
    has_any_admin,
    reset_result,
    set_admin_super,
    upsert_result,
)
from keyboards import (
    admin_manage_admins_keyboard,
    admin_menu_inline_keyboard,
    admin_tests_stats_keyboard,
    answers_inline_keyboard,
    cancel_back_keyboard,
    resume_test_keyboard,
    role_selection_keyboard,
    start_test_keyboard,
    super_view_admins_keyboard,
    test_stats_button_keyboard,
)
from questions import QUESTIONS

logger = logging.getLogger(__name__)

# Conversation states
SELECTING_ROLE, ADMIN_MENU, ADMIN_VIEW_TESTS, ADMIN_CREATE_DESC, ADMIN_DELETE_CODE, ADMIN_ADD_ADMIN, ENTER_CODE, RESUME_OR_RESTART, INSTRUCTION_BEFORE_TEST, ASKING_QUESTIONS = range(
    10
)

INSTRUCTION_TEXT = (
    "Следует прочесть сначала первое предложение, затем – второе и после этого "
    "выбрать оценку, которая наиболее соответствует истине. При этом надо иметь "
    "в виду, что оценки означают:\n"
    "+3 – свойство, указанное в первом предложении, появляется в коллективе всегда;\n"
    "+2 – свойство проявляется в большинстве случаев;\n"
    "+1 – свойство появляется достаточно часто;\n"
    "0 – ни это, ни противоположное (указанное во втором предложении) свойство не "
    "проявляется достаточно ясно или то и другое проявляется в одинаковой степени;\n"
    "–1 – достаточно часто проявляется противоположное свойство (указанное во втором предложении);\n"
    "–2 – свойство проявляется в большинстве случаев;\n"
    "–3 – свойство проявляется всегда."
)

LEVELS_INFO: List[Dict[str, str]] = [
    {
        "min": 27,
        "max": 42,
        "label": "коллектив – «Горящий факел»",
        "description": (
            "5 ступень. «Горящий факел». Горящий факел – это живое пламя, "
            "горючим материалом которого является тесная дружба, единая воля, "
            "отличное взаимопонимание, деловое сотрудничество, ответственность "
            "каждого не только за себя, но и за других. Здесь ярко проявляются "
            "все качества коллектива, которые характерны для «Алого паруса». "
            "Но не только это. Светить можно и для себя, пробираясь сквозь "
            "заросли, поднимаясь на вершины, спускаясь в ущелья, пробивая "
            "первые тропы. Настоящим коллективом можно назвать лишь такую "
            "группу, которая не замыкается в узких рамках пусть и дружного, "
            "сплоченного объединения. Настоящий коллектив – тот, где люди сами "
            "видят, когда они нужны, и сами идут на помощь; тот, где не остаются "
            "равнодушными, если другим группам плохо; тот, который ведет за "
            "собой, освещая, подобно легендарному Данко, жаром своего "
            "пылающего сердца дорогу другим."
        ),
    },
    {
        "min": 10,
        "max": 26,
        "label": "автономия – «Алый парус»",
        "description": (
            "4 ступень. «Алый парус».\n"
            "Алый парус – символ устремлённости вперёд, неуспокоенности, "
            "дружеской верности, долга. Здесь живут и действуют по принципу "
            "«один за всех и все за одного». Дружеское участие и "
            "заинтересованность делами друг друга сочетаются с "
            "принципиальностью и взаимной требовательностью. Командный "
            "состав парусника – знающие и надёжные организаторы и авторитетные "
            "товарищи. К ним идут за советом, обращаются за помощью. У "
            "большинства членов «экипажа» проявляется чувство гордости за "
            "коллектив, все переживают, когда кого-то постигает неудача. "
            "Группа живо интересуется тем, как обстоят дела в соседних "
            "классах, отрядах, и иногда её члены приходят на помощь, когда их "
            "просят об этом. Хотя группа сплочена, однако она не всегда готова "
            "идти наперекор «бурям», не всегда хватает мужества признать "
            "ошибки сразу, но это положение может быть исправлено."
        ),
    },
    {
        "min": -7,
        "max": 9,
        "label": "кооперация – «Мерцающий маяк»",
        "description": (
            "3 ступень. «Мерцающий маяк».\n"
            "В штормящем море мерцающий маяк и начинающему, и опытному "
            "мореходу приносит уверенность, что курс выбран правильно. Важно "
            "только быть внимательным, не потерять световые всплески из виду. "
            "Заметьте, маяк не горит постоянным светом, а периодически "
            "выбрасывает пучки света, как бы говоря: «Я здесь, я готов прийти "
            "на помощь».\n"
            "Формирующийся в группе коллектив тоже подаёт каждому сигналы "
            "«так держать» и каждому готов прийти на помощь. В такой группе "
            "преобладает желание трудиться сообща, помогать друг другу, "
            "дружить. Но желание – это ещё не всё. Дружба, взаимопомощь "
            "требуют постоянного горения, а не одиночных, пусть даже очень "
            "частых вспышек. В то же время в группе уже есть на кого "
            "опереться. Авторитетны «смотрители маяка» – актив. Группа "
            "выделяется среди других своей индивидуальностью. Однако "
            "встречающиеся трудности часто прекращают деятельность группы, "
            "недостаточно проявляется инициатива, активность всплесками и не у "
            "всех."
        ),
    },
    {
        "min": -21,
        "max": -8,
        "label": "ассоциация – «Мягкая глина»",
        "description": (
            "2 ступень. «Мягкая глина».\n"
            "Известно, что мягкая глина – материал, который сравнительно "
            "легко поддаётся воздействию и из него можно лепить различные "
            "изделия. В руках хорошего мастера (а таким может быть в группе и "
            "формальный лидер детского объединения, и просто авторитетный "
            "школьник, и классный руководитель или руководитель кружка) этот "
            "материал превращается в красивый сосуд, в прекрасное изделие. Но "
            "если к нему не приложить усилий, то он может оставаться и простым "
            "куском глины.\n"
            "На этой ступени более заметны усилия по сплочению коллектива, "
            "хотя это могут быть только первые шаги. Не всё получается, нет "
            "достаточного опыта взаимодействия, взаимопомощи, достижение "
            "целей происходит с трудом. Скрепляющим звеном зачастую являются "
            "формальная дисциплина и требования старших. Отношения в основном "
            "доброжелательные, хотя нельзя сказать, что ребята всегда "
            "внимательны и предупредительны друг к другу. Существуют замкнутые "
            "приятельские группировки, которые мало общаются между собой. "
            "Настоящего, сильного организатора пока нет или ему трудно себя "
            "проявить, так как некому поддержать его."
        ),
    },
    {
        "min": -42,
        "max": -22,
        "label": "диффузная группа – «Песчаная россыпь»",
        "description": (
            "1 ступень. «Песчаная россыпь».\n"
            "Не так уж редко встречаются на нашем пути песчаные россыпи. "
            "Посмотришь – сколько песчинок собрано вместе, и в то же время "
            "каждая из них сама по себе. Подует ветерок – отнесёт часть песка, "
            "что лежит с краю, подальше, дунет ветер посильней – разнесёт песок "
            "в стороны, пока кто-нибудь не сгребёт его в кучу. Бывает так и в "
            "человеческих группах. Вроде все вместе, а в то же время каждый "
            "сам по себе. Нет «сцепления» между людьми. Люди не стремятся идти "
            "друг другу навстречу, не желают находить общие интересы и общий "
            "язык. Нет стержня, авторитетного центра, вокруг которого шло бы "
            "объединение и сплочение. Пока «песчаная россыпь» не приносит ни "
            "радости, ни удовлетворения тем, кто её составляет."
        ),
    },
]



def _clear_user_state(user_data: Dict[str, Any]) -> None:
    """Helper to clean per-conversation user data."""
    for key in [
        "role",
        "user_id",
        "test_code",
        "last_name",
        "answers",
        "current_question_index",
    ]:
        user_data.pop(key, None)


async def start(update: Update, context: CallbackContext) -> int:
    """Entry point: show role selection or handle deep link to test."""
    # Deep link: /start <6-digit code> — переход сразу к тестированию
    if (
        update.message
        and context.args
        and len(context.args) == 1
        and len(context.args[0]) == 6
        and context.args[0].isdigit()
    ):
        code = context.args[0].strip()
        user = update.effective_user
        if not user:
            await update.message.reply_text("Не удалось определить пользователя.")
            return ConversationHandler.END
        test = get_test_by_code(code)
        if not test or not test.get("is_active"):
            await update.message.reply_text(
                "Тестирование с таким кодом не найдено или уже завершено."
            )
            return ConversationHandler.END
        context.user_data["role"] = "Тестируемый"
        context.user_data["test_code"] = test["code"]
        context.user_data["user_id"] = user.id
        test_code = test["code"]
        existing = get_user_result(test_code, user.id)
        total_questions = len(QUESTIONS)
        if existing:
            raw_answers = existing.get("answers") or "[]"
            try:
                prev_answers: List[Dict[str, Any]] = json.loads(raw_answers)
            except json.JSONDecodeError:
                prev_answers = []
            is_completed = bool(existing.get("is_completed"))
            answered_count = len(prev_answers)
            if is_completed or answered_count >= total_questions:
                total_score = 0.0
                for a in prev_answers:
                    try:
                        total_score += float(a.get("value", 0))
                    except (TypeError, ValueError):
                        continue
                level_label, level_description = _level_by_score(total_score)
                result_text = (
                    "Спасибо! Ваши ответы успешно сохранены.\n\n"
                    f"Ваша оценка отряда: {total_score:.2f}\n"
                    f"Эта оценка соответствует ступени – {level_label}.\n\n"
                    f"{level_description}\n\n"
                    "Для нового тестирования или смены роли используйте команду /start."
                )
                await update.message.reply_text(
                    result_text,
                    reply_markup=ReplyKeyboardRemove(),
                )
                await update.message.reply_text(
                    "Вы можете посмотреть общую статистику по этому тестированию:",
                    reply_markup=test_stats_button_keyboard(test_code),
                )
                _clear_user_state(context.user_data)
                return ConversationHandler.END
            if answered_count > 0:
                context.user_data["answers"] = prev_answers
                context.user_data["current_question_index"] = answered_count
                await update.message.reply_text(
                    f"Вы уже начинали это тестирование (отвечено {answered_count} "
                    f"из {total_questions} вопросов).\n"
                    "Продолжить или начать заново?",
                    reply_markup=resume_test_keyboard(),
                )
                return RESUME_OR_RESTART
        context.user_data["answers"] = []
        context.user_data["current_question_index"] = 0
        desc = test.get("description", "") or ""
        await update.message.reply_text(
            f"Код принят.\nПройдите тестирование {desc} ({test_code})\n\n"
            "Перед началом ознакомьтесь с инструкцией:",
            reply_markup=cancel_back_keyboard(),
        )
        await update.message.reply_text(
            INSTRUCTION_TEXT,
            reply_markup=start_test_keyboard(),
        )
        return INSTRUCTION_BEFORE_TEST

    _clear_user_state(context.user_data)
    if update.message:
        await update.message.reply_text(
            "Здравствуйте! Выберите свою роль:",
            reply_markup=role_selection_keyboard(),
        )
    else:
        logger.warning("start called without message object.")

    return SELECTING_ROLE


async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel the conversation."""
    _clear_user_state(context.user_data)
    if update.message:
        await update.message.reply_text(
            "Диалог отменён. Для начала заново используйте команду /start.",
            reply_markup=ReplyKeyboardRemove(),
        )
    elif update.callback_query:
        query: CallbackQuery = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "Диалог отменён. Для начала заново используйте команду /start."
        )

    return ConversationHandler.END


def _is_cancel(text: str) -> bool:
    return text.lower() == "отмена"


def _is_back(text: str) -> bool:
    return text.lower() == "назад"


async def select_role(update: Update, context: CallbackContext) -> int:
    """Handle role selection: Administrator or Test Subject."""
    if not update.message:
        return SELECTING_ROLE

    text = (update.message.text or "").strip()

    if _is_cancel(text):
        return await cancel(update, context)

    if text not in ("Администратор", "Тестируемый"):
        await update.message.reply_text(
            "Пожалуйста, выберите роль, используя кнопки ниже.",
            reply_markup=role_selection_keyboard(),
        )
        return SELECTING_ROLE

    context.user_data["role"] = text

    if text == "Администратор":
        user = update.effective_user
        if not user:
            await update.message.reply_text(
                "Не удалось определить пользователя. Попробуйте позже."
            )
            return SELECTING_ROLE

        is_admin = check_admin(user.id, user.username)
        if not is_admin:
            await update.message.reply_text(
                "У вас нет прав администратора. "
                "Если вы первый настраиваете бота, отправьте команду /addadmin, "
                "чтобы назначить себя первым администратором. "
                "В противном случае обратитесь к существующему администратору "
                "или выберите роль 'Тестируемый'.",
                reply_markup=role_selection_keyboard(),
            )
            _clear_user_state(context.user_data)
            return SELECTING_ROLE

        admin_row = get_admin(user.id)
        is_super = bool(admin_row.get("is_super")) if admin_row else False
        context.user_data["is_super_admin"] = is_super

        # Show admin menu
        await update.message.reply_text(
            "Добро пожаловать в меню администратора.",
            reply_markup=cancel_back_keyboard(),
        )
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=admin_menu_inline_keyboard(
                show_super_actions=context.user_data.get("is_super_admin", False)
            ),
        )
        return ADMIN_MENU

    # Role "Тестируемый"
    await update.message.reply_text(
        "Пожалуйста, введите 6-значный код тестирования.",
        reply_markup=cancel_back_keyboard(),
    )
    return ENTER_CODE


async def admin_menu_callback(update: Update, context: CallbackContext) -> int:
    """Handle administrator inline menu actions."""
    if not update.callback_query:
        return ADMIN_MENU

    query: CallbackQuery = update.callback_query
    data = query.data or ""
    await query.answer()

    if data == "admin_view_tests":
        admin_user_id = update.effective_user.id if update.effective_user else None
        tests = get_active_tests(owner_user_id=admin_user_id) if admin_user_id else []
        if not tests:
            text = "Активных тестирований сейчас нет."
        else:
            lines: List[str] = [
                f"Текущие активные тестирования ({admin_user_id}):"
            ]
            for t in tests:
                created_at = t.get("created_at") or ""
                lines.append(
                    f"- Код: {t.get('code')} | "
                    f"Описание: {t.get('description') or '-'} | "
                    f"Создано: {created_at}"
                )
            text = "\n".join(lines)

        await query.edit_message_text(text)
        # Offer per-test statistics and "Назад"
        if query.message and query.message.chat:
            if tests:
                await query.message.reply_text(
                    "Выберите тестирование для просмотра подробной статистики:",
                    reply_markup=admin_tests_stats_keyboard(tests),
                )
            await query.message.reply_text(
                "Чтобы вернуться в меню администратора, нажмите 'Назад'.",
                reply_markup=cancel_back_keyboard(),
            )
        return ADMIN_VIEW_TESTS

    if data == "admin_create_test":
        if query.message and query.message.chat:
            await query.message.reply_text(
                "Введите краткое описание нового тестирования.",
                reply_markup=cancel_back_keyboard(),
            )
        return ADMIN_CREATE_DESC

    if data == "admin_delete_test":
        if query.message and query.message.chat:
            await query.message.reply_text(
                "Введите 6-значный код тестирования, которое нужно удалить "
                "(деактивировать).",
                reply_markup=cancel_back_keyboard(),
            )
        return ADMIN_DELETE_CODE

    if data == "admin_manage_admins":
        # Only super admins can manage other admins
        if not context.user_data.get("is_super_admin"):
            await query.edit_message_text(
                "У вас нет прав для управления администраторами."
            )
            return ADMIN_MENU

        admins = get_all_admins()
        if not admins:
            await query.edit_message_text("Администраторы не найдены.")
            return ADMIN_MENU

        lines_list: List[str] = ["Список администраторов (кнопки меняют роль):"]
        for num, a in enumerate(admins, 1):
            username = a.get("username") or "-"
            uid = a.get("user_id") or "-"
            role = "Суперадмин" if a.get("is_super") else "Обычный админ"
            lines_list.append(f"{num}. {username} ({uid}) — {role}")

        await query.edit_message_text(
            "\n".join(lines_list),
            reply_markup=admin_manage_admins_keyboard(admins),
        )
        return ADMIN_MENU

    # Переключение роли админа: суперадмин / обычный
    if data.startswith("admin_set_super_"):
        if not context.user_data.get("is_super_admin"):
            await query.answer("Нет прав.")
            return ADMIN_MENU
        try:
            admin_id = int(data.split("_", 3)[3])
        except (ValueError, IndexError):
            await query.answer("Ошибка.")
            return ADMIN_MENU
        if set_admin_super(admin_id, True):
            await query.answer("Суперадмин назначен.")
        else:
            await query.answer("Не удалось изменить.")
        admins = get_all_admins()
        if admins:
            lines_list = ["Список администраторов (кнопки меняют роль):"]
            for num, a in enumerate(admins, 1):
                username = a.get("username") or "-"
                uid = a.get("user_id") or "-"
                role = "Суперадмин" if a.get("is_super") else "Обычный админ"
                lines_list.append(f"{num}. {username} ({uid}) — {role}")
            await query.edit_message_text(
                "\n".join(lines_list),
                reply_markup=admin_manage_admins_keyboard(admins),
            )
        return ADMIN_MENU

    if data.startswith("admin_set_normal_"):
        if not context.user_data.get("is_super_admin"):
            await query.answer("Нет прав.")
            return ADMIN_MENU
        try:
            admin_id = int(data.split("_", 3)[3])
        except (ValueError, IndexError):
            await query.answer("Ошибка.")
            return ADMIN_MENU
        if set_admin_super(admin_id, False):
            await query.answer("Теперь обычный админ.")
        else:
            await query.answer("Не удалось изменить.")
        admins = get_all_admins()
        if admins:
            lines_list = ["Список администраторов (кнопки меняют роль):"]
            for num, a in enumerate(admins, 1):
                username = a.get("username") or "-"
                uid = a.get("user_id") or "-"
                role = "Суперадмин" if a.get("is_super") else "Обычный админ"
                lines_list.append(f"{num}. {username} ({uid}) — {role}")
            await query.edit_message_text(
                "\n".join(lines_list),
                reply_markup=admin_manage_admins_keyboard(admins),
            )
        return ADMIN_MENU

    if data == "admin_add_admin":
        if query.message and query.message.chat:
            await query.message.reply_text(
                "Введите ник нового администратора (можно с @).\n"
                "Пример: @username",
                reply_markup=cancel_back_keyboard(),
            )
        return ADMIN_ADD_ADMIN

    return ADMIN_MENU


async def super_view_callback(update: Update, context: CallbackContext) -> int:
    """
    Handle «Просмотр тестирований пользователя» for super admin:
    show list of admins with test counts, then tests of selected admin.
    """
    if not update.callback_query:
        return ADMIN_MENU

    query: CallbackQuery = update.callback_query
    data = query.data or ""
    await query.answer()

    if data == "super_view_admins_tests":
        admins = get_all_admins()
        if not admins:
            await query.edit_message_text("Администраторы не найдены.")
            return ADMIN_MENU

        admins_with_counts: List[Tuple[Dict[str, Any], int]] = []
        lines_list: List[str] = ["Список администраторов и количество созданных тестов:"]
        for num, a in enumerate(admins, 1):
            uid = a.get("user_id")
            count = get_active_tests_count(uid) if uid is not None else 0
            admins_with_counts.append((a, count))
            username = a.get("username") or "-"
            uid_display = uid if uid is not None else "-"
            lines_list.append(f"{num}. {username} ({uid_display}) — тестов: {count}")

        await query.edit_message_text(
            "\n".join(lines_list),
            reply_markup=super_view_admins_keyboard(admins_with_counts),
        )
        return ADMIN_MENU

    if data.startswith("super_view_tests_"):
        try:
            admin_id = int(data.split("_", 3)[3])
        except (ValueError, IndexError):
            await query.edit_message_text("Ошибка выбора администратора.")
            return ADMIN_MENU

        admin = get_admin_by_id(admin_id)
        if not admin:
            await query.edit_message_text("Администратор не найден.")
            return ADMIN_MENU

        owner_user_id = admin.get("user_id")
        tests = get_active_tests(owner_user_id=owner_user_id) if owner_user_id is not None else []

        if not tests:
            text = "У этого администратора нет активных тестирований."
        else:
            lines_list = [
                f"Текущие активные тестирования ({owner_user_id}):"
            ]
            for t in tests:
                created_at = t.get("created_at") or ""
                lines_list.append(
                    f"- Код: {t.get('code')} | "
                    f"Описание: {t.get('description') or '-'} | "
                    f"Создано: {created_at}"
                )
            text = "\n".join(lines_list)

        await query.edit_message_text(text)
        if query.message and query.message.chat:
            if tests:
                await query.message.reply_text(
                    "Выберите тестирование для просмотра подробной статистики:",
                    reply_markup=admin_tests_stats_keyboard(tests),
                )
            await query.message.reply_text(
                "Чтобы вернуться в меню администратора, нажмите 'Назад'.",
                reply_markup=cancel_back_keyboard(),
            )
        return ADMIN_VIEW_TESTS

    return ADMIN_MENU


async def admin_view_back(update: Update, context: CallbackContext) -> int:
    """Return from tests view to admin menu."""
    if not update.message:
        return ADMIN_VIEW_TESTS

    text = (update.message.text or "").strip()

    if _is_cancel(text):
        return await cancel(update, context)

    if _is_back(text):
        await update.message.reply_text(
            "Меню администратора:",
            reply_markup=cancel_back_keyboard(),
        )
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=admin_menu_inline_keyboard(
                show_super_actions=context.user_data.get("is_super_admin", False)
            ),
        )
        return ADMIN_MENU

    await update.message.reply_text(
        "Используйте кнопку 'Назад' для возврата в меню администратора."
    )
    return ADMIN_VIEW_TESTS


async def admin_create_desc(update: Update, context: CallbackContext) -> int:
    """Handle entering description for new test."""
    if not update.message:
        return ADMIN_CREATE_DESC

    text = (update.message.text or "").strip()

    if _is_cancel(text):
        return await cancel(update, context)

    if _is_back(text):
        await update.message.reply_text(
            "Возврат в меню администратора.",
        )
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=admin_menu_inline_keyboard(
                show_super_actions=context.user_data.get("is_super_admin", False)
            ),
        )
        return ADMIN_MENU

    if not text:
        await update.message.reply_text(
            "Описание не может быть пустым. Введите краткое описание."
        )
        return ADMIN_CREATE_DESC

    admin_user_id = update.effective_user.id if update.effective_user else None
    code = create_test(text, owner_user_id=admin_user_id)
    if not code:
        await update.message.reply_text(
            "Не удалось создать тестирование. Попробуйте позже."
        )
        return ADMIN_MENU

    await update.message.reply_text(
        f"Создано новое тестирование.\nКод: {code}\nОписание: {text}",
        reply_markup=cancel_back_keyboard(),
    )
    bot_username = (context.bot.username or "").strip()
    if bot_username:
        link = f"https://t.me/{bot_username}?start={code}"
        await update.message.reply_text(
            f"Ссылка для прохождения тестирования:\n{link}",
            reply_markup=cancel_back_keyboard(),
        )
    await update.message.reply_text(
        "Меню администратора:",
        reply_markup=admin_menu_inline_keyboard(
            show_super_actions=context.user_data.get("is_super_admin", False)
        ),
    )
    return ADMIN_MENU


async def admin_delete_code(update: Update, context: CallbackContext) -> int:
    """Handle entering test code to delete (deactivate) a test."""
    if not update.message:
        return ADMIN_DELETE_CODE

    text = (update.message.text or "").strip()

    if _is_cancel(text):
        return await cancel(update, context)

    if _is_back(text):
        await update.message.reply_text(
            "Возврат в меню администратора.",
            reply_markup=cancel_back_keyboard(),
        )
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=admin_menu_inline_keyboard(
                show_super_actions=context.user_data.get("is_super_admin", False)
            ),
        )
        return ADMIN_MENU

    if len(text) != 6 or not text.isdigit():
        await update.message.reply_text(
            "Код должен содержать 6 цифр. Попробуйте ещё раз."
        )
        return ADMIN_DELETE_CODE

    code = text
    test = get_test_by_code(code)
    if not test or not test.get("is_active"):
        await update.message.reply_text(
            "Активное тестирование с таким кодом не найдено. "
            "Проверьте код и попробуйте снова."
        )
        return ADMIN_DELETE_CODE

    admin_user_id = update.effective_user.id if update.effective_user else None
    ok = deactivate_test(code, owner_user_id=admin_user_id)
    if ok:
        await update.message.reply_text(
            f"Тестирование с кодом {code} было деактивировано (удалено) и больше "
            f"не будет доступно для прохождения.",
            reply_markup=cancel_back_keyboard(),
        )
    else:
        await update.message.reply_text(
            "Не удалось деактивировать тестирование. Попробуйте позже.",
            reply_markup=cancel_back_keyboard(),
        )

    await update.message.reply_text(
        "Меню администратора:",
        reply_markup=admin_menu_inline_keyboard(
            show_super_actions=context.user_data.get("is_super_admin", False)
        ),
    )
    return ADMIN_MENU


async def admin_add_admin_text(update: Update, context: CallbackContext) -> int:
    """Handle text input for adding a new administrator from admin menu."""
    if not update.message:
        return ADMIN_ADD_ADMIN

    text = (update.message.text or "").strip()

    if _is_cancel(text):
        return await cancel(update, context)

    if _is_back(text):
        await update.message.reply_text(
            "Возврат в меню администратора.",
            reply_markup=cancel_back_keyboard(),
        )
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=admin_menu_inline_keyboard(
                show_super_actions=context.user_data.get("is_super_admin", False)
            ),
        )
        return ADMIN_MENU

    username = text
    if username.startswith("@"):
        username = username[1:]

    if not username:
        await update.message.reply_text(
            "Ник не может быть пустым. Введите ник (например: @username)."
        )
        return ADMIN_ADD_ADMIN

    try:
        add_admin_by_username(username)
    except Exception:
        await update.message.reply_text(
            "Не удалось добавить администратора. Проверьте данные и попробуйте снова."
        )
        return ADMIN_ADD_ADMIN

    await update.message.reply_text(
        f"Администратор с ником @{username} добавлен.\n"
        "Когда этот пользователь впервые войдёт к боту и выберет роль "
        "«Администратор», его учётная запись будет активирована.",
        reply_markup=cancel_back_keyboard(),
    )
    await update.message.reply_text(
        "Меню администратора:",
        reply_markup=admin_menu_inline_keyboard(
            show_super_actions=context.user_data.get("is_super_admin", False)
        ),
    )
    return ADMIN_MENU


async def admin_test_stats(update: Update, context: CallbackContext) -> int:
    """Show detailed statistics for a selected test (by code)."""
    if not update.callback_query:
        return ADMIN_VIEW_TESTS

    query: CallbackQuery = update.callback_query
    data = query.data or ""
    await query.answer()

    prefix = "admin_stats_"
    if not data.startswith(prefix):
        return ADMIN_VIEW_TESTS

    code = data[len(prefix) :]
    if not code:
        await query.edit_message_text("Не удалось определить код тестирования.")
        return ADMIN_VIEW_TESTS

    test = get_test_by_code(code)
    if not test:
        await query.edit_message_text(
            "Тестирование с таким кодом не найдено."
        )
        return ADMIN_VIEW_TESTS

    results = get_results_by_test_code(code)
    if not results:
        await query.edit_message_text(
            f"Для тестирования с кодом {code} ещё нет ни одного результата."
        )
        bot_username = (context.bot.username or "").strip()
        if bot_username:
            link = f"https://t.me/{bot_username}?start={code}"
            await query.message.reply_text(
                f"Ссылка для прохождения тестирования: {link}"
            )
        return ADMIN_VIEW_TESTS

    # Aggregate statistics
    started_count = len(results)
    completed_sums: List[float] = []
    details_lines: List[str] = []

    for r in results:
        answers_raw = r.get("answers") or "[]"
        try:
            answers_list: List[Dict[str, Any]] = json.loads(answers_raw)
        except json.JSONDecodeError:
            answers_list = []

        count_answers = len(answers_list)
        sum_value = 0.0
        for a in answers_list:
            try:
                # Суммируем реальные значения (+3 ... -3) без модуля.
                sum_value += float(a.get("value", 0))
            except (TypeError, ValueError):
                continue

        is_completed = bool(r.get("is_completed"))
        if is_completed and count_answers > 0:
            completed_sums.append(sum_value)

        status = "завершено" if is_completed else "не завершено"
        details_lines.append(
            f"- user_id={r.get('user_id')} | "
            f"ответов: {count_answers} | сумма: {sum_value:.2f} | "
            f"статус: {status}"
        )

    completed_count = len(completed_sums)
    if completed_count > 0:
        avg_level = sum(completed_sums) / completed_count
        avg_text = f"{avg_level:.2f}"
    else:
        avg_text = "нет завершённых тестирований"

    text_lines: List[str] = [
        f"Статистика по тестированию с кодом {code}:",
        f"Описание: {test.get('description') or '-'}",
        "",
        f"Средний уровень по всем завершённым тестированиям: {avg_text}",
        f"Начали тестирование: {started_count}",
        f"Завершили тестирование: {completed_count}",
        "",
        "Подробности по каждому участнику:",
        *details_lines,
    ]

    await query.edit_message_text("\n".join(text_lines))
    bot_username = (context.bot.username or "").strip()
    if bot_username:
        link = f"https://t.me/{bot_username}?start={code}"
        await query.message.reply_text(
            f"Ссылка для прохождения тестирования: {link}"
        )
    return ADMIN_VIEW_TESTS


def _level_by_score(score: float) -> Tuple[str, str]:
    """Return (level_label, level_description) for given total score."""
    for lvl in LEVELS_INFO:
        if lvl["min"] <= score <= lvl["max"]:
            return (lvl["label"], lvl["description"])
    return ("не определена", "")


async def show_public_test_stats(update: Update, context: CallbackContext) -> None:
    """
    Show general test statistics for test-takers (no per-participant details).
    Called when user presses «Общая статистика по тестированию» after completing.
    """
    if not update.callback_query:
        return

    query: CallbackQuery = update.callback_query
    data = query.data or ""
    await query.answer()

    prefix = "test_stats_"
    if not data.startswith(prefix):
        return

    code = data[len(prefix) :].strip()
    if not code:
        await query.edit_message_text("Не удалось определить код тестирования.")
        return

    test = get_test_by_code(code)
    if not test:
        await query.edit_message_text(
            "Тестирование с таким кодом не найдено."
        )
        return

    results = get_results_by_test_code(code)
    started_count = len(results)
    completed_sums: List[float] = []

    for r in results:
        answers_raw = r.get("answers") or "[]"
        try:
            answers_list: List[Dict[str, Any]] = json.loads(answers_raw)
        except json.JSONDecodeError:
            answers_list = []
        sum_value = 0.0
        for a in answers_list:
            try:
                sum_value += float(a.get("value", 0))
            except (TypeError, ValueError):
                continue
        if bool(r.get("is_completed")) and answers_list:
            completed_sums.append(sum_value)

    completed_count = len(completed_sums)
    desc = test.get("description") or "–"

    if completed_count > 0:
        avg = sum(completed_sums) / completed_count
        level_label, level_description = _level_by_score(avg)
        stats_text = (
            f"Статистика по тестированию с кодом: {code}\n"
            f"Описание: {desc}\n\n"
            f"Начали тестирование: {started_count}\n"
            f"Завершили тестирование: {completed_count}\n\n"
            f"Средняя оценка отряда: {avg:.2f}\n"
            f"Эта оценка соответствует ступени – {level_label}\n\n"
            f"{level_description}"
        )
    else:
        stats_text = (
            f"Статистика по тестированию с кодом: {code}\n"
            f"Описание: {desc}\n\n"
            f"Начали тестирование: {started_count}\n"
            f"Завершили тестирование: {completed_count}\n\n"
            "Средняя оценка отряда: нет завершённых тестирований."
        )

    await query.edit_message_text(stats_text)


async def enter_test_code(update: Update, context: CallbackContext) -> int:
    """Handle entering test code by test subject."""
    if not update.message:
        return ENTER_CODE

    text = (update.message.text or "").strip()
    user = update.effective_user

    if _is_cancel(text):
        return await cancel(update, context)

    if _is_back(text):
        # Go back to role selection
        _clear_user_state(context.user_data)
        await update.message.reply_text(
            "Вы вернулись в стартовое меню. Выберите роль:",
            reply_markup=role_selection_keyboard(),
        )
        return SELECTING_ROLE

    if not user:
        await update.message.reply_text(
            "Не удалось определить пользователя. Попробуйте позже."
        )
        return ENTER_CODE

    if len(text) != 6 or not text.isdigit():
        await update.message.reply_text(
            "Код должен содержать 6 цифр. Попробуйте ещё раз."
        )
        return ENTER_CODE

    test = get_test_by_code(text.upper())
    if not test or not test.get("is_active"):
        await update.message.reply_text(
            "Тестирование с таким кодом не найдено или уже завершено. "
            "Проверьте код и попробуйте снова."
        )
        return ENTER_CODE

    test_code = test["code"]
    context.user_data["test_code"] = test_code
    context.user_data["user_id"] = user.id

    # Check existing progress for this user and test
    existing = get_user_result(test_code, user.id)
    total_questions = len(QUESTIONS)

    if existing:
        raw_answers = existing.get("answers") or "[]"
        try:
            prev_answers: List[Dict[str, Any]] = json.loads(raw_answers)
        except json.JSONDecodeError:
            prev_answers = []

        is_completed = bool(existing.get("is_completed"))
        answered_count = len(prev_answers)

        if is_completed or answered_count >= total_questions:
            total_score = 0.0
            for a in prev_answers:
                try:
                    total_score += float(a.get("value", 0))
                except (TypeError, ValueError):
                    continue
            level_label, level_description = _level_by_score(total_score)
            result_text = (
                "Спасибо! Ваши ответы успешно сохранены.\n\n"
                f"Ваша оценка отряда: {total_score:.2f}\n"
                f"Эта оценка соответствует ступени – {level_label}.\n\n"
                f"{level_description}\n\n"
                "Для нового тестирования или смены роли используйте команду /start."
            )
            await update.message.reply_text(
                result_text,
                reply_markup=ReplyKeyboardRemove(),
            )
            await update.message.reply_text(
                "Вы можете посмотреть общую статистику по этому тестированию:",
                reply_markup=test_stats_button_keyboard(test_code),
            )
            _clear_user_state(context.user_data)
            return ConversationHandler.END

        if answered_count > 0:
            # Offer resume or restart
            context.user_data["answers"] = prev_answers
            context.user_data["current_question_index"] = answered_count
            await update.message.reply_text(
                f"Вы уже начали это тестирование (отвечено {answered_count} "
                f"из {total_questions} вопросов).\n"
                "Вы хотите продолжить или начать заново?",
                reply_markup=resume_test_keyboard(),
            )
            return RESUME_OR_RESTART

    # New attempt: show instructions before first question
    context.user_data["answers"] = []
    context.user_data["current_question_index"] = 0
    desc = test.get("description", "") or ""
    await update.message.reply_text(
        f"Код принят.\nПройдите тестирование {desc} ({test_code})\n\n"
        "Перед началом ознакомьтесь с инструкцией:",
        reply_markup=cancel_back_keyboard(),
    )
    await update.message.reply_text(
        INSTRUCTION_TEXT,
        reply_markup=start_test_keyboard(),
    )
    return INSTRUCTION_BEFORE_TEST


async def ask_next_question(update: Update, context: CallbackContext) -> int:
    """
    Ask the next question in the list.
    Returns ASKING_QUESTIONS or ends the conversation if no more questions.
    """
    idx = context.user_data.get("current_question_index", 0)
    if idx >= len(QUESTIONS):
        # No more questions - finalize
        return await finish_testing(update, context)

    question = QUESTIONS[idx]
    num = idx + 1
    message_text = (
        f"Вопрос #{num}\n\n"
        f"⬆️ {question['left']} ⬆️\n\n"
        f"⬇️ {question['right']} ⬇️"
    )

    # For callback query continue in same chat
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.message:
            await query.message.reply_text(
                message_text,
                reply_markup=answers_inline_keyboard(),
            )
    elif update.message:
        await update.message.reply_text(
            message_text,
            reply_markup=answers_inline_keyboard(),
        )

    return ASKING_QUESTIONS


async def handle_answer(update: Update, context: CallbackContext) -> int:
    """Handle answer (1-5) for current question."""
    if not update.callback_query:
        return ASKING_QUESTIONS

    query: CallbackQuery = update.callback_query
    data = query.data or ""
    await query.answer()

    if not data.startswith("answer_"):
        return ASKING_QUESTIONS

    try:
        value = int(data.split("_", maxsplit=1)[1])
    except (ValueError, IndexError):
        logger.warning("Invalid answer callback data: %s", data)
        return ASKING_QUESTIONS

    answers: List[Dict[str, Any]] = context.user_data.get("answers", [])
    idx = context.user_data.get("current_question_index", 0)
    test_code = context.user_data.get("test_code")
    user_id = context.user_data.get("user_id")

    if idx >= len(QUESTIONS):
        # Unexpected state but try to finish
        return await finish_testing(update, context)

    question = QUESTIONS[idx]
    # For saved result keep a short text description of the question
    question_text = f"{idx + 1}. {question['left']} | {question['right']}"
    answers.append(
        {
            "id": question["id"],
            "text": question_text,
            "value": value,
        }
    )
    context.user_data["answers"] = answers
    context.user_data["current_question_index"] = idx + 1

    # Save partial progress
    if test_code and user_id:
        answers_json = json.dumps(answers, ensure_ascii=False)
        upsert_result(
            test_code=test_code,
            user_id=user_id,
            answers_json=answers_json,
            is_completed=False,
        )

    # Acknowledge and ask next question
    await query.edit_message_text(
        f"Ваш ответ: {value}.",  # keep previous question text in history
    )
    return await ask_next_question(update, context)


async def questions_cancel_or_back(update: Update, context: CallbackContext) -> int:
    """
    Allow user to cancel or go back during questions.
    For simplicity, both lead to full cancellation and restart suggestion.
    """
    if not update.message:
        return ASKING_QUESTIONS

    text = (update.message.text or "").strip()

    if _is_cancel(text) or _is_back(text):
        return await cancel(update, context)

    await update.message.reply_text(
        "Чтобы прервать тестирование, используйте 'Отмена'."
    )
    return ASKING_QUESTIONS


async def instruction_before_test(update: Update, context: CallbackContext) -> int:
    """Handle confirmation to start the test after showing instructions."""
    if not update.message:
        return INSTRUCTION_BEFORE_TEST

    text = (update.message.text or "").strip()

    if _is_cancel(text):
        return await cancel(update, context)

    if text == "Приступить к тестированию":
        await update.message.reply_text(
            "Начинаем тестирование.",
            reply_markup=cancel_back_keyboard(),
        )
        return await ask_next_question(update, context)

    await update.message.reply_text(
        "Пожалуйста, используйте кнопку 'Приступить к тестированию' или 'Отмена'.",
        reply_markup=start_test_keyboard(),
    )
    return INSTRUCTION_BEFORE_TEST


async def resume_or_restart_test(update: Update, context: CallbackContext) -> int:
    """Handle choice to resume or restart an already-started test."""
    if not update.message:
        return RESUME_OR_RESTART

    text = (update.message.text or "").strip()

    if _is_cancel(text):
        return await cancel(update, context)

    test_code = context.user_data.get("test_code")
    user_id = context.user_data.get("user_id")

    if text == "Продолжить":
        if test_code is None or user_id is None:
            await update.message.reply_text(
                "Не удалось восстановить состояние тестирования. Попробуйте снова.",
                reply_markup=ReplyKeyboardRemove(),
            )
            _clear_user_state(context.user_data)
            return ConversationHandler.END

        await update.message.reply_text(
            "Продолжаем тестирование.",
            reply_markup=cancel_back_keyboard(),
        )
        return await ask_next_question(update, context)

    if text == "Начать заново":
        if test_code and user_id:
            reset_result(test_code, user_id)

        context.user_data["answers"] = []
        context.user_data["current_question_index"] = 0
        await update.message.reply_text(
            "Перед началом, пожалуйста, внимательно ознакомьтесь с инструкцией "
            "по прохождению тестирования:",
        )
        await update.message.reply_text(
            INSTRUCTION_TEXT,
            reply_markup=start_test_keyboard(),
        )
        return INSTRUCTION_BEFORE_TEST

    await update.message.reply_text(
        "Пожалуйста, выберите один из вариантов: 'Продолжить', 'Начать заново' или 'Отмена'.",
        reply_markup=resume_test_keyboard(),
    )
    return RESUME_OR_RESTART


async def finish_testing(update: Update, context: CallbackContext) -> int:
    """Finalize testing: save result and show thank you message."""
    test_code = context.user_data.get("test_code")
    user_id = context.user_data.get("user_id")
    answers = context.user_data.get("answers", [])

    if not (test_code and user_id and answers):
        logger.warning(
            "Incomplete data for saving result: test_code=%s, user_id=%s, answers_len=%s",
            test_code,
            user_id,
            len(answers) if isinstance(answers, list) else "n/a",
        )
        if update.effective_message:
            await update.effective_message.reply_text(
                "Произошла ошибка при сохранении результатов. Попробуйте позже."
            )
        _clear_user_state(context.user_data)
        return ConversationHandler.END

    answers_json = json.dumps(answers, ensure_ascii=False)

    # Sum all answers for this attempt
    total_score = 0.0
    for a in answers:
        try:
            total_score += float(a.get("value", 0))
        except (TypeError, ValueError):
            continue

    # Determine level info by total score
    level_label = "не определена"
    level_description = ""
    for lvl in LEVELS_INFO:
        if lvl["min"] <= total_score <= lvl["max"]:
            level_label = lvl["label"]
            level_description = lvl["description"]
            break

    # Use Telegram last_name just for storing in DB (optional)
    telegram_last_name = ""
    if update.effective_user and update.effective_user.last_name:
        telegram_last_name = update.effective_user.last_name

    ok = upsert_result(
        test_code=test_code,
        user_id=user_id,
        answers_json=answers_json,
        is_completed=True,
        last_name=telegram_last_name,
    )

    if update.effective_message:
        if ok:
            result_text = (
                "Спасибо! Ваши ответы успешно сохранены.\n\n"
                f"Ваша оценка отряда: {total_score:.2f}\n"
                f"Эта оценка соответствует ступени – {level_label}.\n\n"
                f"{level_description}\n\n"
                "Для нового тестирования или смены роли используйте команду /start."
            )
            await update.effective_message.reply_text(
                result_text,
                reply_markup=ReplyKeyboardRemove(),
            )
            await update.effective_message.reply_text(
                "Вы можете посмотреть общую статистику по этому тестированию:",
                reply_markup=test_stats_button_keyboard(test_code),
            )
        else:
            await update.effective_message.reply_text(
                "Не удалось сохранить результаты. Попробуйте позже.",
                reply_markup=ReplyKeyboardRemove(),
            )

    _clear_user_state(context.user_data)
    return ConversationHandler.END


async def add_admin_command(update: Update, context: CallbackContext) -> None:
    """
    /addadmin command.

    - If there are no admins yet, the user who calls this command becomes the first admin.
    - If admins already exist:
        - Only existing admins can add new admins.
        - Usage: /addadmin <user_id> [username]
    """
    if not update.message:
        return

    user = update.effective_user
    if not user:
        await update.message.reply_text("Не удалось определить пользователя.")
        return

    try:
        any_admins = has_any_admin()
    except Exception:
        logger.exception("Failed to check admins presence in /addadmin.")
        await update.message.reply_text(
            "Ошибка при проверке администраторов. Попробуйте позже."
        )
        return

    # Case 1: no admins yet -> current user becomes first superadmin
    if not any_admins:
        try:
            add_admin(user.id, user.username, is_super=True)
        except Exception:
            await update.message.reply_text(
                "Не удалось добавить вас как администратора. Попробуйте позже."
            )
            return

        uname = f"\nusername: @{user.username}" if user.username else ""
        await update.message.reply_text(
            f"Вы назначены первым администратором (суперадмин).\n"
            f"user_id: {user.id}{uname}"
        )
        return

    # Case 2: admins already exist -> only admin can add new admins
    if not check_admin(user.id, user.username):
        await update.message.reply_text(
            "Добавлять новых администраторов могут только существующие администраторы."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Использование: /addadmin <user_id> [username]\n"
            "user_id можно посмотреть, например, через ботов типа @userinfobot."
        )
        return

    new_user_id_text = context.args[0]
    try:
        new_user_id = int(new_user_id_text)
    except ValueError:
        await update.message.reply_text("user_id должен быть числом.")
        return

    new_username = context.args[1] if len(context.args) > 1 else None
    if new_username and new_username.startswith("@"):
        new_username = new_username[1:]

    try:
        add_admin(new_user_id, new_username)
    except Exception:
        await update.message.reply_text(
            "Не удалось добавить администратора. Проверьте данные и попробуйте снова."
        )
        return

    # Check if admin now exists
    if check_admin(new_user_id):
        await update.message.reply_text(
            f"Пользователь с user_id={new_user_id} "
            f"успешно добавлен в администраторы."
        )
    else:
        await update.message.reply_text(
            "Возможно, администратор с таким user_id уже существует, "
            "или произошла ошибка при добавлении."
        )


def build_conversation_handler(application: Application) -> ConversationHandler:
    """
    Build and return ConversationHandler with all states and handlers registered.

    The returned handler should be added to the application in main.py.
    """
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_ROLE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    select_role,
                )
            ],
            ADMIN_MENU: [
                CallbackQueryHandler(admin_menu_callback, pattern=r"^admin_"),
                CallbackQueryHandler(super_view_callback, pattern=r"^super_view_"),
                MessageHandler(
                    filters.Regex("^(Назад|Отмена)$"),
                    admin_view_back,
                ),
            ],
            ADMIN_VIEW_TESTS: [
                CallbackQueryHandler(admin_test_stats, pattern=r"^admin_stats_"),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    admin_view_back,
                )
            ],
            ADMIN_CREATE_DESC: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    admin_create_desc,
                )
            ],
            ADMIN_DELETE_CODE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    admin_delete_code,
                )
            ],
            ADMIN_ADD_ADMIN: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    admin_add_admin_text,
                )
            ],
            ENTER_CODE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    enter_test_code,
                )
            ],
            RESUME_OR_RESTART: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    resume_or_restart_test,
                )
            ],
            INSTRUCTION_BEFORE_TEST: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    instruction_before_test,
                )
            ],
            ASKING_QUESTIONS: [
                CallbackQueryHandler(handle_answer, pattern=r"^answer_(-?[1-3]|0)$"),
                MessageHandler(
                    filters.Regex("^(Назад|Отмена)$"),
                    questions_cancel_or_back,
                ),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex("^Отмена$"), cancel),
        ],
        allow_reentry=True,
    )

    application.add_handler(conv_handler)
    application.add_handler(
        CallbackQueryHandler(
            show_public_test_stats,
            pattern=r"^test_stats_[0-9]{6}$",
        )
    )
    return conv_handler


__all__: Tuple[str, ...] = (
    "build_conversation_handler",
    "add_admin_command",
    "SELECTING_ROLE",
    "ADMIN_MENU",
    "ADMIN_VIEW_TESTS",
    "ADMIN_CREATE_DESC",
    "ADMIN_DELETE_CODE",
    "ENTER_CODE",
    "RESUME_OR_RESTART",
    "INSTRUCTION_BEFORE_TEST",
    "ASKING_QUESTIONS",
)

