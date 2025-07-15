import shutil
from pathlib import Path
import filecmp
import os

import pandas as pd
import pytest

DATA_DIR = Path(__file__).parent.resolve() / "data"
FIETSERSBOND_DIR = (DATA_DIR / "Fietsersbond").resolve()
# TEST_DATA_PATH = (DATA_DIR / "test_data.csv").resolve()


def test_data(TEST_DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(test_data_path)
    # Our CKAN API gets some data as objects instead of ints
    # To emulate that, we convert the dtypes of certain columns here
    for column in ["entity_id", "version_major", "version_minor", "error_code"]:
        df[column] = df[column].astype(object)
    # The original API call has the column _full_text. Reconstruct a fake one
    # for the tests
    df["_full_text"] = "fake data"
    return df


@pytest.fixture
def tmp_wd(tmp_path):
    """Changes working directory and returns to previous on exit.

    Mixes tmp_path from pytest and a cleanup that automatically moves
    back to where you started in cleanup.
    """
    prev_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(prev_cwd)


@pytest.fixture
def test_data_copy(tmp_wd):
    return copy_with_relink(tmp_wd, "test_data.csv")


def copy_with_relink(tmp_root: Path, file_or_dir_name: str):
    file_or_dir = (DATA_DIR / "test_data.csv").resolve()
    # Copy the full tree, copy_function will _not_ be used for symlinks
    if file_or_dir.is_dir():
        from IPython import embed

        embed()
        copied_dir = shutil.copytree(
            template_dir,
            target_dir,
            symlinks=True,
            ignore=shutil.ignore_patterns("PLACEHOLDER*"),
        )
    else:
        copied_file = shutil.copy(file_or_dir, tmp_root)
        assert filecmp.cmp(copied_file, file_or_dir)
        target_dir = Path(copied_file).parent

    # Move into the newly created path
    # Assume wrapping function will move us back with tmp_wd
    os.chdir(target_dir)
    return target_dir
