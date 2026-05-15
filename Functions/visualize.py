from plots import histogram, scatter_plot, box_plot
from interactive import interactive_scatter


# STATIC VISUALIZATION PIPELINE
def run_visualization(df, target, x_col=None):
    figs = {}
    figs["histogram"] = histogram(df, target)
    figs["boxplot"]   = box_plot(df, target)
    if x_col:
        figs["scatter"] = scatter_plot(df, x_col, target)
    return figs


# INTERACTIVE PIPELINE
def run_interactive_visualization(df, x_col, y_col):
    figs = {}
    figs["scatter"] = interactive_scatter(df, x_col, y_col)
    return figs
