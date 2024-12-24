# Tests inlezen.py
# Note that we cannot test functions that need access to the database
# We have not set up a dummy CKAN database to test that functionality
# and the production database contains privacy-sensitive data
#
# As of now, setting up this database is out-of-scope.
# If this changes, see the following websites to get started with setting up a
# database in GitHub Actions:
#   https://docs.ckan.org/en/latest/maintaining/installing/index.html#
#   https://github.com/Pooya-Oladazimi/ckanext-my-first-cool-extension/tree/main
import numpy as np
import pytest

from snuffelfiets.inlezen import *


def test_is_date_matching():
    assert is_date_matching("2024-11-11")
    assert is_date_matching("2024-11-12")
    assert is_date_matching("2024-12-31")
    assert not is_date_matching("2024-11-31")
    assert not is_date_matching("fake date")


def test_build_sql_statement_default():
    # This function is always called with a lot of arguments, usually
    # from within call_api
    # We could be smarter with our SQL queries to make fetches faster
    # TODO: Test smart fetching and/or more solid SQL queries
    sql_args = {
        "columns": "*",
        "datastore": "provincie_utrecht_snuffelfiets_measurement_rydruofi",
        "conditions": [
            {"col": "recording_timestamp", "op": ">", "val": "2024-11-11"},
            {"col": "recording_timestamp", "op": "<", "val": "2024-11-13"},
        ],
        "parameters": {"limit": 32000},
    }
    statement = build_sql_statement(**sql_args)
    assert (
        statement
        == 'SELECT * FROM "provincie_utrecht_snuffelfiets_measurement_rydruofi" WHERE "recording_timestamp" > \'2024-11-11\' AND "recording_timestamp" < \'2024-11-13\' LIMIT 32000'
    )


def test_drop_columns_default(test_data):
    df = test_data
    assert "_full_text" in df.columns
    df = drop_columns(df)
    assert "_full_text" not in df.columns


def test_drop_columns_custom_columns(test_data):
    df = test_data
    assert "horizontal_accuracy" in df.columns
    assert "receive_timestamp" in df.columns
    df = drop_columns(df, columns=["horizontal_accuracy", "receive_timestamp"])
    assert "horizontal_accuracy" not in df.columns
    assert "receive_timestamp" not in df.columns


def test_convert_to_int_default(test_data):
    df = test_data
    for column in ["entity_id", "version_major", "version_minor", "error_code"]:
        assert np.dtype("int64") is not df["entity_id"].dtype
    df = convert_to_int(df)
    for column in ["entity_id", "version_major", "version_minor", "error_code"]:
        assert np.dtype("int64") is df["entity_id"].dtype
