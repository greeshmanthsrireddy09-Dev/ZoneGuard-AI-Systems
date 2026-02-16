import pandas as pd

from data.simulate import generate_synthetic_data


def test_generate_synthetic_data_shape_and_columns() -> None:
    df = generate_synthetic_data(n_zones=3, hours=48, seed=42)
    assert len(df) == 3 * 48
    expected = {"zone_id", "timestamp", "demand", "drivers", "inventory", "weather", "availability"}
    assert expected.issubset(set(df.columns))


def test_generate_synthetic_data_availability_bounds() -> None:
    df = generate_synthetic_data(n_zones=2, hours=24, seed=99)
    assert (df["availability"] >= 0).all()
    assert (df["availability"] <= 1).all()
