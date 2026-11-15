from importlib.resources import files

import pytest


@pytest.fixture(scope="session")
def fixture_csv() -> str:
    fixture = files("transformation_workbench").joinpath(
        "data",
        "synthetic_cases.csv",
    )
    return fixture.read_text(encoding="utf-8")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
