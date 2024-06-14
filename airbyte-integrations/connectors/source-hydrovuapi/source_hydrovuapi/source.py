# ===============================================================================
# Copyright 2024 ross
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ===============================================================================
from abc import ABC
from datetime import datetime
from typing import List, Any, Mapping, Optional, Iterable, Tuple, MutableMapping

import requests
from airbyte_cdk.sources.streams.core import StreamData
from airbyte_cdk.sources.streams.http.requests_native_auth import Oauth2Authenticator
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from airbyte_cdk.sources.abstract_source import AbstractSource
from airbyte_protocol.models import SyncMode
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session


class HydrovuapiStream(HttpStream, ABC):
    url_base = "https://www.hydrovu.com/public-api/v1/"

    def request_headers(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        """
        The X-ISI-Start-Page is a header that is required if accessing any page beyond the fist
        page from the given path to the readings for a given location. If accessing the first page, then the
        header can be empty.
        """
        return {"X-ISI-Start-Page": next_page_token or '', 'Accept': 'application/json'}

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        return response.headers.get('x-isi-next-page', '')


class Locations(HydrovuapiStream):
    primary_key = "id"

    def parse_response(
            self,
            response: requests.Response,
            *,
            stream_state: Mapping[str, Any],
            stream_slice: Optional[Mapping[str, Any]] = None,
            next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> Iterable[Mapping[str, Any]]:
        def format_record(r):
            gps = r['gps']
            del r['gps']
            r['latitude'] = gps['latitude']
            r['longitude'] = gps['longitude']
            return r

        yield from (format_record(r) for r in response.json())

    def path(self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None,
             next_page_token: Mapping[str, Any] = None) -> str:
        """
        End of URL path to locations list from API
        """
        return "locations/list"


class Readings(HydrovuapiStream):
    primary_key = "id"
    cursor_field = "timestamp"

    def __init__(self, start, parent_stream: Stream, **kwargs: Any) -> None:
        self._parent_stream = parent_stream
        self._start_ts = start
        super().__init__(**kwargs)

    def request_params(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None,
            next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        """
        The startTime parameter is required if wanting to pull data starting at any other time
        than the first Epoch timestamp available from the API. This is set up to stored state as the
        last timestamp read for each location. Therefore, when Airbyte executes a new run with these
        timestamps stored in state, the timestamps will be read in from state and set as the startTime
        parameter to read data from that timestamp until the most recently available timestamp.
        """

        # Check to see if self.location_latest_timestamps is an empty dictionary.
        # It is only empty on the first overall call of a given run to request_params.
        # If this is the first time Airbyte is run, and no state is stored, then these
        # will remain as empty dictionaries.
        # if not bool(self.location_latest_timestamps):
        #
        #     # This dictionary will be continously be updated throughout a run
        #     self.location_latest_timestamps = stream_state
        #
        #     # Dictionary copy makes a shallow copy of the dictionary.
        #     # This dictionary will remain static throughout a run and only contain the
        #     # state that is read in at the beginning. If there is no state available to
        #     # be read in, then this dictionary will remain empty for the run.
        #     self.state_location_timestamps = self.location_latest_timestamps.copy()

        # If there are timestamps from state for a given location, then set that to startTime.
        # Otherwise, params will be empty.
        # try:
        #     params = {'startTime': self.state_location_timestamps[str(self.next_location_page)]}
        # except:
        params = {
            'startTime': int(stream_slice['start']),
            'endTime': int(stream_slice['end'])
        }

        return params

    def read_records(
            self,
            sync_mode: SyncMode,
            cursor_field: Optional[List[str]] = None,
            stream_slice: Optional[Mapping[str, Any]] = None,
            stream_state: Optional[Mapping[str, Any]] = None,
    ) -> Iterable[StreamData]:

        try:
            yield from super().read_records(sync_mode=sync_mode, cursor_field=cursor_field, stream_slice=stream_slice,
                                            stream_state=stream_state)
        except Exception as e:
            print(e)
            yield from []

    def parse_response(
            self,
            response: requests.Response,
            *,
            stream_state: Mapping[str, Any],
            stream_slice: Optional[Mapping[str, Any]] = None,
            next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> Iterable[Mapping[str, Any]]:

        r = response.json()

        locationId = r['locationId']
        parameters = r['parameters']

        for param in parameters:
            parameterId = param['parameterId']
            unitId = param['unitId']
            customParameter = param['customParameter']
            readings = param['readings']
            if parameterId != '4':
                continue

            for reading in readings:
                timestamp = reading['timestamp']

                time_utc_iso = datetime.utcfromtimestamp(timestamp).isoformat()
                value = reading['value']
                flat_reading = {'locationId': locationId, 'parameterId': parameterId, 'unitId': unitId,
                                'customParameter': customParameter, 'timestamp': timestamp, 'time_utc_iso': time_utc_iso,
                                'value': value, 'id': f"{locationId}_{parameterId}_{unitId}_{timestamp}"}
                yield flat_reading

    def path(self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None,
             next_page_token: Mapping[str, Any] = None) -> str:
        """
        End of URL path to readings list from API
        """
        location_id = stream_slice['location']['id']
        return f"locations/{location_id}/data"

    def stream_slices(
            self, *, sync_mode: SyncMode, cursor_field: Optional[List[str]] = None, stream_state: Optional[Mapping[str, Any]] = None
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        """
        Slices the stream based on locationId
        """
        start_ts = stream_state.get(self.cursor_field, self._start_ts) if stream_state else self._start_ts
        now_ts = datetime.now().timestamp()

        for start, end in self.chunk_dates(start_ts, now_ts):
            for _slice in self._parent_stream.stream_slices(sync_mode=sync_mode, cursor_field=cursor_field, stream_state=stream_state):
                for parent_record in self._parent_stream.read_records(sync_mode=sync_mode, stream_slice=_slice):
                    yield {'location': parent_record, 'start': start, 'end': end}

    def chunk_dates(self, start_date_ts: int, end_date_ts: int) -> Iterable[Tuple[int, int]]:
        _SLICE_RANGE = 365
        step = int(_SLICE_RANGE * 24 * 60 * 60)
        after_ts = start_date_ts
        while after_ts < end_date_ts:
            before_ts = min(end_date_ts, after_ts + step)
            yield after_ts, before_ts
            after_ts = before_ts + 1

    def get_updated_state(self, current_stream_state: MutableMapping[str, Any], latest_record: Mapping[str, Any]) -> Mapping[str, Any]:
        state_value = max(current_stream_state.get(self.cursor_field, 0), latest_record.get(self.cursor_field, 0))
        return {self.cursor_field: state_value}


class myOauth2Authenticator(Oauth2Authenticator):
    def refresh_access_token(self) -> Tuple[str, int]:
        """
        Returns a tuple of (access_token, token_lifespan_in_seconds)
        """
        client = BackendApplicationClient(client_id=self._client_id)
        oauth = OAuth2Session(client=client)
        response_json = oauth.fetch_token(token_url=self._token_refresh_endpoint,
                                          client_id=self._client_id,
                                          client_secret=self._client_secret)
        return response_json['access_token'], response_json['expires_in']


class SourceHydrovuapi(AbstractSource):
    def __init__(self):
        super().__init__()

    def get_auth(self, config):
        return myOauth2Authenticator(
            token_refresh_endpoint='https://hydrovu.com/public-api/oauth/token',
            client_id=config['client_id'],
            client_secret=config['client_secret'],
            refresh_token=""
        )

    def check_connection(self, logger, config) -> bool:
        try:
            auth = self.get_auth(config)
            client = BackendApplicationClient(client_id=auth._client_id)
            oauth = OAuth2Session(client=client)
            response = oauth.fetch_token(token_url=auth._token_refresh_endpoint,
                                         client_id=auth._client_id,
                                         client_secret=auth._client_secret)
        except Exception as e:
            logger.error(f"Error checking connection {e}")
            return False, e
        return True, None

    def streams(self, config) -> List[Stream]:
        locations = Locations(authenticator=self.get_auth(config))
        start = datetime.strptime('2020', '%Y').timestamp()
        return [locations, Readings(parent_stream=locations,
                                    start=start, authenticator=self.get_auth(config))]

# ============= EOF =============================================
