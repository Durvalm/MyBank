from datetime import datetime
import os
import json

script_directory = os.path.dirname(os.path.realpath(__file__))

class RetrieveData:
    def __init__(self, filename):
        self.filename = filename

    def get_all_spending_or_income(self):
        with open(f"{script_directory}/{self.filename}") as f:
            lines = f.readlines()
            income = 0
            spending = 0
            
            for l in lines:
                data = json.loads(l)
                if data["type"] == "income":
                    income += data["amount"]
                elif data["type"] == "spending":
                    spending += data["amount"]

            print(f"You earned a total of ${income}")
            print(f"And spent a total of ${spending}")
    
    def get_last_months_income_spending(self):
        last_months_data = {
            "30": {"income": 0, "spending": 0},
            "90": {"income": 0, "spending": 0},
            "120": {"income": 0, "spending": 0},
            "360": {"income": 0, "spending": 0}
        }

        with open(f"{script_directory}/{self.filename}") as f:
            lines = f.readlines()
            for l in lines:
                data = json.loads(l)
                dt_obj = datetime.strptime(data["date"], "%Y-%m-%d")
                diff = datetime.now() - dt_obj
                for period in last_months_data.keys():
                    if diff.days < int(period):
                        last_months_data[period][data["type"]] += data["amount"]
        self.display_last_months_income_spending()

    def display_last_months_income_spending(self):
        pass
                
        
    

print("\nWhat do you wanna see?")
print("1 - total spending/income")
print("2 - spending/income in last 1, 3, 6, or 12 months")
print("3 - spending/income table for every month")
print("4 - spending by category")

choice = input("-> ")
data = RetrieveData("data.txt")

choice_methods = {
    "1": data.get_all_spending_or_income,
    "2": data.get_last_months_income_spending,
}

selected_method = choice_methods.get(choice)
selected_method()
