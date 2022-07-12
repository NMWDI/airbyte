#
# Copyright (c) 2021 Airbyte, Inc., all rights reserved.
#

from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import requests
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from airbyte_cdk.sources.streams.http.auth import TokenAuthenticator

"""
Source Connector for NMBGMR Minor and Trace Chemeistry
"""

# Basic full refresh stream
class NmbgmrMinorAndTraceChemistryStream(HttpStream, ABC):
    """
    This class represents a stream output by the connector.
    This is an abstract base class meant to contain all the common functionality at the API level e.g: the API base URL, pagination strategy,
    parsing responses etc..

    Each stream should extend this class (or another abstract subclass of it) to specify behavior unique to that stream.

    Typically for REST APIs each stream corresponds to a resource in the API. For example if the API
    contains the endpoints
        - GET v1/customers
        - GET v1/employees

    then you should have three classes:
    `class NmbgmrMinorAndTraceChemistryStream(HttpStream, ABC)` which is the current class
    `class Customers(NmbgmrMinorAndTraceChemistryStream)` contains behavior to pull data for customers using v1/customers
    `class Employees(NmbgmrMinorAndTraceChemistryStream)` contains behavior to pull data for employees using v1/employees

    If some streams implement incremental sync, it is typical to create another class
    `class IncrementalNmbgmrMinorAndTraceChemistryStream((NmbgmrMinorAndTraceChemistryStream), ABC)` then have concrete stream implementations extend it. An example
    is provided below.

    See the reference docs for the full list of configurable options.
    """

    # TODO: Fill in the url base. Required.
    url_base = "https://maps.nmt.edu/maps/data/waterlevels/minor_and_trace_chemistry"
    
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
        return {}

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        TODO: Override this method to define how a response is parsed.
        :return an iterable containing each record in the response
        """
        yield {}


class Samples(NmbgmrMinorAndTraceChemistryStream):
    """
    Gets Samples from NMBGMR Minor and Trace Chemistry API
    """

    # Required.
    primary_key = "id"

    def __init__(self, *args, **kw):
        super(Samples, self).__init__(*args, **kw)


    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """
        Path to first or another specific page of the NMBGMR Minor and Trace Chemistry API.
        """

        if not next_page_token:
            return ""

        else:
            return next_page_token


    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        """
        Parses the nextLink URL from the JSON response.
        """

        try:
            next_page = response.json()["nextLink"]

            return next_page

        except:
            pass


    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        Parses the JSON response for the records which are contained within a list corresponding
        to the "value" key.  
        """

        yield from response.json()["value"]


# Source
class SourceNmbgmrMinorAndTraceChemistry(AbstractSource):
    def check_connection(self, logger, config) -> Tuple[bool, any]:
        """
        Implements a connection check to validate that the user-provided config can be used to connect to the underlying API

        :param config:  the user-input config object conforming to the connector's spec.json
        :param logger:  logger object
        :return Tuple[bool, any]: (True, None) if the input config can be used to connect to the API successfully, (False, error) otherwise.
        """
        url_base = "https://maps.nmt.edu/maps/data/waterlevels/minor_and_trace_chemistry"

        try:
            resp = get_resp(logger, url_base)
            if not resp.status_code == 200:
                raise Exception
            return True, None
        except Exception as e:
            return False, e


    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        """
        :param config: A Mapping of the user input configuration as defined in the connector spec.
        """
        
        return [Samples()]


def get_resp(logger, url):
    resp = requests.get(url)
    logger.debug(f'url={url}, resp={resp}')
    if resp.status_code == 200:
        return resp
