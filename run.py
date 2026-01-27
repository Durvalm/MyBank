from getpass import getpass

from bank import Money
from data import RetrieveData
from storage import authenticate_user, init_db

print("Welcome to MyBank, would you like to:")
print("1 - Add income/spending")
print("2 - See stats")

email = input("Email: ").strip().lower()
password = getpass("Password: ")
user = authenticate_user(email, password)
if not user:
    print("Invalid email or password.")
    raise SystemExit(1)

user_id = user["id"]

choice = input("-> ")

if choice == "1":
    init_db()
    money = Money(user_id)
    money.add()
    
elif choice == "2":
    init_db()
    data = RetrieveData(user_id)
    data.run()
