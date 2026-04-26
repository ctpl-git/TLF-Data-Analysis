def handle_missing(df, strategy="drop", fill_value=None):
    if strategy == "drop":
        return df.dropna()
    elif strategy == "fill":
        return df.fillna(fill_value)
    elif strategy == "drop_duplicates":
        return df.drop_duplicates()
    elif strategy == "replace":
        return df.replace(fill_value)
    else:
        raise ValueError(f"Invalid strategy: {strategy}")


def handle_invalid(df, column, condition, replacement=None):
    """
    condition: function that returns True for valid values
    """
    mask = df[column].apply(condition)

    df = df.copy()  # Avoid modifying original DataFrame

    if replacement is None:
        return df[mask]
    else:
        df.loc[~mask, column] = replacement
        return df