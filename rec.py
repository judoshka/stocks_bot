import numpy as np


def recommendations(data, alpha=0.5, n=5):
    arr = np.array([])
    first_list = data["Optim"].values
    second_list = data["Pessim"].values
    third_list = data["Mix"].values
    arr = np.append(arr, alpha*np.min(first_list)+(1-alpha)*np.max(first_list))
    arr = np.append(arr, alpha*np.min(second_list)+(1-alpha)*np.max(second_list))
    arr = np.append(arr, alpha*np.min(third_list)+(1-alpha)*np.max(third_list))
    result = np.max(arr)
    data['All'] = ((data["Optim"]+data["Pessim"]+data["Mix"])/3-result).apply(abs)
    data.sort_values(by='All', ascending=True, inplace=True)
    string = np.array2string(data.index.values[0:n], separator='|')
    
    return data.index.values[0:n], f'Список акций рекомендуемых вам: {string}'