"""
db_setup.py
------------
Generates a synthetic e-commerce database (SQLite) for the SQL + GenAI
Analytics Dashboard project.

Domain: same e-commerce/retail world as your Return Risk Modeling project,
so the two make a coherent portfolio pair (one is the ML model, this is the
SQL + dashboard + GenAI query layer on top of similar data).

Run:
    python db_setup.py

Produces: analytics.db (SQLite file) in the same folder.
"""

import sqlite3
import random
from datetime import date, timedelta

random.seed(42)  # reproducible data

DB_PATH = "analytics.db"

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditi", "Diya", "Kabir", "Ananya", "Ishaan", "Myra",
    "Rohan", "Sara", "Arjun", "Kavya", "Dev", "Anika", "Vihaan", "Riya",
    "Yash", "Priya", "Kunal", "Meera", "Sameer", "Naina", "Aryan", "Tara",
    "Karan", "Isha", "Nikhil", "Pooja", "Rahul", "Sneha",
]
LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Mehta", "Kapoor", "Reddy", "Nair", "Iyer",
    "Chopra", "Malhotra", "Bose", "Rao", "Singh", "Kulkarni", "Joshi",
]
REGIONS = ["North", "South", "East", "West", "Central"]
SEGMENTS = ["New", "Regular", "VIP"]

CATEGORIES = {
    "Apparel": ["Denim Jacket", "Cotton Tee", "Formal Shirt", "Sneakers", "Hoodie", "Chinos"],
    "Electronics": ["Wireless Earbuds", "Smartwatch", "Bluetooth Speaker", "Phone Case", "Power Bank"],
    "Home": ["Table Lamp", "Cushion Cover", "Wall Clock", "Storage Box", "Bedsheet Set"],
    "Beauty": ["Face Serum", "Lip Balm Set", "Sunscreen SPF50", "Hair Oil", "Perfume"],
    "Footwear": ["Running Shoes", "Sandals", "Formal Loafers", "Sports Slides"],
    "Accessories": ["Sunglasses", "Leather Wallet", "Backpack", "Analog Watch", "Belt"],
}

# Categories with historically higher return rates (mirrors real e-commerce:
# apparel/footwear return far more than electronics/beauty) — this is what
# makes the "return rate by category" chart in the dashboard interesting,
# and echoes the finding from your Return Risk Modeling project.
RETURN_RATE_BY_CATEGORY = {
    "Apparel": 0.27,
    "Footwear": 0.24,
    "Electronics": 0.08,
    "Home": 0.10,
    "Beauty": 0.06,
    "Accessories": 0.13,
}

N_CUSTOMERS = 500
N_ORDERS = 3500
START_DATE = date(2025, 1, 1)
END_DATE = date(2026, 9, 1)

REVIEW_TEXT_BY_RATING = {
    5: ["Excellent quality, exactly as described.", "Loved it, will buy again.", "Great value for the price."],
    4: ["Good product, minor issues with packaging.", "Works well, happy with the purchase."],
    3: ["It's okay, nothing special.", "Average quality, expected a bit more."],
    2: ["Not as described, quality could be better.", "Disappointed with the material."],
    1: ["Poor quality, would not recommend.", "Arrived damaged, requesting a return."],
}


def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def build_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        DROP TABLE IF EXISTS reviews;
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS customers;

        CREATE TABLE customers (
            customer_id   INTEGER PRIMARY KEY,
            name          TEXT NOT NULL,
            region        TEXT NOT NULL,
            segment       TEXT NOT NULL,
            signup_date   TEXT NOT NULL
        );

        CREATE TABLE products (
            product_id    INTEGER PRIMARY KEY,
            product_name  TEXT NOT NULL,
            category      TEXT NOT NULL,
            price         REAL NOT NULL
        );

        CREATE TABLE orders (
            order_id      INTEGER PRIMARY KEY,
            customer_id   INTEGER NOT NULL,
            order_date    TEXT NOT NULL,
            status        TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE order_items (
            order_item_id INTEGER PRIMARY KEY,
            order_id      INTEGER NOT NULL,
            product_id    INTEGER NOT NULL,
            quantity      INTEGER NOT NULL,
            unit_price    REAL NOT NULL,
            returned      INTEGER NOT NULL, -- 0/1
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );

        CREATE TABLE reviews (
            review_id     INTEGER PRIMARY KEY,
            product_id    INTEGER NOT NULL,
            customer_id   INTEGER NOT NULL,
            rating        INTEGER NOT NULL, -- 1-5
            review_text   TEXT NOT NULL,
            review_date   TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(product_id),
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );
        """
    )
    conn.commit()


def seed_customers(conn: sqlite3.Connection) -> None:
    rows = []
    for cid in range(1, N_CUSTOMERS + 1):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        region = random.choice(REGIONS)
        segment = random.choices(SEGMENTS, weights=[0.3, 0.55, 0.15])[0]
        signup = random_date(START_DATE, END_DATE)
        rows.append((cid, name, region, segment, signup.isoformat()))
    conn.executemany(
        "INSERT INTO customers VALUES (?, ?, ?, ?, ?)", rows
    )
    conn.commit()


def seed_products(conn: sqlite3.Connection) -> list[dict]:
    rows = []
    pid = 1
    catalog = []
    for category, names in CATEGORIES.items():
        for name in names:
            price = round(random.uniform(8, 25) * random.choice([2, 3, 4, 5]), 2)
            rows.append((pid, name, category, price))
            catalog.append({"product_id": pid, "category": category, "price": price})
            pid += 1
    conn.executemany(
        "INSERT INTO products VALUES (?, ?, ?, ?)", rows
    )
    conn.commit()
    return catalog


def seed_orders_and_items(conn: sqlite3.Connection, catalog: list[dict]) -> None:
    order_rows = []
    item_rows = []
    item_id = 1

    for oid in range(1, N_ORDERS + 1):
        customer_id = random.randint(1, N_CUSTOMERS)
        order_date = random_date(START_DATE, END_DATE)
        status = random.choices(
            ["Completed", "Cancelled"], weights=[0.94, 0.06]
        )[0]
        order_rows.append((oid, customer_id, order_date.isoformat(), status))

        n_items = random.choices([1, 2, 3, 4], weights=[0.45, 0.3, 0.15, 0.1])[0]
        chosen = random.sample(catalog, k=min(n_items, len(catalog)))
        for product in chosen:
            qty = random.choices([1, 2, 3], weights=[0.7, 0.22, 0.08])[0]
            return_prob = RETURN_RATE_BY_CATEGORY[product["category"]]
            returned = 1 if (status == "Completed" and random.random() < return_prob) else 0
            item_rows.append(
                (item_id, oid, product["product_id"], qty, product["price"], returned)
            )
            item_id += 1

    conn.executemany(
        "INSERT INTO orders VALUES (?, ?, ?, ?)", order_rows
    )
    conn.executemany(
        "INSERT INTO order_items VALUES (?, ?, ?, ?, ?, ?)", item_rows
    )
    conn.commit()


def seed_reviews(conn: sqlite3.Connection, catalog: list[dict]) -> None:
    """
    One review per (customer, product) that actually appears together in
    order_items, so reviews stay grounded in real purchases. Rating is
    skewed by the product's category return rate — categories that get
    returned more also tend to rate a bit lower, which keeps the
    reviews/returns story consistent for the dashboard.
    """
    pairs = conn.execute(
        "SELECT DISTINCT o.customer_id, oi.product_id "
        "FROM order_items oi JOIN orders o ON oi.order_id = o.order_id "
        "WHERE o.status = 'Completed'"
    ).fetchall()

    product_category = {p["product_id"]: p["category"] for p in catalog}

    # only a subset of purchases get reviewed, like in real life
    reviewed_pairs = random.sample(pairs, k=int(len(pairs) * 0.35))

    rows = []
    for review_id, (customer_id, product_id) in enumerate(reviewed_pairs, start=1):
        category = product_category[product_id]
        return_prob = RETURN_RATE_BY_CATEGORY[category]
        # map return_prob (0.06-0.27) to an average rating (roughly 4.4-3.2)
        avg_rating = 4.6 - (return_prob * 5)
        rating = min(5, max(1, round(random.gauss(avg_rating, 0.9))))
        text = random.choice(REVIEW_TEXT_BY_RATING[rating])
        review_date = random_date(START_DATE, END_DATE)
        rows.append((review_id, product_id, customer_id, rating, text, review_date.isoformat()))

    conn.executemany(
        "INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?)", rows
    )
    conn.commit()


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    build_schema(conn)
    seed_customers(conn)
    catalog = seed_products(conn)
    seed_orders_and_items(conn, catalog)
    seed_reviews(conn, catalog)

    cur = conn.cursor()
    n_customers = cur.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    n_orders = cur.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    n_items = cur.execute("SELECT COUNT(*) FROM order_items").fetchone()[0]
    n_reviews = cur.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    conn.close()

    print(f"Created {DB_PATH}")
    print(f"  customers:   {n_customers}")
    print(f"  orders:      {n_orders}")
    print(f"  order_items: {n_items}")
    print(f"  reviews:     {n_reviews}")


if __name__ == "__main__":
    main()
