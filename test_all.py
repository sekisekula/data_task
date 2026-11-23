import pandas as pd
from solution import add_virtual_column
from pipeline import clean_sales_data, run_pipeline

def test_virtual_column_does_not_mutate_input():
    df = pd.DataFrame({"a": [2, 4], "b": [3, 5]})
    original_cols = list(df.columns)

    result = add_virtual_column(df, "a * b", "prod")

    assert list(df.columns) == original_cols
    assert "prod" not in df.columns
    assert result["prod"].tolist() == [6, 20]


def test_virtual_column_rejects_unsupported_and_malformed_roles():
    df = pd.DataFrame({"a": [10, 20], "b": [2, 4]})

    for bad_role in ["a / b", "a ** b", "a +", "+ b", "a + + b", "a", "", None]:
        res = add_virtual_column(df, bad_role, "out")
        assert res.empty, f"Expected empty DataFrame for role={bad_role!r}"


def test_virtual_column_rejects_bad_df_or_incompatible_types():
    assert add_virtual_column(None, "a + b", "out").empty

    df_bad_add = pd.DataFrame({"a": ["abc", "def"], "b": [1, 2]})
    assert add_virtual_column(df_bad_add, "a + b", "out").empty

    df_bad_sub = pd.DataFrame({"a": ["abc", "def"], "b": ["x", "y"]})
    assert add_virtual_column(df_bad_sub, "a - b", "out").empty



def test_virtual_column_chained_operations():
    df = pd.DataFrame({"a": [2, 3], "b": [4, 5], "c": [1, 2]})
    res = add_virtual_column(df, "a * b - c", "net")
    assert res["net"].tolist() == [7, 13]


def test_clean_sales_data_fixes_anomalies():
    raw = pd.DataFrame(
        [
            ["Order ID", "Region", "Product", "Quantity ", "Unit Price", "Discount", "Order Date"],
            ["SO-1", "  west ", "Mouse", "2", "29.50", "", "2026-01-01"],
            ["SO-1", "  west ", "Mouse", "2", "29.50", "", "2026-01-01"],
            ["SO-2", "EAST", "Mouse", "1 000", "29,50", "10.00", "2026-01-02"],
            ["SO-3", "North", "Mouse", "3", "", "", "2026-01-03"],
            ["SO-4", "North", "Mouse", "-1", "29.50", "", "2026-01-04"],
            ["TOTAL", "", "", "1001", "", "10.00", ""],
        ],
        columns=["Order ID", "Region", "Product", "Quantity ", "Unit Price", "Discount", "Order Date"],
    )

    cleaned = clean_sales_data(raw)

    assert len(cleaned) == 4
    assert list(cleaned.columns) == [
        "order_id",
        "region",
        "product",
        "quantity",
        "unit_price",
        "discount",
        "order_date",
    ]
    assert cleaned["region"].tolist() == ["West", "East", "North", "North"]
    assert cleaned.loc[cleaned["order_id"] == "SO-2", "quantity"].iloc[0] == 1000
    assert cleaned.loc[cleaned["order_id"] == "SO-2", "unit_price"].iloc[0] == 29.5
    assert cleaned.loc[cleaned["order_id"] == "SO-3", "unit_price"].iloc[0] == 29.5
    assert cleaned.loc[cleaned["order_id"] == "SO-1", "discount"].iloc[0] == 0.0
    assert cleaned.loc[cleaned["order_id"] == "SO-4", "quantity"].iloc[0] == -1


def test_run_pipeline_on_temp_csv(tmp_path):
    csv_file = tmp_path / "sample_sales.csv"
    out_file = tmp_path / "out_revenue.csv"

    csv_file.write_text(
        "Order ID,Region,Product,Quantity ,Unit Price,Discount,Order Date\n"
        "SO-1,North,Desk lamp,2,39.90,9.80,2026-02-01\n"
        "SO-2, north ,Desk lamp,1,39.90,,2026-02-02\n"
        "SO-3,South,Mouse,4,29.50,,2026-02-03\n",
        encoding="utf-8",
    )

    agg = run_pipeline(input_path=csv_file, output_path=out_file)

    assert out_file.exists()
    assert list(agg.columns) == ["region", "revenue"]
    north_rev = agg.loc[agg["region"] == "North", "revenue"].iloc[0]
    south_rev = agg.loc[agg["region"] == "South", "revenue"].iloc[0]
    # North: (2*39.90 - 9.80) + (1*39.90 - 0) = 70.00 + 39.90 = 109.90
    assert north_rev == 109.90
    # South: 4*29.50 - 0 = 118.00
    assert south_rev == 118.00


def test_run_pipeline_on_real_sales_csv():
    agg = run_pipeline()
    assert not agg.empty
    assert list(agg.columns) == ["region", "revenue"]
    assert agg["revenue"].isna().sum() == 0