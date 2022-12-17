import requests
import datetime
from mongo_app import insert_stock
DAY_IN_SEC = 86400
WEEK_IN_SEC = 604800


def process_data(data, N=20):
    reverse = data[::-1]
    last_intervals = reverse[:20]
    last_days_intervals = []
    last_weeks_intervals = []
    zero_date_timestamp = reverse[0][-2]
    zero_date = datetime.datetime.fromtimestamp(zero_date_timestamp)
    j = 0
    for i in reverse:
        date_timestamp = i[-2]
        date = datetime.datetime.fromtimestamp(date_timestamp)
        x = zero_date - date
        if x.seconds % DAY_IN_SEC == 0:
            last_days_intervals.append(i)
            j += 1
        if j == N:
            break
    j = 0
    for i in reverse:
        date_timestamp = i[-2]
        date = datetime.datetime.fromtimestamp(date_timestamp)
        x = zero_date - date
        if x.seconds % WEEK_IN_SEC == 0:
            last_weeks_intervals.append(i)
            j += 1
        if j == N:
            break

    return {
        'last_intervals': last_intervals,
        'last_days_intervals': last_days_intervals,
        'last_weeks_intervals': last_weeks_intervals,
    }


def get_data(stock_name, start_timestamp, end_timestamp):
    url = f"https://api.bcs.ru/udfdatafeed/v1/history?symbol={stock_name}" + \
    f"&resolution=15&from={start_timestamp}&to={end_timestamp}"
    r = requests.get(url)
    return r.json()


def make_column(data):
    column_data = []
    table = zip(data['t'], data['o'], data['h'], data['l'], data['c'], data['v'])

    for row in table:
        # Convert timestamp to datetime
        row = list(row)
        timestamp = row.pop(0)
        date = datetime.datetime.utcfromtimestamp(timestamp)
        row += [timestamp, date.isoformat()]
        column_data.append(row)

    return column_data


if __name__ == '__main__':
    data_to_mongo = []
    from_timestamp_parameter = 1656422100
    to_timestamp_parameter = 1671050700
    stocks = [
        ('YNDX', 'Яндекс', 'Рубль'),
        ('MGNT', 'Магнит', 'Рубль'),
        ('QIWI', 'Киви', 'Рубль'),
        ('SBER', 'Сбербанк', 'Рубль'),
        ('VTBR', 'ВТБ', 'Рубль'),
        ('SIBN', 'ГазПромНефть', 'Рубль'),
        ('LKOH', 'Лукойл', 'Рубль'),
        ('ROSN', 'Роснефть', 'Рубль'),
        ('GAZP', 'ГазПром', 'Рубль'),
        ('AGRO', 'РусАгро', 'Рубль'),
        ('ALRS', 'Алроса', 'Рубль'),
        ('APTK', 'Аптека 36.6', 'Рубль'),
        ('RUAL', 'РусАл', 'Рубль'),
        ('MOEX', 'Московская биржа', 'Рубль'),
        ('TSLA', 'Тесла', 'Доллар'),
        ('NVDA', 'NVidea', 'Доллар'),
        ('NFLX', 'Netflix', 'Доллар'),
        ('INTC', 'Intel', 'Доллар'),
        ('CROX', 'Crocs', 'Доллар'),
        ('BABA', 'Alibaba', 'Доллар')
    ]
    for stock in stocks:
        stock_name = stock[0]
        data = get_data(stock_name, start_timestamp=from_timestamp_parameter, end_timestamp=to_timestamp_parameter)
        column_data = make_column(data)
        data_to_mongo.append({
            'name': stock[1],
            'currency': stock[2],
            'api_name': stock_name,
            'data': column_data,
            **process_data(column_data)
        })

    for item in data_to_mongo:
        insert_stock(item)
