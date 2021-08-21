# pylint: disable=too-many-lines
"""
Tests for the Datasette adapter.
"""
import pytest

from ...fakes import datasette_columns_response
from ...fakes import datasette_data_response_1
from ...fakes import datasette_data_response_2
from ...fakes import datasette_metadata_response
from ...fakes import datasette_results
from shillelagh.adapters.api.datasette import DatasetteAPI
from shillelagh.adapters.api.datasette import get_field
from shillelagh.backends.apsw.db import connect
from shillelagh.exceptions import ProgrammingError
from shillelagh.fields import Float
from shillelagh.fields import Integer
from shillelagh.fields import ISODate
from shillelagh.fields import ISODateTime
from shillelagh.fields import String


def test_datasette(requests_mock):
    """
    Test a simple query.
    """
    columns_url = (
        "https://global-power-plants.datasettes.com/global-power-plants.json?"
        "sql=SELECT+*+FROM+%22global-power-plants%22+LIMIT+0"
    )
    requests_mock.get(columns_url, json=datasette_columns_response)
    metadata_url = (
        "https://global-power-plants.datasettes.com/global-power-plants.json?sql=SELECT+"
        "MAX%28%22country%22%29%2C+"
        "MAX%28%22country_long%22%29%2C+"
        "MAX%28%22name%22%29%2C+"
        "MAX%28%22gppd_idnr%22%29%2C+"
        "MAX%28%22capacity_mw%22%29%2C+"
        "MAX%28%22latitude%22%29%2C+"
        "MAX%28%22longitude%22%29%2C+"
        "MAX%28%22primary_fuel%22%29%2C+"
        "MAX%28%22other_fuel1%22%29%2C+"
        "MAX%28%22other_fuel2%22%29%2C+"
        "MAX%28%22other_fuel3%22%29%2C+"
        "MAX%28%22commissioning_year%22%29%2C+"
        "MAX%28%22owner%22%29%2C+"
        "MAX%28%22source%22%29%2C+"
        "MAX%28%22url%22%29%2C+"
        "MAX%28%22geolocation_source%22%29%2C+"
        "MAX%28%22wepp_id%22%29%2C+"
        "MAX%28%22year_of_capacity_data%22%29%2C+"
        "MAX%28%22generation_gwh_2013%22%29%2C+"
        "MAX%28%22generation_gwh_2014%22%29%2C+"
        "MAX%28%22generation_gwh_2015%22%29%2C+"
        "MAX%28%22generation_gwh_2016%22%29%2C+"
        "MAX%28%22generation_gwh_2017%22%29%2C+"
        "MAX%28%22generation_data_source%22%29%2C+"
        "MAX%28%22estimated_generation_gwh%22%29+"
        "FROM+%22global-power-plants%22+LIMIT+1"
    )
    requests_mock.get(metadata_url, json=datasette_metadata_response)
    data_url_1 = (
        "https://global-power-plants.datasettes.com/global-power-plants.json?"
        "sql=SELECT+*+FROM+%22global-power-plants%22"
    )
    requests_mock.get(data_url_1, json=datasette_data_response_1)
    data_url_2 = (
        "https://global-power-plants.datasettes.com/global-power-plants.json?"
        "sql=SELECT+%2A+FROM+%22global-power-plants%22+OFFSET+1000"
    )
    requests_mock.get(data_url_2, json=datasette_data_response_2)

    connection = connect(":memory:")
    cursor = connection.cursor()
    sql = """
        SELECT * FROM
        "datasette+https://global-power-plants.datasettes.com/global-power-plants/global-power-plants"
    """
    data = list(cursor.execute(sql))
    assert data == datasette_results


def test_datasette_no_data(mocker):
    """
    Test result with no rows.
    """
    CachedSession = mocker.patch(  # pylint: disable=invalid-name
        "shillelagh.adapters.api.datasette.requests_cache.CachedSession",
    )
    CachedSession.return_value.get.return_value.json.return_value = {
        "columns": [],
        "rows": [],
    }

    with pytest.raises(ProgrammingError) as excinfo:
        DatasetteAPI("https://example.com", "database", "table")
    assert str(excinfo.value) == 'Table "table" has no data'


def test_get_metadata(requests_mock):
    """
    Test ``get_metadata``.
    """
    requests_mock.get(
        "https://example.com/database.json?sql=SELECT+%2A+FROM+%22table%22+LIMIT+0",
        json={"columns": ["a", "b"]},
    )
    requests_mock.get(
        (
            "https://example.com/database.json?"
            "sql=SELECT+MAX%28%22a%22%29%2C+MAX%28%22b%22%29+FROM+%22table%22+LIMIT+1"
        ),
        json={"rows": [[1, 2], [3, 4]]},
    )
    requests_mock.get(
        "https://example.com/-/metadata.json",
        json={
            "databases": {"database": {"tables": {"table": {"foo": "bar"}}}},
        },
    )

    adapter = DatasetteAPI("https://example.com", "database", "table")
    assert adapter.get_metadata() == {"foo": "bar"}


def test_get_field():
    """
    Test ``get_field``.
    """
    assert isinstance(get_field(1), Integer)
    assert isinstance(get_field(1.1), Float)
    assert isinstance(get_field("test"), String)
    assert isinstance(get_field("2021-01-01"), ISODate)
    assert isinstance(get_field("2021-01-01 00:00:00"), ISODateTime)
    assert isinstance(get_field(None), String)
