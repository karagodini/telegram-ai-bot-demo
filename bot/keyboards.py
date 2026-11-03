"""Клавиатуры основного меню и шага заявки."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from bot.texts import BTN_CANCEL, BTN_CONTACTS, BTN_LEAD, BTN_SERVICES, BTN_TERMS


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SERVICES), KeyboardButton(text=BTN_TERMS)],
            [KeyboardButton(text=BTN_CONTACTS), KeyboardButton(text=BTN_LEAD)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Напишите вопрос",
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )
