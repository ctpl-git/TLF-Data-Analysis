import pandas as pd
import numpy as np
from scipy import stats


# DESCRIPTIVE STATS
def describe(df: pd.DataFrame):
    return df.describe(include="all").T


# CORRELATION
def correlation_matrix(df: pd.DataFrame):
    return df.corr(numeric_only=True)


# HYPOTHESIS TESTS
def t_test(a, b):
    a, b = a.dropna(), b.dropna()
    stat, p = stats.ttest_ind(a, b, equal_var=False)
    return {"test": "t-test", "stat": stat, "p": p}


def chi_square(df, col1, col2):
    table = pd.crosstab(df[col1], df[col2])
    stat, p, _, _ = stats.chi2_contingency(table)
    return {"test": "chi-square", "stat": stat, "p": p}


def anova(df, value_col, group_col):
    groups = [g[value_col].dropna() for _, g in df.groupby(group_col)]
    stat, p = stats.f_oneway(*groups)
    return {"test": "anova", "stat": stat, "p": p}


# AUTO TEST SELECTOR
def auto_test(df, target, feature):
    if pd.api.types.is_numeric_dtype(df[target]) and pd.api.types.is_numeric_dtype(df[feature]):
        return {"feature": feature, **correlation_test(df[target], df[feature])} # numeric vs numeric → correlation

    elif pd.api.types.is_numeric_dtype(df[target]):
        groups = df[feature].dropna().unique()
        if len(groups) == 2:
            return {"feature": feature, **t_test(df[df[feature] == groups[0]][target], 
                                                  df[df[feature] == groups[1]][target])} # numeric vs categorical with 2 groups → t-test 
        else:
            return {"feature": feature, **anova(df, target, feature)} # numeric vs categorical with >2 groups → ANOVA

    else:
        return {"feature": feature, **chi_square(df, target, feature)} # categorical vs categorical → chi-square


def correlation_test(a, b):
    stat, p = stats.pearsonr(a.dropna(), b.dropna())
    return {"test": "pearson", "stat": stat, "p": p}