from pathlib import Path
import pytest

from snuffelfiets import routefilter as rf

def test_filter_routes():
    dfR_list, routes = rf.read_routes()
    df = rf.read_data()
    rf.filter_routes(dfR_list, routes, df)
    root: Path = rf.main_directory_default
    output_directory = root / "Output"
    assert output_directory.exists(), "Output folder not created"
    assert len(list(output_directory.iterdir())) == 8, "Wrong amount of output files created!"

if __name__ == "__main__":
    test_filter_routes()
