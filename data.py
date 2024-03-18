import datetime
import os
import json

script_directory = os.path.dirname(os.path.realpath(__file__))

class RetrieveData:
    def __init__(self, filename):
        self.filename = filename

    def get_all_spending(self):
        with open(f"{script_directory}/{self.filename}") as f:
            lines = f.readlines()
            spending = 0
            
            for l in lines:
                data = json.loads(l)
                print(data["date"])
                if data["type"] == "spending":
                    spending += data["amount"]

            print("Spent a total of $", spending)
            return spending
    
    def get_all_income(self):
        with open(f"{script_directory}/{self.filename}") as f:
            lines = f.readlines()
            income = 0
            
            for l in lines:
                data = json.loads(l)
                if data["type"] == "income":
                    income += data["amount"]

            print("Earned a total of $", income)
            return income

data = RetrieveData("data.txt")
data.get_all_spending()
data.get_all_income()