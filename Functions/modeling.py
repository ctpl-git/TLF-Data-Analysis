import numpy as np
import pandas as pd


def linear_regression(df, target, predictors):
    data = df[[target] + predictors].dropna()

    y = data[target].values
    X = data[predictors].values

    X = np.column_stack([np.ones(len(X)), X])

    beta = np.linalg.lstsq(X, y, rcond=None)[0]

    y_hat = X @ beta
    residuals = y - y_hat

    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)

    r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0

    return {
        "coefficients": beta,
        "r2": r2,
        "residuals": residuals
    }