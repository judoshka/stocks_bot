import pymongo
from pymongo import MongoClient
from utils import value_to_type, risk_to_index
from mongo_init_data import users


client = MongoClient('mongodb://localhost:27017/')
db = client['hackaton']
user_col = db['users']
data_col = db['data']


def insert_stock(item) -> None:
    data_col.insert_one(item)


def insert_user(user_obj) -> None:
    user_col.insert_one({
        "user_id": user_obj['user_id'],
        'name': user_obj['name'],
        "type": value_to_type(user_obj['type_value']),
        "type_value": user_obj['type_value'],
        "risk_value": user_obj['risk_value'],
        'income': user_obj.get('income', 0),
        "amount": user_obj.get('amount', 10_000),
        "history": user_obj.get('history', [])
        }
    )


def get_user(user_id) -> dict:
    return user_col.find_one({'user_id': user_id})


def get_top_investors(N=5) -> list:
    data = [
        tuple(user.values()) for user in user_col.find(
            {},
            {'_id': 0, 'name': 1, 'type': 1}).sort('type_value', pymongo.DESCENDING).limit(N)
    ]
    return data


def get_stock(name):
    return data_col.find_one({'name': name})


def get_stock_names():
    return [i['name'] for i in data_col.find({}, {'_id': 0, 'name': 1})]


def write_predictions(stock_name, arima_prediction: list, auto_arima_prediction: list):
    data_col.update_one(
        {'name': stock_name},
        {"$set": {
            'arima_prediction': arima_prediction,
            'auto_arima_prediction': auto_arima_prediction
        }}
    )


def make_sub_prediction(risk_value: float):
    res = [
        item for item in data_col.find({},
                                       {'_id': 0,
                                        'name': 1,
                                        'arima_prediction': 1,
                                        'auto_arima_prediction': 1,
                                        'data': 1})
    ]
    index = risk_to_index(risk_value)
    data = []
    for stock in res:
        value = stock['data'][-1][1]
        name = stock['name']
        values = (stock['arima_prediction'][index], stock['auto_arima_prediction'][index])
        best = (max(values) - value) / value * 100
        worst = (min(values) - value) / value * 100
        middle = (best + worst) / 2
        data.append((name, best, worst, middle))

    return data


def make_d_matrix_column(stock_name):
    res = data_col.find_one({'name': stock_name},
                            {'_id': 0, 'arima_prediction': 1, 'auto_arima_prediction': 1, 'data': 1})
    value = res['data'][-1][1]
    data = []
    for i in range(1, 6):
        index = 43 * i
        predicted_value = (res['arima_prediction'][index] + res['auto_arima_prediction'][index]) / 2
        data.append((predicted_value - value) / value * 100)

    return data


if __name__ == '__main__':
    for i in user_col.find({}, {'user_id': 1}):
        print(i)
