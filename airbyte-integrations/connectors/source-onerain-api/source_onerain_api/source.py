#
# Copyright (c) 2024 Airbyte, Inc., all rights reserved.
#


from abc import ABC
from datetime import datetime
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import requests
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.core import StreamData
from airbyte_cdk.sources.streams.http import HttpStream
from airbyte_cdk.sources.streams.http.requests_native_auth import TokenAuthenticator
import xmltodict
from airbyte_protocol.models import SyncMode

"""
TODO: Most comments in this class are instructive and should be deleted after the source is implemented.

This file provides a stubbed example of how to use the Airbyte CDK to develop both a source connector which supports full refresh or and an
incremental syncs from an HTTP API.

The various TODOs are both implementation hints and steps - fulfilling all the TODOs should be sufficient to implement one basic and one incremental
stream from a source. This pattern is the same one used by Airbyte internally to implement connectors.

The approach here is not authoritative, and devs are free to use their own judgement.

There are additional required TODOs in the files within the integration_tests folder and the spec.yaml file.
"""


# Basic full refresh stream
class OnerainApiStream(HttpStream, ABC):
    """
    TODO remove this comment

    This class represents a stream output by the connector.
    This is an abstract base class meant to contain all the common functionality at the API level e.g: the API base URL, pagination strategy,
    parsing responses etc..

    Each stream should extend this class (or another abstract subclass of it) to specify behavior unique to that stream.

    Typically for REST APIs each stream corresponds to a resource in the API. For example if the API
    contains the endpoints
        - GET v1/customers
        - GET v1/employees

    then you should have three classes:
    `class OnerainApiStream(HttpStream, ABC)` which is the current class
    `class Customers(OnerainApiStream)` contains behavior to pull data for customers using v1/customers
    `class Employees(OnerainApiStream)` contains behavior to pull data for employees using v1/employees

    If some streams implement incremental sync, it is typical to create another class
    `class IncrementalOnerainApiStream((OnerainApiStream), ABC)` then have concrete stream implementations extend it. An example
    is provided below.

    See the reference docs for the full list of configurable options.
    """

    # TODO: Fill in the url base. Required.
    url_base = "https://example-api.com/v1/"
    _system_key = "system_key"

    def __init__(self, config, **kw):
        super().__init__(**kw)
        self._system_key = config['system_key']
        self.url_base = config['url_base']

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        """
        TODO: Override this method to define a pagination strategy. If you will not be using pagination, no action is required - just return None.

        This method should return a Mapping (e.g: dict) containing whatever information required to make paginated requests. This dict is passed
        to most other methods in this class to help you form headers, request bodies, query params, etc..

        For example, if the API accepts a 'page' parameter to determine which page of the result to return, and a response from the API contains a
        'page' number, then this method should probably return a dict {'page': response.json()['page'] + 1} to increment the page count by 1.
        The request_params method should then read the input next_page_token and set the 'page' param to next_page_token['page'].

        :param response: the most recent response from the API
        :return If there is another page in the result, a mapping (e.g: dict) containing information needed to query the next page in the response.
                If there are no more pages in the result, return None.
        """
        return None

    def request_params(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        """
        TODO: Override this method to define any query parameters to be set. Remove this method if you don't need to define request params.
        Usually contains common params e.g. pagination size etc.
        """
        return {'system_key': self._system_key}

    # def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
    #     """
    #     TODO: Override this method to define how a response is parsed.
    #     :return an iterable containing each record in the response
    #     """
    #     yield {}
    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        print(response.url)
        doc = xmltodict.parse(response.text)
        try:
            general = doc['onerain']['response']['general']
        except KeyError:
            print(response.text)
            print('no general')
            return []

        if general and 'row' in general:
            for row in general['row']:
                yield row
        else:
            print('no data')
            print(response.url)
            print(response.text)
            return []

    # def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
    #     doc = xmltodict.parse(response.text)
    #     try:
    #         general = doc['onerain']['response']['general']
    #     except KeyError:
    #         print(response.text)
    #         print('no general')
    #         return []
    #
    #     for row in general['row']:
    #         yield row

    def path(
            self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """
        TODO: Override this method to define the path this stream corresponds to. E.g. if the url is https://example-api.com/v1/customers then this
        should return "customers". Required.
        """
        return "/OneRain/DataAPI"


class GetSiteMetaData(OnerainApiStream):
    """
    TODO: Change class name to match the table/data source this stream corresponds to.
    """

    # TODO: Fill in the primary key. Required. This is usually a unique field in the stream, like an ID or a timestamp.
    primary_key = "site_id"

    def request_params(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        params = super().request_params(stream_state, stream_slice, next_page_token)
        params['method'] = 'GetSiteMetaData'
        return params


class GetSensorMetaData(OnerainApiStream):
    primary_key = "sensor_id"

    def __init__(self, parent_stream: Stream, **kw: Any) -> None:
        super().__init__(**kw)
        self._parent_stream = parent_stream

    def request_params(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        params = super().request_params(stream_state, stream_slice, next_page_token)
        params['method'] = 'GetSensorMetaData'
        params['or_site_id'] = stream_slice['location']['or_site_id']
        return params

    def stream_slices(
            self, *, sync_mode: SyncMode, cursor_field: Optional[List[str]] = None, stream_state: Optional[Mapping[str, Any]] = None
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        """
        """
        for _slice in self._parent_stream.stream_slices(sync_mode=sync_mode, cursor_field=cursor_field, stream_state=stream_state):
            for parent_record in self._parent_stream.read_records(sync_mode=sync_mode, stream_slice=_slice):
                yield {'location': parent_record}


class GetSensorData(OnerainApiStream):
    primary_key = ""
    _start_ts = None

    def __init__(self, parent_stream: Stream,
                 sensor_stream: Stream, start: datetime = None, **kw: Any) -> None:
        super().__init__(**kw)
        self._parent_stream = parent_stream
        self._sensor_stream = sensor_stream

        if start:
            self._start_ts = start.timestamp()

    @property
    def cursor_field(self) -> str:
        return "data_time"
    # def read_records(
    #         self,
    #         sync_mode: SyncMode,
    #         cursor_field: Optional[List[str]] = None,
    #         stream_slice: Optional[Mapping[str, Any]] = None,
    #         stream_state: Optional[Mapping[str, Any]] = None,
    # ) -> Iterable[StreamData]:
    #     return []

    def request_params(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        params = super().request_params(stream_state, stream_slice, next_page_token)
        params['method'] = 'GetSensorData'
        params['or_site_id'] = stream_slice['location']['or_site_id']
        params['data_start'] = datetime.fromtimestamp(stream_slice['start']).strftime('%Y-%m-%d %H:%M:%S')
        params['data_end'] = datetime.fromtimestamp(stream_slice['end']).strftime('%Y-%m-%d %H:%M:%S')
        params['or_sensor_id'] = stream_slice['sensor']['or_sensor_id']
        return params

    def stream_slices(
            self, *, sync_mode: SyncMode, cursor_field: Optional[List[str]] = None, stream_state: Optional[Mapping[str, Any]] = None
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        """
        Slices the stream based on locationId
        """
        now_ts = datetime.now().timestamp() - (60 * 60 * 24 * 2)

        for k, parent_record in enumerate(self._parent_stream.read_records(sync_mode=sync_mode)):

            start_ts = None
            if stream_state:
                state = stream_state.get(parent_record['or_site_id'], {})
                start_ts = state.get(self.cursor_field, self._start_ts) if stream_state else self._start_ts

            print("or_site_id", parent_record['or_site_id'], start_ts, stream_state)
            if start_ts is None:
                start_ts = now_ts - (60 * 60 * 24 * 2)

            for i, (start, end) in enumerate(self.chunk_dates(start_ts, now_ts)):
                for m, sensor_record in enumerate(self._sensor_stream.read_records(sync_mode=sync_mode,
                                                                                   stream_slice={'location': parent_record})):


                    # 94 = (2) Gauge Height, (3) Gauge Height, Elevation - Water Level, Gauge Height
                    if sensor_record['sensor_class'] in ('94', ):
                        yield {'location': parent_record, 'sensor': sensor_record, 'start': start, 'end': end}

    def chunk_dates(self, start_date_ts: int, end_date_ts: int) -> Iterable[Tuple[int, int]]:
        _SLICE_RANGE = 30  # days
        step = int(_SLICE_RANGE * 24 * 60 * 60)

        # after_ts = end_date_ts
        # while after_ts > start_date_ts:
        #     # before_ts = after_ts
        #     before_ts = max(start_date_ts, after_ts - step)
        #     yield before_ts, after_ts
        #     after_ts = before_ts - 1

        after_ts = start_date_ts
        while after_ts < end_date_ts:
            before_ts = min(end_date_ts, after_ts + step)
            yield after_ts, before_ts
            after_ts = before_ts + 1

    def get_updated_state(self, current_stream_state: MutableMapping[str, Any], latest_record: Mapping[str, Any]) -> Mapping[str, Any]:
        key = latest_record['or_site_id']
        state = current_stream_state.get(key, {})
        dt = latest_record.get(self.cursor_field)
        if dt is not None:
            dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S').timestamp()
        else:
            dt = 0

        state_value = max(state.get(self.cursor_field, 0), dt)
        current_stream_state[key] = {self.cursor_field: state_value}
        return current_stream_state

        # return {latest_record['location']['or_site_id']: latest_record[self.cursor_field]}
    #     state_value = max(current_stream_state.get(self.cursor_field, 0), latest_record.get(self.cursor_field, 0))
    #     print('updafa', state_value, current_stream_state, latest_record)
    #     return {self.cursor_field: state_value}

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        print(response.url)
        doc = xmltodict.parse(response.text)
        try:
            general = doc['onerain']['response']['general']
        except KeyError:
            print(response.text)
            print('no general')
            return []

        if general and 'row' in general:
            for row in general['row']:
                yield row
        else:
            print('no data')
            print(response.url)
            print(response.text)
            return []


class BackloadGetSensorData(GetSensorData):
    pass

# # Basic incremental stream
# class IncrementalOnerainApiStream(OnerainApiStream, ABC):
#     """
#     TODO fill in details of this class to implement functionality related to incremental syncs for your connector.
#          if you do not need to implement incremental sync for any streams, remove this class.
#     """
#
#     # TODO: Fill in to checkpoint stream reads after N records. This prevents re-reading of data if the stream fails for any reason.
#     state_checkpoint_interval = None
#
#     @property
#     def cursor_field(self) -> str:
#         """
#         TODO
#         Override to return the cursor field used by this stream e.g: an API entity might always use created_at as the cursor field. This is
#         usually id or date based. This field's presence tells the framework this in an incremental stream. Required for incremental.
#
#         :return str: The name of the cursor field.
#         """
#         return []
#
#     def get_updated_state(self, current_stream_state: MutableMapping[str, Any], latest_record: Mapping[str, Any]) -> Mapping[str, Any]:
#         """
#         Override to determine the latest state after reading the latest record. This typically compared the cursor_field from the latest record and
#         the current state and picks the 'most' recent cursor. This is how a stream's state is determined. Required for incremental.
#         """
#         return {}
#
#
# class Employees(IncrementalOnerainApiStream):
#     """
#     TODO: Change class name to match the table/data source this stream corresponds to.
#     """
#
#     # TODO: Fill in the cursor_field. Required.
#     cursor_field = "start_date"
#
#     # TODO: Fill in the primary key. Required. This is usually a unique field in the stream, like an ID or a timestamp.
#     primary_key = "employee_id"
#
#     def path(self, **kwargs) -> str:
#         """
#         TODO: Override this method to define the path this stream corresponds to. E.g. if the url is https://example-api.com/v1/employees then this should
#         return "single". Required.
#         """
#         return "employees"
#
#     def stream_slices(self, stream_state: Mapping[str, Any] = None, **kwargs) -> Iterable[Optional[Mapping[str, any]]]:
#         """
#         TODO: Optionally override this method to define this stream's slices. If slicing is not needed, delete this method.
#
#         Slices control when state is saved. Specifically, state is saved after a slice has been fully read.
#         This is useful if the API offers reads by groups or filters, and can be paired with the state object to make reads efficient. See the "concepts"
#         section of the docs for more information.
#
#         The function is called before reading any records in a stream. It returns an Iterable of dicts, each containing the
#         necessary data to craft a request for a slice. The stream state is usually referenced to determine what slices need to be created.
#         This means that data in a slice is usually closely related to a stream's cursor_field and stream_state.
#
#         An HTTP request is made for each returned slice. The same slice can be accessed in the path, request_params and request_header functions to help
#         craft that specific request.
#
#         For example, if https://example-api.com/v1/employees offers a date query params that returns data for that particular day, one way to implement
#         this would be to consult the stream state object for the last synced date, then return a slice containing each date from the last synced date
#         till now. The request_params function would then grab the date from the stream_slice and make it part of the request by injecting it into
#         the date query param.
#         """
#         raise NotImplementedError("Implement stream slices or delete this method!")
#

# Source
class SourceOnerainApi(AbstractSource):
    def check_connection(self, logger, config) -> Tuple[bool, any]:
        """
        TODO: Implement a connection check to validate that the user-provided config can be used to connect to the underlying API

        See https://github.com/airbytehq/airbyte/blob/master/airbyte-integrations/connectors/source-stripe/source_stripe/source.py#L232
        for an example.

        :param config:  the user-input config object conforming to the connector's spec.yaml
        :param logger:  logger object
        :return Tuple[bool, any]: (True, None) if the input config can be used to connect to the API successfully, (False, error) otherwise.
        """
        url = f'{config["url_base"]}/OneRain/DataAPI?method=GetTime&timezone=MDT'
        try:
            resp = requests.get(url)
            doc = xmltodict.parse(resp.text)
            t = doc['onerain']['response']['general']['row']['time']
        except Exception as e:
            return False, f"Unable to connect to API at {url}- {str(e)}"

        return True, None

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        """
        TODO: Replace the streams below with your own streams.

        :param config: A Mapping of the user input configuration as defined in the connector spec.
        """
        # TODO remove the authenticator if not required.
        # auth = TokenAuthenticator(token="api_key")  # Oauth2Authenticator is also available if you need oauth support
        # return [Customers(authenticator=auth), Employees(authenticator=auth)]
        start = datetime.strptime('2020', '%Y')
        # start = datetime.now()
        site_stream = GetSiteMetaData(config=config)
        sensor_stream = GetSensorMetaData(config=config, parent_stream=site_stream)
        backload_stream = BackloadGetSensorData(config=config, parent_stream=site_stream, sensor_stream=sensor_stream,
                                                start=start)
        data_stream = GetSensorData(config=config, parent_stream=site_stream, sensor_stream=sensor_stream)

        return [site_stream, sensor_stream, backload_stream, data_stream]
