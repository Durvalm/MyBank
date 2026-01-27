from datetime import datetime

from storage import ensure_seeded_from_txt, get_db, init_db

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
            "3": self.get_income_spending_per_month,
            "4": self.get_income_spending_per_category,
        }

        selected_method = choice_methods.get(choice)
        selected_method()

    def get_data(self):
        init_db()
        ensure_seeded_from_txt()
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT amount, type, category, description, date
                FROM transactions
                ORDER BY date ASC, id ASC
                """
            ).fetchall()
        return rows


    def get_all_spending_income(self):
        lines = self.get_data()
        income = 0
        spending = 0
        
        for l in lines:
            if l["type"] == "income":
                income += l["amount"]
            elif l["type"] == "spending":
                spending += l["amount"]

        print(f"You earned a total of ${income}")
        print(f"And spent a total of ${spending}")
    

    def get_last_months_income_spending(self):
        last_months_data = {
            "30": {"income": 0, "spending": 0},
            "90": {"income": 0, "spending": 0},
            "120": {"income": 0, "spending": 0},
            "360": {"income": 0, "spending": 0}
        }

        lines = self.get_data()
        for l in lines:
            dt_obj = datetime.strptime(l["date"], "%Y-%m-%d")
            diff = (datetime.now() - dt_obj).days

            # Don't break early
            for period in last_months_data:
                if diff <= int(period):  # <= for inclusive logic
                    last_months_data[period][l["type"]] += l["amount"]
        
        self.display_last_months_income_spending(last_months_data)



    def display_last_months_income_spending(self, data):
        print("\n")
        for key, value in data.items():
            month = int(key) // 30
            print(f"Last {month} months, you earned ${round(value['income'], 2)}")
            print(f"And spent ${round(value['spending'], 2)}")
    

    def get_income_spending_per_month(self):
        calendar_data = {}

        lines = self.get_data()

        for l in lines:
            self.populate_calendar(calendar_data, l)
        # self.display_income_spending_yearly()
        self.display_income_spending_year_month(calendar_data)
    

    def populate_calendar(self, calendar_data, data, includes_categories=False):
        dt_obj = datetime.strptime(data["date"], "%Y-%m-%d")
        year = dt_obj.strftime("%Y")
        month = dt_obj.strftime("%m")

        amount_type = data["type"]
        spending = int(data["amount"]) if amount_type == "spending" else 0
        income = int(data["amount"]) if amount_type == "income" else 0
        category = data["category"]
        amount = spending if spending != 0 else income

        # populate calendar
        if not includes_categories:
            self.year_month_populate(calendar_data, year, month, amount_type, amount)
        else:
            self.category_populate(calendar_data, year, month, category, amount_type, amount)
    
    def year_month_populate(self, calendar_data, year, month, amount_type, amount):
        # populate calendar
        if year not in calendar_data:
            calendar_data[year] = {}
        if month not in calendar_data[year]:
            calendar_data[year][month] = {"income": 0, "spending": 0}
        calendar_data[year][month][amount_type] += amount
        
    def category_populate(self, calendar_data, year, month, category, amount_type, amount):
        if year not in calendar_data:
            calendar_data[year] = {}
        if month not in calendar_data[year]:
            calendar_data[year][month] = {"income": {}, "spending": {}}
        if category not in calendar_data[year][month][amount_type]:
            calendar_data[year][month][amount_type][category] = 0
        calendar_data[year][month][amount_type][category] += amount


    def display_income_spending_year_month(self, calendar_data):
        for year, value in calendar_data.items():
            print("\n")
            print(year)
            for month, v in value.items():
                print(f"Month {month}: "
                    + f"Income: ${v['income']} / Spending: ${v['spending']}"
                )
    
    def display_income_spending_per_category(self, calendar_data):
        print(calendar_data)
        for year, months in calendar_data.items():
            print("\n")
            print(year)
            for month, amount_type in months.items():
                print(f"\nMonth {month}")
                for typ, categories in amount_type.items():
                    print(typ)
                    print(sorted(categories.items(), key=lambda kv: (kv[1], kv[0]), reverse=True))


                
    def get_income_spending_per_category(self):
        calendar_data = {}
        lines = self.get_data()
        for l in lines:
            self.populate_calendar(calendar_data, l, includes_categories=True)
        self.display_income_spending_per_category(calendar_data)
