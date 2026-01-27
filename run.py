from bank import Money
from data import RetrieveData
from storage import init_db

print("Welcome to MyBank, would you like to:")
print("1 - Add income/spending")
print("2 - See stats")

choice = input("-> ")

if choice == "1":
    init_db()
    money = Money()
    money.add()
    
elif choice == "2":
    init_db()
    data = RetrieveData()
    data.run()
