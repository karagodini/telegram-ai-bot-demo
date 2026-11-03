"""Свободный диалог с консультантом."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatAction, ChatType
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handlers.lead import begin_lead
from bot.keyboards import main_menu
from bot.services.consultant import Consultant
from bot.texts import BTN_LEAD, QUICK_QUESTIONS

router = Router(name="chat")
router.message.filter(F.chat.type == ChatType.PRIVATE)


@router.message(StateFilter(None), F.text, ~F.text.startswith("/"))
async def on_text(message: Message, consultant: Consultant, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        return
    if text == BTN_LEAD:
        await begin_lead(message, state)
        return

    query = QUICK_QUESTIONS.get(text, text)
    if message.bot is not None:
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    answer = await consultant.reply(message.chat.id, query)
    await message.answer(answer, reply_markup=main_menu())
