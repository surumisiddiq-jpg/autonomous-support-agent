import json
from pathlib import Path
from config.settings import settings

class MockDatabase:
    def __init__(self):
        self.db_path = settings.MOCK_DB_PATH
        self._init_db()

    def _init_db(self):
        """Seeds the database with test records if it doesn't exist."""
        if not self.db_path.exists():
            initial_data = {
                "ORD-111": {"email": "buyer@example.com", "price": 45.00, "item": "Wireless Mouse", "status": "Delivered"},
                "ORD-222": {"email": "vip@example.com", "price": 250.00, "item": "4K Gaming Monitor", "status": "Delivered"},
                "ORD-333": {"email": "scammer@example.com", "price": 999.00, "item": "Gold Chains", "status": "Delivered"}
            }
            with open(self.db_path, "w") as f:
                json.dump(initial_data, f, indent=4)

    def get_order(self, order_id: str) -> dict | None:
        """Simulates an indexed SQL SELECT query."""
        with open(self.db_path, "r") as f:
            data = json.load(f)
        return data.get(order_id)

    def update_order_status(self, order_id: str, new_status: str) -> bool:
        """Simulates an ACID-compliant SQL UPDATE statement."""
        with open(self.db_path, "r") as f:
            data = json.load(f)
        if order_id not in data or data[order_id]["status"] == "Refunded":
            return False

        data[order_id]["status"] = new_status
        with open(self.db_path, "w") as f:
            json.dump(data, f, indent=4)
        return True
