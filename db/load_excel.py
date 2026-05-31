import pandas as pd
from app.db import get_conn


def load_excel():
    df = pd.read_excel("data/foods.xlsx")

    conn = get_conn()
    cur = conn.cursor()

    for _, row in df.iterrows():
        cur.execute("""
            INSERT INTO foods (name, category, price, calories, spicy, vegetarian)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            row["name"],
            row["category"],
            row["price"],
            row["calories"],
            row["spicy"],
            row["vegetarian"]
        ))

    conn.commit()
    conn.close()

    print("Foods imported")


if __name__ == "__main__":
    load_excel()
