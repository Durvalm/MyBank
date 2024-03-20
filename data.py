from datetime import datetime
import os
import json

script_directory = os.path.dirname(os.path.realpath(__file__))

class RetrieveData:
    def __init__(self, filename):
        self.filename = filename


    def run(self):
        print("\nWhat do you wanna see?")
        print("1 - total spending/income")
        print("2 - spending/income in last 1, 3, 6, or 12 months")
        print("3 - spending/income table for every month")
        print("4 - spending by category")

        choice = input("-> ")
        choice_methods = {
            "1": self.get_all_spending_income,
            "2": self.get_last_months_income_spending,
            "3": self.get_income_spending_per_month
        }

        selected_method = choice_methods.get(choice)
        selected_method()


    def get_all_spending_income(self):
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

                if diff.days > 360:
                    break

                for period in last_months_data.keys():
                    if diff.days < int(period):
                        last_months_data[period][data["type"]] += data["amount"]
        self.display_last_months_income_spending(last_months_data)


    def display_last_months_income_spending(self, data):
        print("\n")
        for key, value in data.items():
            month = int(key) // 30
            print(f"Last {month} months, you earned ${value['income']}")
            print(f"And spent ${value['spending']}")
    

    def get_income_spending_per_month(self):
        calendar_data = {}

        with open(f"{script_directory}/{self.filename}") as f:
            lines = f.readlines()
            for l in lines:
                data = json.loads(l)
                self.populate_calendar(calendar_data, data)
        
        # self.display_income_spending_yearly()
        self.display_income_spending_year_month(calendar_data)
    

    def populate_calendar(self, calendar_data, data):
        dt_obj = datetime.strptime(data["date"], "%Y-%m-%d")
        year = dt_obj.strftime("%Y")
        month = dt_obj.strftime("%m")

        amount_type = data["type"]
        spending = int(data["amount"]) if amount_type == "spending" else 0
        income = int(data["amount"]) if amount_type == "income" else 0
        total = income - spending

        # populate calendar
        if year not in calendar_data.keys():
            calendar_data[year] = {month: {"income": income, "spending": spending}, "total": total}
        else:
            if month not in calendar_data[year]:
                    calendar_data[year][month] = {"income": income, "spending": spending}
            else:
                calendar_data[year][month]["income"] += income
                calendar_data[year][month]["spending"] += spending
            calendar_data[year]["total"] += total
    
    def display_income_spending_year_month(self, calendar_data):
        for year, value in calendar_data.items():
            print("\n")
            print(year)
            for month, v in value.items():
                if month == "total":
                    continue
                print(f"Month {month}: "
                    + f"Income: ${v['income']} / Spending: ${v['spending']}"
                )
            print(f"Total for {year} is ${value['total']}")
