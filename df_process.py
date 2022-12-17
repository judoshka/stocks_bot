from mongo_app import make_sub_prediction, make_d_matrix_column
import pandas as pd
import numpy as np
from rec import recommendations
from math_method import optimization


def make_income_matrix(risk_value):
    data = make_sub_prediction(risk_value)
    ids = list()
    opt = list()
    pes = list()
    mix = list()
    for item in data:
        ids.append(item[0])
        opt.append(item[1])
        pes.append(item[2])
        mix.append(item[3])

    return pd.DataFrame({
        "Id": np.array(ids),
        "Optim": np.array(opt),
        "Pessim": np.array(pes),
        "Mix": np.array(mix)
    })


def make_d_matrix(stock_names):
    data = [make_d_matrix_column(stock_name) for stock_name in stock_names]
    return pd.DataFrame(data).transpose()


def make_recommendation(risk_value):
    income_df = make_income_matrix(risk_value)
    x1, x2 = recommendations(income_df.set_index('Id'), risk_value, n=5)
    return x2


def make_portfel(risk_value):
    income_df = make_income_matrix(risk_value)
    income_df.set_index('Id', inplace=True)
    x1, x2 = recommendations(income_df, risk_value, n=5)
    D_matrix = make_d_matrix(x1)
    # income_df = make_income_matrix(risk_value)
    res = optimization(D_matrix.values, income_df, risk_value, stock_names=x1)
    return res


if __name__ == '__main__':
    pass