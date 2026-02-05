import requests


class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def login(self, email, password):
        resp = self.session.post(
            f"{self.base_url}/api/login",
            json={"email": email, "password": password},
            timeout=15,
        )
        if resp.status_code != 200:
            return False
        data = resp.json()
        return bool(data.get("ok"))

    def is_authenticated(self):
        resp = self.session.get(
            f"{self.base_url}/api/transactions",
            params={"limit": 1, "offset": 0},
            timeout=15,
        )
        if resp.status_code == 401:
            return False
        resp.raise_for_status()
        return True

    def list_transactions(self, limit=200, offset=0):
        resp = self.session.get(
            f"{self.base_url}/api/transactions",
            params={"limit": limit, "offset": offset},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def list_all_transactions(self, page_size=200):
        all_rows = []
        offset = 0
        while True:
            rows = self.list_transactions(limit=page_size, offset=offset)
            all_rows.extend(rows)
            if len(rows) < page_size:
                break
            offset += page_size
        return all_rows

    def add_transaction(self, payload):
        resp = self.session.post(
            f"{self.base_url}/api/transactions",
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def set_cookies(self, cookies):
        self.session.cookies.update(cookies or {})

    def get_cookies(self):
        return requests.utils.dict_from_cookiejar(self.session.cookies)
