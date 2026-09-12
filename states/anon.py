from aiogram.fsm.state import State, StatesGroup


class SupportStates(StatesGroup):
    waiting_message = State()


class AnonStates(StatesGroup):
    waiting_anon = State()