from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def test_data() -> pd.DataFrame:
    data_path = (Path(__file__) / "../data/test_data.csv").resolve()
    df = pd.read_csv(data_path)
    # Our CKAN API gets some data as objects instead of ints
    # To emulate that, we convert the dtypes of certain columns here
    for column in ["entity_id", "version_major", "version_minor", "error_code"]:
        df[column] = df[column].astype(object)
    # The original API call has the column _full_text. Reconstruct a fake one
    # for the tests
    df["_full_text"] = "fake data"
    return df
