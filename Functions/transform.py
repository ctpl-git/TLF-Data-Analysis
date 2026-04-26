def filter_data(df, condition):
    """
    condition: function applied row-wise
    """
    mask = df.apply(condition, axis=1)
    return df[mask]


def select_columns(df, columns):
    return df[columns]


def add_column(df, column_name, func):
    df[column_name] = df.apply(func, axis=1)
    return df


def sort_data(df, by, ascending=True):
    return df.sort_values(by=by, ascending=ascending, ignore_index=True)

# groupby(), aggregate(), pivot_table(), merge(), sort_values(), value_counts() can be added as needed