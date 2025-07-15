from pathlib import Path
import shutil
import pytest
from _pytest._py.path import LocalPath

from conftest import FIETSERSBOND_DIR, DATA_DIR
from snuffelfiets import routefilter as rf


# DATA_DIR = Path(__file__).parent.resolve() / 'data'
# @pytest.mark.datafiles(DATA_DIR / "test_data.csv")
def test_filter_routes(tmpdir: LocalPath, test_data_copy):
    with tmpdir.as_cwd():
        # Routes filter assumes specific naming of CSV files
        # Recreate it in our tmpdir
        # We got a copy from test_data_copy
        year = 2024
        month = 9
        prefix = "mcu_gegevens"
        filename = f"{prefix}_{year}-{month:02d}.csv"
        shutil.move("test_data.csv", filename)
        dfR_list, routes = rf.read_routes(routes_directory=FIETSERSBOND_DIR)
        df = rf.read_data(
            data_directory=tmpdir, prefix=prefix, years=[year], months=[month]
        )
        rf.filter_routes(dfR_list, routes, df, output_directory=tmpdir)  # inplace
        # One gets one CSV per route. Should be
        n_out_csvs = 2 * len(list(FIETSERSBOND_DIR.glob("*.csv")))
        outlist = list(Path(tmpdir).glob("*-dfRoute-*.csv")) + list(
            Path(tmpdir).glob("*-dfOutput-*.csv")
        )
        assert (
            len(outlist) == n_out_csvs
        ), "Number of output CSVs is not equal to expected amount of files"


if __name__ == "__main__":
    test_filter_routes()
