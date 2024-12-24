""" Test internal pytest functions """

from pathlib import Path

from IPython import embed  # pylint: disable=unused-import # noqa: F401


def test_import():
    """Test if we can load pytest"""
    import pytest
