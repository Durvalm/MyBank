import datetime
import os
import json

script_directory = os.path.dirname(os.path.realpath(__file__))


class Money:

    def __init__(self):
        self.introduce()
        self.amount = self.get_amount()
        if self.amount is None:
            return None
        self.option = self.get_option()
        if self.option is None:
            return None
        self.category = self.get_category()
        if self.category is None:
            return None
        self.decription = self.get_description()
        self.date = datetime.date.today()

    def introduce(self):
        print("\nWelcome to the Bank program")
        print("Enter the amount and select [income] or [spending]")
    

    def add(self):
        if not self.option and self.amount:
            return None
        with open(f"{script_directory}/data.txt", "a") as file:
            file.write("\n" + self.to_dict())
        print(f"{self.amount} added as {self.category} {self.option} in {self.date}")
    
    def to_dict(self):
        data = {"amount": self.amount, "type": self.option,
                    "date": self.date.isoformat(), "category": self.category, "description": self.decription}
        return json.dumps(data)



    def get_amount(self):
        try:
            amount = float(input("Enter Amount: "))
        except ValueError:
            print("Has to be number")
            return None
        return amount
    
    def get_description(self):
        return input(f"More details about this {self.option}: ")

    def get_option(self):
        option = input("Enter if is income or spending: ").lower()
        return self.check_option(option)


    def check_option(self, option):
        if option == "income" or option == "spending":
            return option
        else:
            print("invalid type")
            return None

    def get_category(self):
        print(f"\nNow select what category is this {self.option}")
        if self.option == "income":
            categories = self.income_categories()
        else:
            categories = self.spending_categories()

        print("Categories:", *categories)

        category = input("Select category: ").lower()

        if category not in categories:
            return None
        return category


    def income_categories(self):
        categories = ["work", "financial_aid", "family", "sell", "other"]
        return categories
    
    def spending_categories(self):
        categories = ["transportation", "personal_care", "groceries", "eating_out", "travel", "shopping", "app_subscriptions",
                      "education", "utilities", "rent", "cellphone", "hobbies", "fitness", "medical", "other"]
        return categories

