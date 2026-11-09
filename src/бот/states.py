from aiogram.fsm.state import State, StatesGroup

class RecipeInterview(StatesGroup):
    """FSM states for recipe interview flow."""
    waiting_for_dish = State()          # User just started, waiting for dish name
    waiting_for_servings = State()      # Got dish, waiting for servings
    waiting_for_cuisine = State()       # Got servings, waiting for cuisine
    waiting_for_preferences = State()   # Got cuisine, waiting for preferences
    generating = State()                # All info collected, generating recipe