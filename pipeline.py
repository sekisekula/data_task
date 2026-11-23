from pathlib import Path
import pandas as pd

from solution import add_virtual_column


def clean_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()

    cleaned.columns = [
        col.strip().lower().replace(" ", "_") for col in cleaned.columns
    ]

    for col in ["order_id", "region", "product", "order_date"]:
        if col in cleaned.columns:
            cleaned[col] = cleaned[col].fillna("").astype(str).str.strip()

    # Usuwamy powtórzony nagłówek w środku pliku oraz wiersz podsumowujący TOTAL na dole
    cleaned = cleaned[
        (cleaned["order_id"] != "")
        & (cleaned["order_id"].str.lower() != "order_id")
        & (cleaned["order_id"].str.upper() != "TOTAL")
        & (cleaned["region"].str.lower() != "region")
    ].copy()

    cleaned = cleaned.drop_duplicates().copy()

    cleaned["region"] = cleaned["region"].str.lower().str.capitalize()

    cleaned["quantity"] = pd.to_numeric(
        cleaned["quantity"].fillna("").astype(str).str.replace(" ", "", regex=False),
        errors="coerce",
    )
    cleaned["unit_price"] = pd.to_numeric(
        cleaned["unit_price"]
        .fillna("")
        .astype(str)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )

    cleaned["discount"] = pd.to_numeric(
        cleaned["discount"]
        .fillna("0")
        .astype(str)
        .str.strip()
        .replace("", "0")
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce",
    ).fillna(0.0)

    # Uzupełniamy brakującą cenę jednostkową stałą ceną znaną dla danego produktu
    price_by_product = (
        cleaned.dropna(subset=["unit_price"])
        .groupby("product")["unit_price"]
        .first()
    )
    missing_price_mask = cleaned["unit_price"].isna() & (cleaned["product"] != "")
    cleaned.loc[missing_price_mask, "unit_price"] = cleaned.loc[
        missing_price_mask, "product"
    ].map(price_by_product)

    cleaned = cleaned.dropna(subset=["quantity", "unit_price"]).copy()

    return cleaned


def run_pipeline(
    input_path: str | Path = "sales.csv",
    output_path: str | Path = "revenue_by_region.csv",
) -> pd.DataFrame:
    raw_df = pd.read_csv(input_path, dtype=str)
    cleaned_df = clean_sales_data(raw_df)

    # add_virtual_column obsługuje proste wyrażenia dwuargumentowe, więc liczymy w dwóch krokach
    with_gross = add_virtual_column(cleaned_df, "quantity * unit_price", "gross_revenue")
    if with_gross.empty:
        raise ValueError("Failed to calculate gross_revenue using add_virtual_column")

    with_revenue = add_virtual_column(with_gross, "gross_revenue - discount", "revenue")
    if with_revenue.empty:
        raise ValueError("Failed to calculate revenue using add_virtual_column")

    revenue_by_region = (
        with_revenue.groupby("region", as_index=False)["revenue"]
        .sum()
        .sort_values("region")
        .reset_index(drop=True)
    )
    revenue_by_region["revenue"] = revenue_by_region["revenue"].round(2)

    revenue_by_region.to_csv(output_path, index=False)
    return revenue_by_region


if __name__ == "__main__":
    run_pipeline()