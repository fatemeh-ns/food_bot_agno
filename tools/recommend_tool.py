from app.db import get_conn


def recommend_food(max_price=None, vegetarian=None, spicy=None):
    conn = get_conn()
    cur = conn.cursor()

    query = "SELECT * FROM foods WHERE 1=1"
    params = []

    if max_price is not None:
        query += " AND price <= ?"
        params.append(max_price)

    if vegetarian is not None:
        query += " AND vegetarian = ?"
        params.append(vegetarian)

    if spicy is not None:
        query += " AND spicy = ?"
        params.append(spicy)

    cur.execute(query, params)
    result = cur.fetchall()

    conn.close()

    return result
