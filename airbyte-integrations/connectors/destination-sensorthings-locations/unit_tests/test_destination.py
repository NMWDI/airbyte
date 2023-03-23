from unittest.mock import MagicMock

import pytest
from pytest import fixture
from datetime import datetime
from typing import Any, Dict
import random
import string

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

from destination_sensorthings_locations import DestinationSensorthingsLocations

rand_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
RAND_STRING_WITH_NAME_MSG3 = "".join(["LEWIS N DIVERSION_", rand_string])


@pytest.fixture
def config_isc():
    return {"config": {"destination_path": "http://34.106.60.230:8080/FROST-Server/v1.1", "name": "ISC Seven Rivers Monitoring Points", "description": "ISC Seven Rivers Monitoring Point Locations", "agency": "ISC_SEVEN_RIVERS", "source_api": "https://nmisc-wf.gladata.com/api/", "observation_category": "levels" }}


@pytest.fixture
def config_pecos():
    return {"config": {"destination_path": "http://34.106.60.230:8080/FROST-Server/v1.1", "name": "Pecos Valley Locations", "description": "Pecos Valley Well Locations", "agency": "PVACD", "observation_category": "levels" }}


@pytest.fixture
def config_nmbgmr():
    return {"config": {"destination_path": "http://34.106.60.230:8080/FROST-Server/v1.1", "name": "NMBGMR Wells", "description": "NMBGMR Wells", "agency": "NMBGMR", "observation_category": "levels" }}


@pytest.fixture
def config_ebid():
    return {"config": {"destination_path": "http://34.106.60.230:8080/FROST-Server/v1.1", "name": "EBID Locations", "description": "EBID Locations", "agency": "EBID", "observation_category": "levels" }}


@pytest.fixture
def airbyte_message1():

    rand_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    rand_string_with_name = "".join(["Yellow_", rand_string])

    return AirbyteMessage(
        type=Type.RECORD,
        record=AirbyteRecordMessage(
            stream="isc_seven_rivers_monitoring_points", data={"id": "180", "name": rand_string_with_name, "type": "Shallow GW", "comments": "", "latitude": "32.61627", "longitude": -104.38256, "groundSurfaceElevationFeet": 3289.0, "_airbyte_ab_id": "99407136-3e9f-421d-9894-86327cd99d87"}, emitted_at=int(datetime.now().timestamp()) * 1000
        ),
    )


@pytest.fixture
def airbyte_message2():
    
    rand_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    rand_string_with_name = "".join(["BOR North Well_", rand_string])

    return AirbyteMessage(
        type=Type.RECORD,
        record=AirbyteRecordMessage(
            stream="isc_seven_rivers_monitoring_points", data={"id": "148", "name": rand_string_with_name, "type": "Unknown", "comments": "", "latitude": "32.6", "longitude": -104.4, "groundSurfaceElevationFeet": None, "_airbyte_ab_id": "87aa5569996e4cad4da19af6c5a41ec6"}, emitted_at=int(datetime.now().timestamp()) * 1000
        ),
    )


@pytest.fixture
def airbyte_message3():
    return AirbyteMessage(
        type=Type.RECORD,
        record=AirbyteRecordMessage(
            stream="isc_seven_rivers_monitoring_points", data={"id": "228", "name": RAND_STRING_WITH_NAME_MSG3, "type": "Unknown", "comments": "", "latitude": "32.6", "longitude": -104.4, "groundSurfaceElevationFeet": None, "_airbyte_ab_id": "103f9bbb-c847-4f13-b87a-16a88ef77afc"}, emitted_at=int(datetime.now().timestamp()) * 1000
        ),
    )


@pytest.fixture
def airbyte_message4_for_patch():
    return AirbyteMessage(
        type=Type.RECORD,
        record=AirbyteRecordMessage(
            stream="isc_seven_rivers_monitoring_points", data={"id": "228", "name": RAND_STRING_WITH_NAME_MSG3, "type": "Unknown", "comments": "Updated groundSurfaceElevationFeet", "latitude": "32.6", "longitude": -104.4, "groundSurfaceElevationFeet": 352.8, "_airbyte_ab_id": "103f9bbb-c847-4f13-b87a-16a88ef77afc"}, emitted_at=int(datetime.now().timestamp()) * 1000
        ),
    )


# The following test message should throw an error as intended because the NMWDI development 
# FROST-Server currently has multiple locations with the name "Yellow".
@pytest.fixture
def airbyte_message5_error_for_mult_loc_with_same_name():

    return AirbyteMessage(
        type=Type.RECORD,
        record=AirbyteRecordMessage(
            stream="isc_seven_rivers_monitoring_points", data={"id": "180", "name": "Yellow", "type": "Shallow GW", "comments": "", "latitude": "32.61627", "longitude": -104.38256, "groundSurfaceElevationFeet": 3289.0, "_airbyte_ab_id": "99407136-3e9f-421d-9894-86327cd99d87"}, emitted_at=int(datetime.now().timestamp()) * 1000
        ),
    )


@pytest.fixture
def airbyte_message6_pecos():
    rand_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    rand_string_with_name = "".join(["Transwestern Level_", rand_string])

    return AirbyteMessage(
        type=Type.RECORD,
        record=AirbyteRecordMessage(
            stream="pecos_locations", data={"id": "228", "name": rand_string_with_name, "type": "Unknown", "comments": "", "latitude": "32.6", "longitude": -104.4, "use": "active_monitoring", "aquifer": "Permian Aquifer System", "aquifer_group": "Permian Aquifer System", "model_formation": "SanAndreas", "_airbyte_ab_id": "103f9bbb-c847-4f13-b87a-16a88ef77afc"}, emitted_at=int(datetime.now().timestamp()) * 1000
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

    #overwrite_stream = ConfiguredAirbyteStream(
    #    stream=AirbyteStream(name="overwrite_stream", json_schema=stream_schema, supported_sync_modes=[SyncMode.incremental]),
    #    sync_mode=SyncMode.incremental,
    #    destination_sync_mode=DestinationSyncMode.overwrite,
    #)

    #return ConfiguredAirbyteCatalog(streams=[append_stream, overwrite_stream])
    
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


def test_check_connection(config_isc):

    destination = DestinationSensorthingsLocations()

    logger_mock = MagicMock()

    status = destination.check(logger_mock, **config_isc)

    assert status.status == Status.SUCCEEDED

    
def test_write_isc(
    config_isc,
    request,
    configured_catalog_isc: ConfiguredAirbyteCatalog,
    airbyte_message1: AirbyteMessage,
    airbyte_message2: AirbyteMessage,
    airbyte_message3: AirbyteMessage,
    airbyte_message4_for_patch: AirbyteMessage,
    airbyte_message5_error_for_mult_loc_with_same_name: AirbyteMessage,
    airbyte_message6_pecos: AirbyteMessage,
):

    config_unpacked = config_isc['config']

    destination = DestinationSensorthingsLocations()

    generator = destination.write(config_unpacked, configured_catalog_isc, [airbyte_message1, airbyte_message2, airbyte_message3, airbyte_message4_for_patch, airbyte_message5_error_for_mult_loc_with_same_name])

    assert True


def test_write_pecos(
    config_pecos,
    request,
    configured_catalog_pecos: ConfiguredAirbyteCatalog,
    airbyte_message6_pecos: AirbyteMessage,
):

    config_unpacked = config_pecos['config']

    destination = DestinationSensorthingsLocations()

    generator = destination.write(config_unpacked, configured_catalog_pecos, [airbyte_message6_pecos])

    assert True


