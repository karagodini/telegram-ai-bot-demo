"""Сценарий заявки: имя, телефон, задача, пересылка менеджеру."""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import Settings
from bot.keyboards import cancel_keyboard, main_menu
from bot.services.leads import (
    Lead,
    format_lead,
    mask_phone,
    normalize_phone,
    validate_name,
    validate_task,
)
from bot.states import LeadForm
from bot.texts import (
    ASK_NAME,
    ASK_NAME_AGAIN,
    ASK_PHONE,
    ASK_PHONE_AGAIN,
    ASK_TASK,
    ASK_TASK_AGAIN,
    BTN_CANCEL,
    LEAD_CANCELLED,
    LEAD_SAVED_ONLY,
    LEAD_SENT,
    NEED_TEXT,
)

logger = logging.getLogger(__name__)

router = Router(name="lead")
router.message.filter(F.chat.type == ChatType.PRIVATE)


async def begin_lead(message: Message, state: FSMContext) -> None:
    await state.set_state(LeadForm.name)
    await message.answer(ASK_NAME, reply_markup=cancel_keyboard())


def _is_cancel(text: str | None) -> bool:
    return (text or "").strip().casefold() == BTN_CANCEL.casefold()


async def _stop(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(LEAD_CANCELLED, reply_markup=main_menu())


@router.message(StateFilter(LeadForm), F.text)
async def on_lead_step(message: Message, state: FSMContext, settings: Settings, bot: Bot) -> None:
    text = message.text or ""
    if _is_cancel(text):
        await _stop(message, state)
        return

    current = await state.get_state()
    if current == LeadForm.name.state:
        name = validate_name(text)
        if name is None:
            await message.answer(ASK_NAME_AGAIN)
            return
        await state.update_data(name=name)
        await state.set_state(LeadForm.phone)
        await message.answer(ASK_PHONE)
        return

    if current == LeadForm.phone.state:
        phone = normalize_phone(text)
        if phone is None:
            await message.answer(ASK_PHONE_AGAIN)
            return
        await state.update_data(phone=phone)
        await state.set_state(LeadForm.task)
        await message.answer(ASK_TASK)
        return

    task = validate_task(text)
    if task is None:
        await message.answer(ASK_TASK_AGAIN)
        return

    data = await state.get_data()
    await state.clear()
    username = message.from_user.username if message.from_user else None
    lead = Lead(
        name=str(data["name"]),
        phone=str(data["phone"]),
        task=task,
        chat_id=message.chat.id,
        username=username,
    )
    delivered = await notify_manager(bot, settings.manager_chat_id, lead)
    await message.answer(LEAD_SENT if delivered else LEAD_SAVED_ONLY, reply_markup=main_menu())


@router.message(StateFilter(LeadForm))
async def on_lead_non_text(message: Message) -> None:
    await message.answer(NEED_TEXT)


async def notify_manager(bot: Bot, manager_chat_id: int | None, lead: Lead) -> bool:
    logger.info(
        "заявка chat_id=%s name=%s phone=%s",
        lead.chat_id,
        lead.name,
        mask_phone(lead.phone),
    )
    if manager_chat_id is None:
        logger.warning(
            "MANAGER_CHAT_ID не задан, заявка осталась только в логе. task=%s",
            lead.task,
        )
        return False
    try:
        await bot.send_message(manager_chat_id, format_lead(lead))
    except TelegramAPIError as exc:
        logger.error("не удалось переслать заявку в %s: %s", manager_chat_id, exc)
        return False
    return True
