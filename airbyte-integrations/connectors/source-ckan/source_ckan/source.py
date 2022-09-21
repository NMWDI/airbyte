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
TODO: Most comments in this class are instructive and should be deleted after the source is implemented.

This file provides a stubbed example of how to use the Airbyte CDK to develop both a source connector which supports full refresh or and an
incremental syncs from an HTTP API.

The various TODOs are both implementation hints and steps - fulfilling all the TODOs should be sufficient to implement one basic and one incremental
stream from a source. This pattern is the same one used by Airbyte internally to implement connectors.

The approach here is not authoritative, and devs are free to use their own judgement.

There are additional required TODOs in the files within the integration_tests folder and the spec.json file.
"""


# Basic full refresh stream
class CkanStream(HttpStream, ABC):
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
    `class CkanStream(HttpStream, ABC)` which is the current class
    `class Customers(CkanStream)` contains behavior to pull data for customers using v1/customers
    `class Employees(CkanStream)` contains behavior to pull data for employees using v1/employees

    If some streams implement incremental sync, it is typical to create another class
    `class IncrementalCkanStream((CkanStream), ABC)` then have concrete stream implementations extend it. An example
    is provided below.

    See the reference docs for the full list of configurable options.
    """

    # TODO: Fill in the url base. Required.
    url_base = "https://catalog.newmexicowaterdata.org/api/3/"

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


class CollectionSchema(CkanStream):
    """
    Gets the schema of the current collection - see: https://developers.webflow.com/#get-collection-with-full-schema, and
    then converts that schema to a json-schema.org-compatible schema that uses supported Airbyte types.
    More info about Webflow schema: https://developers.webflow.com/#get-collection-with-full-schema
    Airbyte data types: https://docs.airbyte.com/understanding-airbyte/supported-data-types/
    """

    # Required.
    primary_key = "id"

    def __init__(self, resource_id,  *args, **kw):
        super(CollectionSchema, self).__init__(*args, **kw)

        self.resource_id = resource_id


    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """
        Path to given resource_id
        """

        return f"action/datastore_search?resource_id={self.resource_id}"


    def parse_response(self,
        response: requests.Response,
        stream_state: Mapping[str, Any],
        **kwargs) -> Iterable[Mapping]:
        """
        Parses the Data Dictionary fields from the given resource_id
        """

        r = response.json()

        yield from r['result']['fields']


class Csv(CkanStream):
    """
    Gets specified CSV from CKAN
    """

    # Required.
    primary_key = "id"

    def __init__(self, resource_id,  *args, **kw):
        super(Csv, self).__init__(*args, **kw)

        self.resource_id = resource_id


    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """
        Path to given resource_id
        """

        return f"action/datastore_search?resource_id={self.resource_id}"


    def get_json_schema(self):
        """
        Dynamically generate schema based upon the Data Dictionary for the given resource_id
        """

        schema = super().get_json_schema()

        resource_id = self.resource_id

        schema_stream = CollectionSchema(resource_id=resource_id)

        schema_records = schema_stream.read_records(sync_mode="full_refresh")

        type_conversion_dict = {
            "int": "integer",
            "numeric": "number",
            "text": "string"
        }

        for field in schema_records:

            property_name = field["id"]
            
            field_type = field["type"]

            schema_type = type_conversion_dict[field_type]
                       
            schema['properties'][property_name] = {"type": schema_type} 

        return schema


    def parse_response(self,
        response: requests.Response,
        stream_state: Mapping[str, Any],
        **kwargs) -> Iterable[Mapping]:
        """
        Parses the response with the CSV from the given resource_id
        """

        r = response.json()

        yield from r['result']['records']


# Source
class SourceCkan(AbstractSource):

    def check_connection(self, logger, config) -> Tuple[bool, any]:
        """
        Implements a connection check to validate that the user-provided config can be used to connect to the underlying API
        :param config:  the user-input config object conforming to the connector's spec.json
        :param logger:  logger object
        :return Tuple[bool, any]: (True, None) if the input config can be used to connect to the API successfully, (False, error) otherwise.
        """
        url_base = "https://catalog.newmexicowaterdata.org/api/3/"

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

        return [Csv(config['resource_id'])]


def get_resp(logger, url):
    resp = requests.get(url)
    logger.debug(f'url={url}, resp={resp}')
    if resp.status_code == 200:
        return resp

