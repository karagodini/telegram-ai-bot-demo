"""Команды /start, /help, /reset и служебные."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handlers.lead import begin_lead
from bot.keyboards import main_menu
from bot.memory import DialogMemory
from bot.texts import HELP, LEAD_CANCELLED, NOTHING_TO_CANCEL, RESET, START

router = Router(name="commands")
router.message.filter(F.chat.type == ChatType.PRIVATE)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, memory: DialogMemory) -> None:
    await state.clear()
    memory.reset(message.chat.id)
    await message.answer(START, reply_markup=main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP, reply_markup=main_menu())


@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext, memory: DialogMemory) -> None:
    await state.clear()
    memory.reset(message.chat.id)
    await message.answer(RESET, reply_markup=main_menu())


@router.message(Command("lead"))
async def cmd_lead(message: Message, state: FSMContext) -> None:
    await begin_lead(message, state)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    await state.clear()
    text = NOTHING_TO_CANCEL if current is None else LEAD_CANCELLED
    await message.answer(text, reply_markup=main_menu())


@router.message(Command("chatid"))
async def cmd_chatid(message: Message) -> None:
    await message.answer(
        f"chat_id: {message.chat.id}\n"
        "Этот номер можно записать в MANAGER_CHAT_ID, если чат принадлежит менеджеру. "
        "Сначала менеджер должен нажать /start, иначе бот не сможет написать первым."
    )
