"""Состояния сценария «оставить заявку»."""

from aiogram.fsm.state import State, StatesGroup


class LeadForm(StatesGroup):
    name = State()
    phone = State()
    task = State()
