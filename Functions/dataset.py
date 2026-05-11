import pandas as pd


class Dataset:
    def __init__(self, df: pd.DataFrame, schema: dict):
        self.df = df.copy()
        self.schema = schema

    def validate(self):
        errors = []

        for col in self.schema:
            if col not in self.df.columns:
                errors.append(f"Missing column: {col}")

        if errors:
            raise ValueError("\n".join(errors))

        return True

    def get_cols_by_role(self, role):
        return [
            c for c, m in self.schema.items()
            if m.role == role and c in self.df.columns
        ]