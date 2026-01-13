"""Unit tests for Temporal Validation logic."""

import numpy as np
import pandas as pd

from hygeia_graph.temporal_validation import (
    check_equal_intervals,
    detect_time_type,
    validate_temporal_inputs,
)


class TestTemporalValidation:

    def test_detect_time_type(self):
        df = pd.DataFrame({
            "num": [1, 2, 3],
            "date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
            "str": ["a", "b", "c"]
        })
        assert detect_time_type(df["num"]) == "numeric"
        assert detect_time_type(df["date"]) == "datetime"
        assert detect_time_type(df["str"]) == "unknown"

    def test_equal_intervals_numeric(self):
        # Perfect
        df = pd.DataFrame({"time": [1, 2, 3, 4], "id": [1, 1, 1, 1]})
        res = check_equal_intervals(df, "id", "time")
        assert res["ok"]

        # Unequal
        df2 = pd.DataFrame({"time": [1, 2, 4, 5], "id": [1, 1, 1, 1]})
        res2 = check_equal_intervals(df2, "id", "time")
        assert not res2["ok"]
        assert "1" in res2["unequal_ids"]

    def test_equal_intervals_datetime(self):
        # Perfect days
        times = pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"])
        df = pd.DataFrame({"time": times, "id": [1, 1, 1]})
        res = check_equal_intervals(df, "id", "time")
        assert res["ok"]

        # Unequal (miss one day)
        times2 = pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-04"])
        df2 = pd.DataFrame({"time": times2, "id": [1, 1, 1]})
        res2 = check_equal_intervals(df2, "id", "time")
        assert not res2["ok"]

    def test_validation_rules(self):
        # Setup valid df
        df = pd.DataFrame({
            "time": range(30),
            "v1": np.random.randn(30),
            "v2": np.random.randn(30)
        })

        # 1. Base case
        ok, msgs, _ = validate_temporal_inputs(df, None, "time", ["v1", "v2"])
        assert ok

        # 2. Short series (<20)
        short_df = df.head(10)
        ok, msgs, _ = validate_temporal_inputs(short_df, None, "time", ["v1", "v2"])
        assert not ok
        assert any("too small" in m for m in msgs)

        # 3. Missing Data
        df_miss = df.copy()
        df_miss.loc[0, "v1"] = np.nan
        # Fails if impute="none"
        ok, msgs, _ = validate_temporal_inputs(df_miss, None, "time", ["v1", "v2"], impute="none")
        assert not ok
        assert any("Imputation required" in m for m in msgs)

        # Passes if impute="linear"
        ok, msgs, _ = validate_temporal_inputs(df_miss, None, "time", ["v1", "v2"], impute="linear")
        assert ok

        # 4. Unequal intervals requires strict unlock
        df_unequal = df.copy()
        df_unequal.loc[29, "time"] = 100 # Jump
        ok, msgs, _ = validate_temporal_inputs(df_unequal, None, "time", ["v1", "v2"], unequal_ok=False)
        assert not ok
        assert any("Unequal time intervals" in m for m in msgs)

        ok, msgs, _ = validate_temporal_inputs(df_unequal, None, "time", ["v1", "v2"], unequal_ok=True)
        assert ok
