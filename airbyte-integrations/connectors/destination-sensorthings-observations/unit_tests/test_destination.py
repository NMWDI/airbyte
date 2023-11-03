from unittest.mock import MagicMock 
import pytest
from pytest import fixture
from datetime import datetime
from typing import Any, Dict
import random
import string
import json
import time

from google.cloud import bigquery
from google.oauth2 import service_account
import os

from airbyte_cdk.models import (
    AirbyteMessage,
    AirbyteRecordMessage,
    AirbyteStateMessage,
    AirbyteStream,
    ConfiguredAirbyteCatalog,
    ConfiguredAirbyteStream,
    DestinationSyncMode,
    Status,
    SyncMode,
    Type,
)

from destination_sensorthings_observations import DestinationSensorthingsObservations

rand_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
RAND_STRING_WITH_NAME_MSG3 = "".join(["LEWIS N DIVERSION_", rand_string])

# Enter frost server url below. No slash at the end of url.
#FROST_SERVER = "http://...8080/FROST-Server/v1.1"

cwd = os.getcwd()

cred_file = os.path.join(cwd, "secrets/bq_creds.json")

service_account_info_dict = json.load(open(cred_file))

service_account_info = json.dumps(service_account_info_dict)

global_timestamp = int(datetime.now().timestamp())

@pytest.fixture
def config_isc():
    return {"config": {"destination_path": f"{FROST_SERVER}", "bigquery_credentials": service_account_info, "name": "ISC Seven Rivers Monitoring Points", "description": "ISC Seven Rivers Monitoring Point Locations", "agency": "isc", "source_api": "https://nmisc-wf.gladata.com/api/", "observation_category": "levels" }}


@pytest.fixture
def config_pecos():
    return {"config": {"destination_path": f"{FROST_SERVER}", "bigquery_credentials": service_account_info, "name": "Pecos Valley Locations", "description": "Pecos Valley Well Locations", "agency": "pvacd", "observation_category": "levels" }}


@pytest.fixture
def config_nmbgmr():
    return {"config": {"destination_path": f"{FROST_SERVER}", "bigquery_credentials": service_account_info, "name": "NMBGMR Wells", "description": "NMBGMR Wells", "agency": "nmbgmr", "observation_category": "levels" }}


@pytest.fixture
def config_ebid():
    return {"config": {"destination_path": f"{FROST_SERVER}", "bigquery_credentials": service_account_info, "name": "EBID Locations", "description": "EBID Locations", "agency": "ebid", "observation_category": "levels" }}


@pytest.fixture
def airbyte_message1():

    rand_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    rand_string_with_name = "".join(["Yellow_", rand_string])

    dateTime = int(datetime.now().timestamp()) * 1000

    return AirbyteMessage(
        type=Type.RECORD,
        record=AirbyteRecordMessage(
            stream="isc_water_levels", data={"monitoring_point_id": "177", "dateTime": dateTime,"depthToWaterFeet": 3289.1, "_airbyte_ab_id": "99407136-3e9f-421d-9894-86327cd99d87"}, emitted_at=int(datetime.now().timestamp()) * 1000
        ),
    )


@pytest.fixture
def airbyte_message6_pecos():
    rand_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    rand_string_with_name = "".join(["Transwestern Level_", rand_string])
    
    dateTime = int(datetime.now().timestamp())

    return AirbyteMessage(
        type=Type.RECORD,
        record=AirbyteRecordMessage(
            stream="pecos_readings", data={"locationId": "5525065881092096", "timestamp": dateTime, "value": 14.079, "_airbyte_ab_id": "99407136-3e9f-421d-9894-86327cd99d87"}, emitted_at=int(datetime.now().timestamp()) * 1000
        ),
    )


@pytest.fixture
def airbyte_message7_nmbgmr():
    rand_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    rand_string_with_name = "".join(["BW-0505_", rand_string])

    # Sleep 2 seconds in order to ensure a different time for this message
    time.sleep(2)
    timestamp = int(datetime.now().timestamp())

    dateTime = datetime.strftime(datetime.utcfromtimestamp(timestamp), '%Y-%m-%d %H:%M:%S UTC')

    print ("\n------------------------------------")
    print ("Two of the NMBGMR tests should give errors due to no location and no phenomenon time.")
    print ("------------------------------------\n")

    return AirbyteMessage(
        type=Type.RECORD,
        record=AirbyteRecordMessage(
            stream="nmbgmr_manual_gwl", data={"PointID": "PP-011", "DateTimeMeasured": dateTime, "DepthToWater": 66.0, "LevelStatus": "Operating Well", "_airbyte_ab_id": "99407136-3e9f-421d-9894-86327cd99d87"}, emitted_at=int(datetime.now().timestamp()) * 1000
        ),
    )


@pytest.fixture
def airbyte_message9_nmbgmr_null_result():
    rand_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    rand_string_with_name = "".join(["BW-0505_", rand_string])

    # Sleep 2 seconds in order to ensure a different time for this message
    time.sleep(2)
    timestamp = int(datetime.now().timestamp())

    dateTime = datetime.strftime(datetime.utcfromtimestamp(timestamp), '%Y-%m-%d %H:%M:%S UTC')

    return AirbyteMessage(
        type=Type.RECORD,
        record=AirbyteRecordMessage(
            stream="nmbgmr_manual_gwl", data={"PointID": "PP-011", "DateTimeMeasured": dateTime, "DepthToWater": None, "LevelStatus": "Well Dry", "_airbyte_ab_id": "99407136-3e9f-421d-9894-86327cd99d87"}, emitted_at=int(datetime.now().timestamp()) * 1000
        ),
    )


@pytest.fixture
def airbyte_message10_nmbgmr_missing_location():
    rand_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    rand_string_with_name = "".join(["BW-0505_", rand_string])

    # Sleep 2 seconds in order to ensure a different time for this message
    time.sleep(2)
    timestamp = int(datetime.now().timestamp())

    dateTime = datetime.strftime(datetime.utcfromtimestamp(timestamp), '%Y-%m-%d %H:%M:%S UTC')

    return AirbyteMessage(
        type=Type.RECORD,
        record=AirbyteRecordMessage(
            stream="nmbgmr_manual_gwl", data={"PointID": "aPP-011", "DateTimeMeasured": dateTime, "DepthToWater": 66.0, "LevelStatus": "Operating Well", "_airbyte_ab_id": "99407136-3e9f-421d-9894-86327cd99d87"}, emitted_at=int(datetime.now().timestamp()) * 1000
        ),
    )


@pytest.fixture
def airbyte_message11_nmbgmr_missing_datetime():
    rand_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    rand_string_with_name = "".join(["BW-0505_", rand_string])

    timestamp = int(datetime.now().timestamp())

    dateTime = datetime.strftime(datetime.utcfromtimestamp(timestamp), '%Y-%m-%d %H:%M:%S UTC')

    return AirbyteMessage(
        type=Type.RECORD,
        record=AirbyteRecordMessage(
            stream="nmbgmr_manual_gwl", data={"PointID": "PP-011", "DateTimeMeasured": None, "DepthToWater": 66.0, "LevelStatus": "Operating Well", "_airbyte_ab_id": "99407136-3e9f-421d-9894-86327cd99d87"}, emitted_at=int(datetime.now().timestamp()) * 1000
        ),
    )


@pytest.fixture
def airbyte_message12_nmbgmr():
    rand_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    rand_string_with_name = "".join(["BW-0505_", rand_string])

    # Sleep 2 seconds in order to ensure a different time for this message
    time.sleep(2)
    timestamp = int(datetime.now().timestamp())

    dateTime = datetime.strftime(datetime.utcfromtimestamp(timestamp), '%Y-%m-%d %H:%M:%S UTC')

    return AirbyteMessage(
        type=Type.RECORD,
        record=AirbyteRecordMessage(
            stream="nmbgmr_manual_gwl", data={"PointID": "PP-011", "DateTimeMeasured": dateTime, "DepthToWater": 100.0, "LevelStatus": "Well Dry", "_airbyte_ab_id": "99407136-3e9f-421d-9894-86327cd99d87"}, emitted_at=int(datetime.now().timestamp()) * 1000
        ),
    )


@pytest.fixture
def airbyte_message13_nmbgmr():
    rand_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    rand_string_with_name = "".join(["BW-0505_", rand_string])

    dateTime = datetime.strftime(datetime.utcfromtimestamp(global_timestamp), '%Y-%m-%d %H:%M:%S UTC')

    return AirbyteMessage(
        type=Type.RECORD,
        record=AirbyteRecordMessage(
            stream="nmbgmr_manual_gwl", data={"PointID": "PP-011", "DateTimeMeasured": dateTime, "DepthToWater": 200.0, "LevelStatus": "Well Dry", "_airbyte_ab_id": "99407136-3e9f-421d-9894-86327cd99d87"}, emitted_at=int(datetime.now().timestamp()) * 1000
        ),
    )


@pytest.fixture
def airbyte_message8_ebid():

    timestamp = int(datetime.now().timestamp())
    dateTime = datetime.strftime(datetime.utcfromtimestamp(timestamp), '%Y-%m-%d %H:%M:%S')

    return AirbyteMessage(
        type=Type.RECORD,
        record=AirbyteRecordMessage(
            stream="GetSiteMetaData", data={"site_id": "211-0000-M26R", "data_time": dateTime, "data_value": 33.9, "_airbyte_ab_id": "99407136-3e9f-421d-9894-86327cd99d87"}, emitted_at=int(datetime.now().timestamp()) * 1000
        ),
    )


@pytest.fixture(name="configured_catalog_isc")
def configured_catalog_fixture_isc() -> ConfiguredAirbyteCatalog:
    stream_schema = {"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}, "type": {"type": "string"}, "comments": {"type": "string"}, "latitude": {"type": "number"}, "longitude": {"type": "number"}, "groundSurfaceElevationFeet": {"type": "number"}, "_airbyte_ab_id": {"type": "string"}}}

    append_stream = ConfiguredAirbyteStream(
        stream=AirbyteStream(name="append_stream", json_schema=stream_schema, supported_sync_modes=[SyncMode.incremental]),
        sync_mode=SyncMode.incremental,
        destination_sync_mode=DestinationSyncMode.append,
    )
    
    return ConfiguredAirbyteCatalog(streams=[append_stream])


@pytest.fixture(name="configured_catalog_pecos")
def configured_catalog_fixture_pecos() -> ConfiguredAirbyteCatalog:
    stream_schema = {"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}, "type": {"type": "string"}, "comments": {"type": "string"}, "latitude": {"type": "number"}, "longitude": {"type": "number"}, "_airbyte_ab_id": {"type": "string"}}}

    append_stream = ConfiguredAirbyteStream(
        stream=AirbyteStream(name="append_stream", json_schema=stream_schema, supported_sync_modes=[SyncMode.incremental]),
        sync_mode=SyncMode.incremental,
        destination_sync_mode=DestinationSyncMode.append,
    )
    
    return ConfiguredAirbyteCatalog(streams=[append_stream])


@pytest.fixture(name="configured_catalog_nmbgmr")
def configured_catalog_fixture_nmbgmr() -> ConfiguredAirbyteCatalog:
    stream_schema = {"type": "object", "properties": {"id": {"type": "integer"}, "PointID": {"type": "string"}, "type": {"type": "string"}, "comments": {"type": "string"}, "Easting": {"type": "number"}, "Northing": {"type": "number"}, "Altitude": {"type": "number"}, "AltitudeAccuracy": {"type": "number"}, "WellDepth": {"type": "number"}, "CasingDiameter": {"type": "number"}, "HoleDepth": {"type": "number"}, "_airbyte_ab_id": {"type": "string"}}}

    append_stream = ConfiguredAirbyteStream(
        stream=AirbyteStream(name="append_stream", json_schema=stream_schema, supported_sync_modes=[SyncMode.incremental]),
        sync_mode=SyncMode.incremental,
        destination_sync_mode=DestinationSyncMode.append,
    )
    
    return ConfiguredAirbyteCatalog(streams=[append_stream])


@pytest.fixture(name="configured_catalog_ebid")
def configured_catalog_fixture_ebid() -> ConfiguredAirbyteCatalog:
    stream_schema = {"type": "object", "properties": {"site_id": {"type": "integer"}, "name": {"type": "string"}, "type": {"type": "string"}, "comments": {"type": "string"}, "latitude": {"type": "number"}, "longitude": {"type": "number"}, "_airbyte_ab_id": {"type": "string"}}}

    append_stream = ConfiguredAirbyteStream(
        stream=AirbyteStream(name="append_stream", json_schema=stream_schema, supported_sync_modes=[SyncMode.incremental]),
        sync_mode=SyncMode.incremental,
        destination_sync_mode=DestinationSyncMode.append,
    )
    
    return ConfiguredAirbyteCatalog(streams=[append_stream])


def test_check_connection(config_isc):

    destination = DestinationSensorthingsObservations()

    logger_mock = MagicMock()

    status = destination.check(logger_mock, **config_isc)

    assert status.status == Status.SUCCEEDED


def test_write_isc(
    config_isc,
    request,
    configured_catalog_isc: ConfiguredAirbyteCatalog,
    airbyte_message1: AirbyteMessage,
):

    config_unpacked = config_isc['config']

    destination = DestinationSensorthingsObservations()

    generator = destination.write(config_unpacked, configured_catalog_isc, [airbyte_message1])

    results = list(generator)

    assert len(results) == 1

    assert True


def test_write_pecos(
    config_pecos,
    request,
    configured_catalog_pecos: ConfiguredAirbyteCatalog,
    airbyte_message6_pecos: AirbyteMessage,
):

    config_unpacked = config_pecos['config']

    destination = DestinationSensorthingsObservations()

    generator = destination.write(config_unpacked, configured_catalog_pecos, [airbyte_message6_pecos])

    results = list(generator)

    assert len(results) == 1

    assert True


def test_write_nmbgmr(
    config_nmbgmr,
    request,
    configured_catalog_nmbgmr: ConfiguredAirbyteCatalog,
    airbyte_message7_nmbgmr: AirbyteMessage,
    airbyte_message9_nmbgmr_null_result: AirbyteMessage,
    airbyte_message10_nmbgmr_missing_location: AirbyteMessage,
    airbyte_message11_nmbgmr_missing_datetime: AirbyteMessage,
    airbyte_message12_nmbgmr: AirbyteMessage,
    airbyte_message13_nmbgmr: AirbyteMessage
):

    config_unpacked = config_nmbgmr['config']

    destination = DestinationSensorthingsObservations()

    generator = destination.write(config_unpacked, configured_catalog_nmbgmr, [airbyte_message7_nmbgmr, airbyte_message9_nmbgmr_null_result, airbyte_message10_nmbgmr_missing_location, airbyte_message11_nmbgmr_missing_datetime, airbyte_message12_nmbgmr, airbyte_message13_nmbgmr])

    results = list(generator)

    assert len(results) == 6

    assert True


def test_write_ebid(
    config_ebid,
    request,
    configured_catalog_ebid: ConfiguredAirbyteCatalog,
    airbyte_message8_ebid: AirbyteMessage,
):

    config_unpacked = config_ebid['config']

    destination = DestinationSensorthingsObservations()

    generator = destination.write(config_unpacked, configured_catalog_ebid, [airbyte_message8_ebid])

    results = list(generator)

    assert len(results) == 1

    assert True
