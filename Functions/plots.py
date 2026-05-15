import matplotlib.pyplot as plt


# BAR CHART
def bar_chart(labels, values, title=""):
    fig, ax = plt.subplots()
    ax.bar(labels, values)
    ax.set_title(title)
    return fig


# LINE CHART
def line_chart(x, y, title=""):
    fig, ax = plt.subplots()
    ax.plot(x, y)
    ax.set_title(title)
    return fig


# SCATTER PLOT
def scatter_plot(df, x_col, y_col, title=""):
    fig, ax = plt.subplots()
    ax.scatter(df[x_col], df[y_col])
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(title)
    return fig


# HISTOGRAM
def histogram(df, column, bins=20, title=""):
    fig, ax = plt.subplots()
    ax.hist(df[column].dropna(), bins=bins)
    ax.set_title(title or f"Distribution of {column}")
    return fig


# BOX PLOT
def box_plot(df, column, title=""):
    fig, ax = plt.subplots()
    ax.boxplot(df[column].dropna())
    ax.set_title(title or f"Box Plot of {column}")
    return fig
