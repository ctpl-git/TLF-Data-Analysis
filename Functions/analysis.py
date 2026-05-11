import pandas as pd

from dataset import Dataset
from stats import describe, correlation_matrix, auto_test
from modeling import linear_regression


def run_analysis(df, schema, target):

    ds = Dataset(df, schema)
    ds.validate()

    clean_df = ds.df

    # Descriptive
    desc = describe(clean_df)

    # Correlation
    corr = correlation_matrix(clean_df)

    # Hypothesis tests
    tests = []
    for col in clean_df.columns:
        if col != target:
            try:
                tests.append(auto_test(clean_df, target, col))
            except:
                pass

    # Regression
    predictors = [
        c for c in clean_df.columns
        if c != target and pd.api.types.is_numeric_dtype(clean_df[c])
    ]

    model = linear_regression(clean_df, target, predictors)

    return {
        "dataset": ds,
        "descriptive": desc,
        "correlation": corr,
        "tests": pd.DataFrame(tests),
        "model": model
    }


# QUICK MODE
def run_quick_analysis(df, target):

    schema = {
        col: type("Meta", (), {
            "role": "target" if col == target else "continuous"
        })()
        for col in df.columns
    }

    return run_analysis(df, schema, target)