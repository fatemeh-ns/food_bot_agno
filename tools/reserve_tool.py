import json
from app.db import get_conn
from datetime import datetime


def reserve_food(food_id: int, user_name: str, food_name: str = None):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO orders (food_id, user_name, status)
        VALUES (?, ?, ?)
    """, (food_id, user_name, "pending"))

    if food_name is None:
        cur.execute("SELECT name FROM foods WHERE id = ?", (food_id,))
        result = cur.fetchone()
        food_name = result[0] if result else f"food_{food_id}"

    # log
    with open("orders.log", "a", encoding="utf-8") as f:
        order_data = {
            "timestamp": datetime.now().isoformat(),
            "customer_name": user_name,
            "food_name": food_name,
            "food_id": food_id,
            "status": "confirmed"
        }
        f.write(json.dumps(order_data, ensure_ascii=False) + "\n")

    conn.commit()
    conn.close()

    return {
        "message": "Order created successfully",
        "food_id": food_id,
        "user_name": user_name,
        "status": "pending"
    }
