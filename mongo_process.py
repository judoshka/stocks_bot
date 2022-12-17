from pymongo import MongoClient
import pandas as pd
import datetime



def get_stock(mongo_collection, name):
    return mongo_collection.find_one({'name': name})


def get_dataframe(data, field='last_intervals'):
    df = pd.DataFrame()
    sub_data = data[field][::-1]
    df['Price'] = [item[1] for item in sub_data]
    df['Date'] = [datetime.datetime.fromtimestamp(item[-2]) for item in sub_data]
    df.set_index('Date', inplace=True)
    return df



client = MongoClient('mongodb://localhost:27017/')
db = client['hackaton']
db_collection = db['data']


data = get_stock(db_collection, 'Яндекс')


