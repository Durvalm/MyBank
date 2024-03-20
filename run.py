from bank import Money
from data import RetrieveData

print("Welcome to MyBank, would you like to:")
print("1 - Add income/spending")
print("2 - See stats")

choice = input("-> ")

if choice == "1":
    money = Money()
    money.add()
    
elif choice == "2":
    data = RetrieveData("data.txt")
    data.run()
