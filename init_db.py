from mongo_app import get_stock_names, get_user, insert_stock, insert_user
import json


def read_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


if __name__ == '__main__':
    stocks = read_json('stocks.json')
    stock_names = get_stock_names()
    for stock in stocks:
        stock_name = stock['name']
        if stock_name not in stock_names:
            insert_stock(stock)

    users = read_json('users.json')
    for user in users:
        user_id = user['user_id']
        if isinstance(user_id, dict):
            user_id = int(user_id['$numberLong'])
        if not get_user(user_id):
            insert_user(user)

