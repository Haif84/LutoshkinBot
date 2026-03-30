from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def role_selection_keyboard() -> ReplyKeyboardMarkup:
    """Reply keyboard for selecting role."""
    keyboard = [
        [KeyboardButton("Администратор"), KeyboardButton("Тестируемый")],
        [KeyboardButton("Отмена")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def cancel_back_keyboard() -> ReplyKeyboardMarkup:
    """Reply keyboard with Back / Cancel."""
    keyboard = [[KeyboardButton("Назад"), KeyboardButton("Отмена")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def resume_test_keyboard() -> ReplyKeyboardMarkup:
    """Reply keyboard to offer resume or restart test."""
    keyboard = [
        [KeyboardButton("Продолжить"), KeyboardButton("Начать заново")],
        [KeyboardButton("Отмена")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def start_test_keyboard() -> ReplyKeyboardMarkup:
    """Reply keyboard to confirm starting the test after instructions."""
    keyboard = [
        [KeyboardButton("Приступить к тестированию")],
        [KeyboardButton("Отмена")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def admin_menu_inline_keyboard(show_super_actions: bool = False) -> InlineKeyboardMarkup:
    """Inline keyboard for administrator menu."""
    keyboard = [
        [
            InlineKeyboardButton(
                "Просмотр текущих тестирований", callback_data="admin_view_tests"
            )
        ],
        [
            InlineKeyboardButton(
                "Создать новое тестирование", callback_data="admin_create_test"
            )
        ],
        [
            InlineKeyboardButton(
                "Удалить тестирование", callback_data="admin_delete_test"
            )
        ],
    ]
    if show_super_actions:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "Просмотр тестирований пользователя",
                    callback_data="super_view_admins_tests",
                )
            ]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "Добавить администратора", callback_data="admin_add_admin"
                )
            ]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "Управление администраторами", callback_data="admin_manage_admins"
                )
            ]
        )
    return InlineKeyboardMarkup(keyboard)


def super_view_admins_keyboard(admins_with_counts: list) -> InlineKeyboardMarkup:
    """
    Inline keyboard for «Просмотр тестирований пользователя»:
    one button per admin: «Просмотреть тесты N».
    admins_with_counts: list of (admin_dict, test_count); admin_dict must have "id".
    """
    keyboard = []
    for num, (admin, _count) in enumerate(admins_with_counts, 1):
        admin_id = admin.get("id")
        if admin_id is None:
            continue
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"Просмотреть тесты {num}",
                    callback_data=f"super_view_tests_{admin_id}",
                )
            ]
        )
    return InlineKeyboardMarkup(keyboard)


def admin_manage_admins_keyboard(admins: list) -> InlineKeyboardMarkup:
    """
    Inline keyboard for "Управление администраторами":
    for each admin — two buttons: "Сделать № суперадмином" / "Сделать № обычным".
    """
    keyboard = []
    for num, a in enumerate(admins, 1):
        admin_id = a.get("id")
        if admin_id is None:
            continue
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"Сделать {num} суперадмином",
                    callback_data=f"admin_set_super_{admin_id}",
                ),
                InlineKeyboardButton(
                    f"Сделать {num} обычным",
                    callback_data=f"admin_set_normal_{admin_id}",
                ),
            ]
        )
    return InlineKeyboardMarkup(keyboard)


def answers_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for answers +3 ... -3 in one row."""
    keyboard = [
        [
            InlineKeyboardButton("+3", callback_data="answer_3"),
            InlineKeyboardButton("+2", callback_data="answer_2"),
            InlineKeyboardButton("+1", callback_data="answer_1"),
            InlineKeyboardButton("0", callback_data="answer_0"),
            InlineKeyboardButton("–1", callback_data="answer_-1"),
            InlineKeyboardButton("–2", callback_data="answer_-2"),
            InlineKeyboardButton("–3", callback_data="answer_-3"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def test_stats_button_keyboard(test_code: str) -> InlineKeyboardMarkup:
    """Inline keyboard with one button: «Общая статистика по тестированию» (для тестируемых)."""
    keyboard = [
        [
            InlineKeyboardButton(
                "Общая статистика по тестированию",
                callback_data=f"test_stats_{test_code}",
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_tests_stats_keyboard(tests) -> InlineKeyboardMarkup:
    """
    Inline keyboard with one button per active test
    to view detailed statistics for a selected test.
    """
    keyboard = []
    for t in tests:
        code = t.get("code")
        if not code:
            continue
        desc = t.get("description") or ""
        label = f"{code} - {desc}" if desc else str(code)
        keyboard.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=f"admin_stats_{code}",
                )
            ]
        )
    return InlineKeyboardMarkup(keyboard)

