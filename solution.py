import re
import pandas as pd


def _is_valid_col_name(name: str) -> bool:
    return isinstance(name, str) and bool(re.fullmatch(r"[A-Za-z_]+", name.strip()))


def add_virtual_column(df: pd.DataFrame, role: str, new_column: str) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame([])

    if not isinstance(role, str) or not role.strip():
        return pd.DataFrame([])

    if not _is_valid_col_name(new_column):
        return pd.DataFrame([])

    target_col = new_column.strip()
    operators = {"+", "-", "*"}

    # Rozdzielamy operatory spacjami, aby obsłużyć np. "a+b" i "  a + b  "
    expr = role.strip()
    for op in operators:
        expr = expr.replace(op, f" {op} ")

    # Wyrażenie musi mieć nieparzystą liczbę elementów: kolumna, op, kolumna itp. itd.
    parts = expr.split()
    if len(parts) < 3 or len(parts) % 2 == 0:
        return pd.DataFrame([])

    for i, token in enumerate(parts):
        if i % 2 == 0:
            if not _is_valid_col_name(token) or token not in df.columns:
                return pd.DataFrame([])
        else:
            if token not in operators:
                return pd.DataFrame([])

    result = df.copy()

    try:
        current = result[parts[0]]
        for i in range(1, len(parts), 2):
            op = parts[i]
            next_series = result[parts[i + 1]]

            if op == "+":
                current = current + next_series
            elif op == "-":
                current = current - next_series
            elif op == "*":
                current = current * next_series

        result[target_col] = current
        return result
    except (TypeError, ValueError):
        return pd.DataFrame([])