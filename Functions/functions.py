# TODO:
# Develop workflow for different data types (For example: read excel data, clean excel data, extract fields and data, represent fields and data into JSON file)
# Develop a list of functions needed for the workflow
# Code the functions and then interlink the functions as per the workflow

from .io import read_data, write_data
from .cleaning import handle_missing
from .transform import sort_data

def run_pipeline(input_path, output_path):
    df = read_data(input_path)
    df = handle_missing(df, strategy="drop")
    df = sort_data(df, by=df.columns[0])
    write_data(df, output_path)
    return df