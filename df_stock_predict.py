import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from mongo_app import get_stock, write_predictions, get_stock_names
import pmdarima as pm


PREDICTION_SIZE = 43 * 183


def get_stock_data(data):
    df = pd.DataFrame()
    sub_data = data['data']
    df['Price'] = [item[1] for item in sub_data]
    return df


def process_stock(stock_name):
    print(stock_name)
    stock = get_stock(stock_name)
    y = get_stock_data(stock)
    arima_model = ARIMA(y.Price, order=(2, 1, 2))
    model = arima_model.fit()
    arima_predictions = list(model.forecast(PREDICTION_SIZE))
    auto_arima = pm.auto_arima(y.Price, stepwise=False, seasonal=False)
    auto_predictions = list(auto_arima.predict(PREDICTION_SIZE))

    write_predictions(stock_name, arima_predictions, auto_predictions)


if __name__ == '__main__':
    for stock_name in get_stock_names():
        process_stock(stock_name=stock_name)



