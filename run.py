import json
import os
import sys
from getpass import getpass

from bank import Money
from data import RetrieveData
from storage import authenticate_user, get_user_by_id, init_db

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".mybank")
CONFIG_PATH = os.path.join(CONFIG_DIR, "credentials.json")


def load_saved_user():
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH) as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return None

    user_id = data.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(user_id)


def save_user(user):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as file:
        json.dump({"user_id": user["id"], "email": user["email"]}, file)


def clear_saved_user():
    try:
        os.remove(CONFIG_PATH)
    except FileNotFoundError:
        pass


if "--logout" in sys.argv:
    clear_saved_user()
    print("Saved CLI session cleared.")
    raise SystemExit(0)

print("Welcome to MyBank, would you like to:")
print("1 - Add income/spending")
print("2 - See stats")

init_db()
user = load_saved_user()
if not user:
    email = input("Email: ").strip().lower()
    password = getpass("Password: ")
    user = authenticate_user(email, password)
    if not user:
        print("Invalid email or password.")
        raise SystemExit(1)
    remember = input("Remember this login on this device? (y/N): ").strip().lower()
    if remember in ("y", "yes"):
        save_user(user)
user_id = user["id"]

choice = input("-> ")

if choice == "1":
    money = Money(user_id)
    money.add()
    
elif choice == "2":
    data = RetrieveData(user_id)
    data.run()
