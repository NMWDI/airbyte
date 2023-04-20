#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


from typing import Any, Iterable, Mapping

from airbyte_cdk import AirbyteLogger
from airbyte_cdk.destinations import Destination
from airbyte_cdk.models import AirbyteConnectionStatus, AirbyteMessage, ConfiguredAirbyteCatalog, Status


import frost_sta_client as fsc


#from google.cloud import bigquery
#from google.oauth2 import service_account
import os
import requests
from datetime import datetime
import copy
import logging
#import pyproj

logger = logging.getLogger("airbyte")

PROJECTIONS = {}





class DestinationSensorthingsObservations(Destination):
    def write(
        self, config: Mapping[str, Any], configured_catalog: ConfiguredAirbyteCatalog, input_messages: Iterable[AirbyteMessage]
    ) -> Iterable[AirbyteMessage]:

        """
        TODO
        Reads the input stream of messages, config, and catalog to write data to the destination.

        This method returns an iterable (typically a generator of AirbyteMessages via yield) containing state messages received
        in the input message stream. Outputting a state message means that every AirbyteRecordMessage which came before it has been
        successfully persisted to the destination. This is used to ensure fault tolerance in the case that a sync fails before fully completing,
        then the source is given the last state message output from this method as the starting point of the next sync.

        :param config: dict of JSON configuration matching the configuration declared in spec.json
        :param configured_catalog: The Configured Catalog describing the schema of the data being received and how it should be persisted in the
                                    destination
        :param input_messages: The stream of input messages received from the source
        :return: Iterable of AirbyteStateMessages wrapped in AirbyteMessage structs
        """


        self._config = config
        self._service = fsc.SensorThingsService(config["destination_path"])
        self._validation_service = "https://nmwdistvalidation-dot-waterdatainitiative-271000.appspot.com/"

        for message in input_messages:

            logger.info(f'Message: {message}')
            logger.info(f'========================')

            if message.type == Type.RECORD:

                logger.info(f'RECORD Message: {message}')
                logger.info(f'========================')

                data = message.record.data

                stream = message.record.stream

                #location = self._make_location(data)

                #self._validate_location(location)

                #self._make_thing(location, data)
                
                #self._validate_thing(location)


            elif message.type == Type.STATE:
                logger.info(f'STATE Message: {message}')
                logger.info(f'========================')

                yield message


            else:
                logger.info(f'Not Record Message: {message}')
                logger.info(f'========================')










    def check(self, logger: AirbyteLogger, config: Mapping[str, Any]) -> AirbyteConnectionStatus:
        """
        Tests if the input configuration can be used to successfully connect to the destination with the needed permissions
            e.g: if a provided API token or password can be used to connect and write to the destination.

        :param logger: Logging object to display debug/info/error to the logs
            (logs will not be accessible via airbyte UI if they are not passed to this logger)
        :param config: Json object containing the configuration of this destination, content of this json is as specified in
        the properties of the spec.json file

        :return: AirbyteConnectionStatus indicating a Success or Failure
        """
        try:
            x = requests.request("CONNECT", config["destination_path"])


            return AirbyteConnectionStatus(status=Status.SUCCEEDED)
        except Exception as e:
            return AirbyteConnectionStatus(status=Status.FAILED, message=f"An exception occurred: {repr(e)}")
