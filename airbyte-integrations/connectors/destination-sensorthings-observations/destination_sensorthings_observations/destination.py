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


# Credentials to a GCP BigQuery table
#CREDENTIALS = service_account.Credentials.from_service_account_file("")


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
            
        logger.info(f'========================')

        for message in input_messages:

            logger.info(f'Message: {message}')
            logger.info(f'========================')

            if message.type == Type.RECORD:

                logger.info(f'RECORD Message: {message}')
                logger.info(f'========================')

                data = message.record.data

                stream = message.record.stream

                datastream = self._make_datastream(data)

                self._validate_datastream(datastream)

                self._make_observation(datastream, data)
                
                self._validate_observation(datastream)


            elif message.type == Type.STATE:
                logger.info(f'STATE Message: {message}')
                logger.info(f'========================')

                yield message


            else:
                logger.info(f'Not Record Message: {message}')
                logger.info(f'========================')



    def _make_datastream(self, data):
        # does this datastream exist

        # Get source_id from record
        source_id= self._get_source_id_from_record(data)

        # Other Opption
        # Get location name from BQ table corresponding to the source_id
        # Does the location with that name exist?
        # Does the datastream associated with that location exist?


        # Need to add source_id to loc connector for either location or thing for each agency
        # Below
        # Query ST locations for source_id. Can add agency to query to narrow.
        # If location or thing exists, then check if the datastream exists
        # If the location or thing does not exist, then output an error

        #Add list or dict for datastreams already queried??


        # TODO: Add agency to query
        # Query SensorThings Locations for source_id
        locations = self._service.locations().query().filter(f"source_id eq '{source_id}'").list()

        # Check length of list and log error if more than one location with the same source_id
        if len(locations.entities) > 1:
            #Log error
            logger.error(f"Multiple locations with the source_id [{source_id}] exist")

        elif len(locations.entities) < 1:
            #Log error
            logger.error(f"A location with the source_id [{source_id}] does not exist")

        # Else if one location with the source_id exists, check if datastream exists
        else:
            for location in locations:
                iotid = location.id
               
                datastream_url = self._query_things_for_datastream_url(iotid)

                # Check if datastream exists
                if (self._query_for_datastream_existence(datastream_url)):
                    # Add observations
                    pass
                else:
                    # Create Datastream

                    unit_of_measurement_dict = {
                        "name": "Foot",
                        "symbol": "ft",
                        "definition": "http://www.qudt.org/vocab/unit/FT"
                    }


                    #TODO: Add phenomenon_time and result_time 
                    # Add empty dict for properties??
                    datastream = fsc.Datastream(name="Groundwater Levels",
                                            description='Measurement of groundwater depth in a water well, as measured below ground surface',
                                            observation_type="http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Measurement"
                                            observed_area=location.location
                                            properties={"topic", "Water Quantity"}
                                            unit_of_measurement=unit_of_measurement_dict)
                    self._service.create(datastream)


    def _query_things_for_datastream_url(self, iotid):

        location_iotid = location.id

        location_thing_url = f'{self._service.url}/Locations({location_iotid})/Things'

        r = requests.get(location_thing_url)

        #TODO: Add else or check for water well not found to return alt for datastream
        if r.status_code == 200:
            response_json = r.json()

            response_json_values = response_json["value"]

            water_well_thing_found = False

            for thing in response_json_values:
                if thing["name"] == "Water Well":
                    water_well_thing_found = True

                    #thing_url = response_json_values[0]["@iot.selfLink"]

                    datastream_url = response_json_values[0]["Datastreams@iot.navigationLink"]


    def _query_for_datastream_existence(self, datastream_url)
        
        r = requests.get(datastream_url)

        # Set false here instead of below??
        #datastream_found = False

        if r.status_code == 200:
            response_json = r.json()

            response_json_values = response_json["value"]

            datastream_found = False

            for datastream in response_json_values:
                if datastream["name"] == "Groundwater Levels":
                    datastream_found = True

        return datastream_found


    def _get_source_id_from_record(self, data)

        source_id = 0

        #TODO: Add WellID to nmbgmr ST locations
        if self._config['agency'] == "nmbgmr":
            source_id = data['WellID']
        elif self._config['agency'] == "isc":
            source_id = data['monitoring_point_id']
        elif self._config['agency'] == "pvacd":
            source_id = data['locationId']
        elif self._config['agency'] == "ebid":
            source_id = data['site_id']
        #TODO: add cabq and ose roswell basin
        #elif self._config['agency'] == "cabq":
        #    source_id = data['site_id']




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
