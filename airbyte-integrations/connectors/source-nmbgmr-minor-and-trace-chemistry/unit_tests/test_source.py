#
# Copyright (c) 2021 Airbyte, Inc., all rights reserved.
#

from unittest.mock import MagicMock

from source_nmbgmr_minor_and_trace_chemistry.source import SourceNmbgmrMinorAndTraceChemistry


def test_check_connection(mocker):
    source = SourceNmbgmrMinorAndTraceChemistry()
    logger_mock, config_mock = MagicMock(), MagicMock()
    assert source.check_connection(logger_mock, config_mock) == (True, None)


def test_streams(mocker):
    source = SourceNmbgmrMinorAndTraceChemistry()
    config_mock = MagicMock()
    streams = source.streams(config_mock)
    # TODO: replace this with your streams number
    expected_streams_number = 2
    assert len(streams) == expected_streams_number
