import matplotlib.pyplot as plt
import pandas as pd


# TIME SERIES
def plot_timeseries(df, date_col, value_col, title=""):
    fig, ax = plt.subplots()
    dates = pd.to_datetime(df[date_col])
    ax.plot(dates, df[value_col])
    ax.set_title(title or value_col)
    return fig


# ROLLING AVERAGE
def plot_rolling_average(df, date_col, value_col, window=7):
    fig, ax = plt.subplots()
    dates = pd.to_datetime(df[date_col])
    rolling = df[value_col].rolling(window).mean()
    ax.plot(dates, df[value_col], alpha=0.5, label="original")
    ax.plot(dates, rolling, label="rolling mean")
    ax.legend()
    return fig
