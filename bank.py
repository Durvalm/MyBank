import datetime

from storage import INCOME_CATEGORIES, SPENDING_CATEGORIES, init_db, insert_transaction


class Money:

    def __init__(self, user_id, api_client=None):
        self.user_id = user_id
        self.api_client = api_client
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
        self.description = self.get_description()
        self.date = datetime.date.today()

    def introduce(self):
        print("\nWelcome to the Bank program")
        print("Enter the amount and select [income] or [spending]")
    

    def add(self):
        if not self.option and self.amount:
            return None
        payload = self.to_payload()
        if self.api_client:
            self.api_client.add_transaction(payload)
        else:
            init_db()
            insert_transaction(
                self.user_id,
                payload["amount"],
                payload["type"],
                payload["category"],
                payload["description"],
                payload["date"],
            )
        print(f"{self.amount} added as {self.category} {self.option} in {self.date}")
    
    def to_payload(self):
        return {
            "amount": self.amount,
            "type": self.option,
            "date": self.date.isoformat(),
            "category": self.category,
            "description": self.description,
        }



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
        return INCOME_CATEGORIES
    
    def spending_categories(self):
        return SPENDING_CATEGORIES
