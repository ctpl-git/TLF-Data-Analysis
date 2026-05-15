import plotly.express as px
import pandas as pd


# INTERACTIVE SCATTER
def interactive_scatter(df, x_col, y_col):
    fig = px.scatter(df, x=x_col, y=y_col)
    return fig


# INTERACTIVE LINE
def interactive_line(df, x_col, y_col):
    df = df.copy()
    df[x_col] = pd.to_datetime(df[x_col], errors="ignore")
    fig = px.line(df, x=x_col, y=y_col)
    return fig


# INTERACTIVE HISTOGRAM
def interactive_histogram(df, column):
    fig = px.histogram(df, x=column)
    return fig
