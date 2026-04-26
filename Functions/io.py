import pandas as pd
import os


def read_data(filepath: str, table_name: str = None):
    try:
        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".csv":
            return pd.read_csv(filepath)

        elif ext == ".xlsx":
            return pd.read_excel(filepath)

        elif ext == ".json":
            return pd.read_json(filepath)

        elif ext == ".xml":
            return pd.read_xml(filepath)

        elif ext == ".parquet":
            return pd.read_parquet(filepath)

        elif ext == ".sql":
            import sqlite3

            if not table_name:
                raise ValueError("Table name must be provided for SQL files")

            conn = sqlite3.connect(filepath)
            try:
                return pd.read_sql(f"SELECT * FROM {table_name}", conn)
            finally:
                conn.close()

        elif ext == ".html":
            tables = pd.read_html(filepath)
            if not tables:
                raise ValueError("No tables found in HTML file")
            return tables[0]

        elif ext == ".txt":
            return pd.read_csv(filepath, delimiter="\t")

        else:
            raise ValueError(f"Unsupported file format: {ext}")

    except Exception as e:
        raise RuntimeError(f"Failed to read '{filepath}': {e}")


def write_data(df, filepath: str, table_name: str = None):
    try:
        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".csv":
            df.to_csv(filepath, index=False)

        elif ext == ".xlsx":
            df.to_excel(filepath, index=False)

        elif ext == ".json":
            df.to_json(filepath, orient="records")

        elif ext == ".xml":
            df.to_xml(filepath, index=False)

        elif ext == ".parquet":
            df.to_parquet(filepath, index=False)

        elif ext == ".sql":
            import sqlite3

            if not table_name:
                raise ValueError("Table name must be provided for SQL files")

            conn = sqlite3.connect(filepath)
            try:
                df.to_sql(table_name, conn, if_exists="replace", index=False)
            finally:
                conn.close()

        elif ext == ".html":
            df.to_html(filepath, index=False)

        elif ext == ".txt":
            df.to_csv(filepath, index=False, sep="\t")

        else:
            raise ValueError(f"Unsupported file format: {ext}")

    except Exception as e:
        raise RuntimeError(f"Failed to write '{filepath}': {e}")