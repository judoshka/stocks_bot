import numpy as np
import pandas as pd
from scipy.optimize import minimize

def average_d(D):
    m,n= D.shape
    d= np.zeros([n,1])
    for j in np.arange(0,n):
        for i in np.arange(0,m):
            d[j,0]=d[j,0]+D[i,j]
    return d/n

def cov_between_bond(D):
    m,n = D.shape
    CV= np.zeros([m,n])
    for i in np.arange(0,m):
        for j in np.arange(0,n):
            x=np.array(D[0:m,j]).T
            y=np.array(D[0:m,i]).T
            X = np.vstack((x,y))
            CV[i,j]=round(np.cov(x,y,ddof=0)[1,0],3)
    return CV

#Ограничения
def constraint1(x):
    return np.sum(x)-1
    
def constraint2(x):
    global CV
    global risk
    
    m,n = CV.shape
    X = np.array([x]*m)
    result = 0
    for i in range(m):
        for j in range(n):
            result+=X[i,j]*CV[i,j]
    return result-risk       

def risc(data, alpha=0.5):
    arr = np.array([])
    first_list = data["Optim"].values
    second_list = data["Pessim"].values
    third_list = data["Mix"].values
    arr = np.append(arr, alpha*np.min(first_list)+(1-alpha)*np.max(first_list))
    arr = np.append(arr, alpha*np.min(second_list)+(1-alpha)*np.max(second_list))
    arr = np.append(arr, alpha*np.min(third_list)+(1-alpha)*np.max(third_list))
    maximum = np.max(arr)
    arr = np.array([])
    arr = np.append(arr, np.min(first_list))
    arr = np.append(arr, np.min(second_list))
    arr = np.append(arr, np.min(third_list))
    minimum = np.min(arr)
    return maximum-minimum

def bound():
    b = (0.0, 1.0)
    return (b,b,b,b,b)

def point_func(x):
    global d_avg
    
    return np.sum(d_avg*x)

def optimization(D_matrix, df, alpha, stock_names):
    global CV
    global d_avg
    global risk
    
    risk = risc(df, alpha=alpha) # alpha коэффициент, который мы определяем при регестрации
    d_avg = average_d(D=D_matrix)
    CV = cov_between_bond(D=D_matrix)
    x0=np.array([1,1,0,0,0])
    con1={'type':'eq','fun':constraint1}
    con2={'type':'ineq','fun':constraint2}
    cons=[con1,con2]
    bounds = bound()
    sol=minimize(point_func,x0,method='SLSQP',\
                 bounds=bounds,constraints=cons)
    string = 'Доля акций для покупки:\n'
    for i in range(len(sol.x)):
        string += stock_names[i] + ': ' + str(round(sol.x[i] / np.sum(sol.x), 2)) + '\n'
    string += '\nДоходность: ' + str(round(sol.fun, 2))
    return string