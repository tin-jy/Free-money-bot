import database.database as database
from constants.constants import *

def get_remaining_attempts(user_id):
    return database.get_remaining_attempts(user_id)

def take(user_id, amount:int) -> int:
    if not database.decrement_remaining_attempts(user_id):
        return UNEXPECTED_ERROR

    bank_balance = database.get_bank_balance()
    assert bank_balance >= 0

    if amount <= 0:
        return USER_DUMB
    if amount > bank_balance:
        return USER_GREEDY
    
    if database.decrement_bank_balance(amount):
        database.increment_user_balance(user_id, amount)
        return USER_SUCCESS
    
    return UNEXPECTED_ERROR

def create_user_if_not_exist(user_id, user_name):
    return database.create_user_if_not_exist(user_id, user_name)

def add_attempt(user_name):
    return database.add_attempt(user_name)
        
def get_user_balance(user_id):
    balance = database.get_user_balance(user_id)
    attempts = database.get_remaining_attempts(user_id)
    return balance, attempts

def get_bank_balance():
    return database.get_bank_balance()

def get_bank_next_top_up():
    return database.get_bank_next_top_up()

def generate_leaderboard(top_n: int = 10):
    # --- Top balances ---
    top_users = database.rank_users(top_n)
    top_withdrawals = database.rank_withdrawals(top_n)
    return top_users, top_withdrawals

def top_up_bank():
    database.top_up_bank_random()
    # can choose between random or daily

def reset_user_attempts():
    database.reset_user_attempts()

def set_user_balance(user_name, amount):
    database.set_user_balance(user_name, amount)

def log_take_attempt(user_id, user_name, chat_id, chat_type, amount, is_successful, reason):
    database.log_take_attempt(user_id, user_name, chat_id, chat_type, amount, is_successful, reason)

def get_user_history(user_id):
    return database.get_user_history(user_id)

def get_withdrawal_history(last_n=10):
    return database.get_withdrawal_history(last_n)