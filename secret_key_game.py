import random

players = []
MIN_SECRET = 0
MAX_SECRET = 99

def add_player(user_id, user_name, original_secret, coins=50):
    global players
    if len(players) > MAX_SECRET:
        raise ValueError("Too many players")

    secret = original_secret
    if secret == -1:
        secret = random.randint(MIN_SECRET, MAX_SECRET)

    player = {
        "user_id": user_id,
        "user_name": user_name,
        "original_secret": original_secret,
        "secret": secret,
        "coins": coins,
        "is_alive": True
    }
    players.append(player)

def enforce_unique_secrets():
    global players

    while True:
        secret_map = {}
        for p in players:
            secret_map.setdefault(p["secret"], []).append(p)

        collisions = [group for group in secret_map.values() if len(group) > 1]

        if not collisions:
            return

        used = {p["secret"] for p in players}

        for group in collisions:
            for player in group:
                new_secret = random.randint(MIN_SECRET, MAX_SECRET)
                while new_secret in used:
                    new_secret = random.randint(MIN_SECRET, MAX_SECRET)

                player["secret"] = new_secret
                used.add(new_secret)


def clue_is_even(buyer_id: int, cost=50):
    if get_coins(buyer_id) < cost:
        return
    
    subtract_coins(buyer_id, cost)
    

def get_coins(user_id: int) -> int:
    for player in players:
        if player["user_id"] == user_id:
            return player.get("coins", 0)
    return 0


def add_coins(user_id: int, amount: int):
    for player in players:
        if player["user_id"] == user_id:
            player["coins"] += amount
            return


def subtract_coins(user_id: int, amount: int):
    for player in players:
        if player["user_id"] == user_id:
            player["coins"] -= amount
            return
