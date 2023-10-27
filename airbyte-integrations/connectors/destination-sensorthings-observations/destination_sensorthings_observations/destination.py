#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#
from typing import Any, Iterable, Mapping

from airbyte_cdk import AirbyteLogger
from airbyte_cdk.destinations import Destination
from airbyte_cdk.models import AirbyteConnectionStatus, AirbyteMessage, ConfiguredAirbyteCatalog, Status, Type

import frost_sta_client as fsc

from google.cloud import bigquery
from google.oauth2 import service_account
import os
import json
import requests
from datetime import datetime
import copy
import logging

logger = logging.getLogger("airbyte")


class DestinationSensorthingsObservations(Destination):
    def write(
        self, config: Mapping[str, Any], configured_catalog: ConfiguredAirbyteCatalog, input_messages: Iterable[AirbyteMessage]
    ) -> Iterable[AirbyteMessage]:

        """
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
            
        #logger.info(f'========================')

        bigquery_credentials = json.loads(config["bigquery_credentials"])

        CREDENTIALS = service_account.Credentials.from_service_account_info(bigquery_credentials)

        # Query BigQuery for source_id
        self._client = bigquery.Client(credentials=CREDENTIALS)

        for message in input_messages:

            #logger.info(f'Message: {message}')
            #logger.info(f'========================')

            if message.type == Type.RECORD:

                #logger.info(f'RECORD Message: {message}')
                #logger.info(f'========================')

                data = message.record.data

                stream = message.record.stream

                datastream, new_datastream_created = self._make_datastream(data)

                if new_datastream_created:
                    self._validate_datastream(datastream)

                    observation = self._make_observation(datastream, data)
                
                    #self._validate_observation(observation)

                yield message


            elif message.type == Type.STATE:
                #logger.info(f'STATE Message: {message}')
                #logger.info(f'========================')

                yield message


            else:
                #logger.info(f'Not Record Message: {message}')
                #logger.info(f'========================')

                yield message


    def _make_datastream(self, data):
        # Get source_id from record
        source_id= self._get_source_id_from_record(data)

        # Get sql query for agency's locations table in BigQuery for the source_id
        sql = self._get_bq_sql_query(source_id)     

        job = self._client.query(sql)

        result = job.result()

        if result.total_rows > 0:
            try:
                for record in result:
                    name = self._get_name_from_record(record)

                    # Uncomment below block for unit testing on nmbgmr development frost server.
                    # Since multiple copies of the base names exist in ST on the frost server,
                    # the following random string additions single out one location.
                    #if self._config['agency'] == "nmbgmr":
                    #    name = name + "__6cddnvwp7j"
                    #elif self._config['agency'] == "isc":
                    #    name = name + "__dju0d39t0m"
                    #elif self._config['agency'] == "pvacd":
                    #    name = name + "__c28ogugvgv"
                    #elif self._config['agency'] == "ebid":
                    #    name = name + "__z60tzi8zrp"


                # Query SensorThings for location name
                locations = self._service.locations().query().filter(f"name eq '{name}'").list()

                location_exists = True

            except:
                location_exists = False
                      
        else:
            location_exists = False


        # Check length of list and log error if more than one location with the same name
        if location_exists and len(locations.entities) > 1:

            #Log error
            logger.error(f"Multiple locations with the name [{name}] exist")
           
            # Need to grab a single location entity to return from method
            for location in locations: 
                pass

            return self._make_empty_datastream(), False

        # Else if one location exists, check if datastream exists
        elif location_exists and len(locations.entities) == 1:

            for location in locations:
                iotid = location.id
               
                datastream_url, thing = self._query_things_for_datastream_url(iotid)

                if thing is not None:
                    # Check if datastream exists
                    datastream_exists, datastream, query_error = self._query_for_datastream_existence(datastream_url)
                    if query_error:
                        return self._make_empty_datastream(), False

                else:
                    return self._make_empty_datastream(), False


                if datastream_exists:
                    pass

                else:
                    # Create Datastream
                    # TODO: Add datastream for groundwater quality
                    datastream = self._make_groundwater_datastream(location, thing)

                break

            return datastream, True


        # Else log error for no location existing
        else:
            #Log error
            try:
                logger.error(f"No location exists with the name [{name}] corresponding to the record [{data}]")
            except:
                logger.error(f"No location exists corresponding to the record [{data}]")


            return self._make_empty_datastream(), False


    def _make_groundwater_datastream(self, location, thing):

        unit_of_measurement_dict = {
            "name": "Foot",
            "symbol": "ft",
            "definition": "http://www.qudt.org/vocab/unit/FT"
        }

        unit_of_measurement_obj = fsc.UnitOfMeasurement(name="Foot",
                                  symbol="ft",
                                  definition="http://www.qudt.org/vocab/unit/FT")

        observed_property_obj = fsc.ObservedProperty(name="Depth to Water Below Ground Surface",
                                definition="No Definition",
                                description="depth to water below ground surface")

        sensor_obj = fsc.Sensor(name="NoSensor",
                                description="No Description",
                                encoding_type="application/pdf",
                                metadata="No Metadata")


        datastream = fsc.Datastream(name="Groundwater Levels",
                                description="Measurement of groundwater depth in a water well, as measured below ground surface",
                                observation_type="http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Measurement",
                                observed_area=location.location,
                                properties={"topics": ["Water Quantity"], "agency": self._config['agency']},
                                observed_property=observed_property_obj,
                                sensor=sensor_obj,
                                thing=thing,
                                unit_of_measurement=unit_of_measurement_obj)
        self._service.create(datastream)

        return datastream


    def _make_empty_datastream(self):
        datastream = fsc.Datastream(name="",
                                description="",
                                observation_type="",
                                observed_area=None,
                                properties=None,
                                observed_property=None,
                                sensor=None,
                                thing=None,
                                unit_of_measurement=None)

        return datastream


    def _make_observation(self, datastream, data): 

        datastream_iotid = datastream.id

        datastream_observation_url = f'{self._service.url}/Datastreams({datastream_iotid})/Observations'

        # Retrieve phenomenon_time
        if self._config['agency'] == "nmbgmr":
            date_time_str = data['DateTimeMeasured'].rstrip(' UTC')

            try:
                date_time = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
            except:
                date_time = datetime.strptime(date_time_str, '%Y-%m-%dT%H:%M:%SZ')

            phenomenon_time = datetime.strftime(date_time, '%Y-%m-%dT%H:%M:%S.000Z')

        elif self._config['agency'] == "isc":
            phenomenon_time = datetime.strftime(datetime.utcfromtimestamp(data['dateTime']/1000), '%Y-%m-%dT%H:%M:%S.000Z')

        elif self._config['agency'] == "pvacd":
            phenomenon_time = datetime.strftime(datetime.utcfromtimestamp(data['timestamp']), '%Y-%m-%dT%H:%M:%S.000Z')
        
        elif self._config['agency'] == "ebid":
            date_time_str = data['data_time']            

            date_time = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')

            phenomenon_time = datetime.strftime(date_time, '%Y-%m-%dT%H:%M:%S.000Z')

        #TODO: add cabq and ose roswell basin
        #elif self._config['agency'] == "cabq":


        # Retrieve result
        if self._config['agency'] == "isc":
            result = data['depthToWaterFeet']
            parameters = None

        elif self._config['agency'] == "pvacd":
            result = data['value']
            parameters = None

        elif self._config['agency'] == "nmbgmr":
            result = data['DepthToWater']
            parameters = {"level_status": data['LevelStatus']}
       
        elif self._config['agency'] == "ebid":
            result = data['data_value']
            parameters = None
       
        #TODO: add cabq and ose roswell basin
        #elif self._config['agency'] == "cabq":


        if type(result) == float or type(result) == int:
            pass
        else:
            result = -99999.0


        observation = fsc.Observation(phenomenon_time=phenomenon_time,
                                result=result,
                                result_time=phenomenon_time,
                                datastream=datastream,
                                parameters=parameters)

        self._service.create(observation)

        return observation


    def _validate_datastream(self, datastream):

        datastream_iotid = datastream.id

        validation_resp = requests.get(f'{self._validation_service}validate_datastream?url={self._service.url}/Datastreams({datastream_iotid})')

        response_json = validation_resp.json()

        try:
            validation_json = response_json[0]
            validation_error = True
        except:
            validation_error = False

        # Log error if call to validation service fails
        if validation_resp.status_code != 200:
            logger.error(f"Validation service error call for datastream {self._service.url}/Datastreams({datastream_iotid}) - {validation_resp.content}")

        elif validation_error and "validation_error" in validation_json:
            logger.error(f"Validation error for datastream {self._service.url}/Datastreams({datastream_iotid}) -  {validation_json}")


    def _validate_observation(self, observation):

        observation_iotid = observation.id

        validation_resp = requests.get(f'{self._validation_service}validate_observation?url={self._service.url}/Observations({observation_iotid})')

        response_json = validation_resp.json()

        try:
            validation_json = response_json[0]
            validation_error = True
        except:
            validation_error = False

        # Log error if call to validation service fails
        if validation_resp.status_code != 200:
            logger.error(f"Validation service error call for observation {self._service.url}/Observations({observation_iotid}) - {validation_resp.content}")

        elif validation_error and "validation_error" in validation_json:
            logger.error(f"Validation error for observation {self._service.url}/Observations({observation_iotid}) -  {validation_json}")


    def _get_name_from_record(self, data):
        name = ''
        if self._config['agency'] == "nmbgmr":
            name = data['PointID']
        elif self._config['agency'] == "isc":
            name = data['name']
        elif self._config['agency'] == "pvacd":
            name = data['name']
        elif self._config['agency'] == "ebid":
            name = data['site_id']
        #TODO: add cabq and ose roswell basin
        #elif self._config['agency'] == "cabq":
        #    name = data['site_id']

        return name


    def _get_source_id_from_record(self, data):

        source_id = 0

        if self._config['agency'] == "nmbgmr":
            source_id = data['PointID']
        elif self._config['agency'] == "isc":
            source_id = data['monitoring_point_id']
            # In BigQuery, the montioring_point_id is currently a float.
            # Therfore, it needs to be converted to an int and will then be converted
            # to a string in the sql query.
            source_id = int(source_id)
        elif self._config['agency'] == "pvacd":
            source_id = data['locationId']
        elif self._config['agency'] == "ebid":
            source_id = data['site_id']
        #TODO: add cabq and ose roswell basin
        #elif self._config['agency'] == "cabq":
        #    source_id = data['']

        return source_id


    def _get_bq_sql_query(self, source_id):     
 
        if self._config['agency'] == "nmbgmr":
            sql = f'select * from locations.nmbgmr_sites where PointId = "{source_id}"'
        elif self._config['agency'] == "isc":
            sql = f'select * from locations.isc_seven_rivers_monitoring_points where id = "{source_id}"'
        elif self._config['agency'] == "pvacd":
            source_id = int(source_id)
            sql = f'select * from locations.pecos_locations where id = {source_id}'
        elif self._config['agency'] == "ebid":
            sql = f'select * from ebid.GetSiteMetaData where site_id = "{source_id}"'
        #TODO: add cabq and ose roswell basin
        #elif self._config['agency'] == "cabq":
        #   sql = ''

        return sql


    def _query_things_for_datastream_url(self, iotid):

        location_thing_url = f'{self._service.url}/Locations({iotid})/Things'

        r = requests.get(location_thing_url)

        if r.status_code == 200:
            datastream_url = ""

            response_json = r.json()

            response_json_values = response_json["value"]

            water_well_thing_found = False

            for thing_value in response_json_values:
                if thing_value["name"] == "Water Well":
                    water_well_thing_found = True

                    thing_id = response_json_values[0]["@iot.id"]

                    datastream_url = response_json_values[0]["Datastreams@iot.navigationLink"]

                things_list = self._service.things().query().filter(f"id eq {thing_id}").list()

                for thing in things_list:
                    pass 

            return datastream_url, thing

        else:
            logger.error(f"Error retrieving Location Thing URL {location_thing_url}. Status code {r.status_code}")

            datastream_url = ""

            thing = None

            return datastream_url, thing


    def _query_for_datastream_existence(self, datastream_url):

        datastream_object = None

        r = requests.get(datastream_url)

        datastream_found = False

        if r.status_code == 200:
            response_json = r.json()

            response_json_values = response_json["value"]

            query_error = False

            for datastream in response_json_values:
                if datastream["name"] == "Groundwater Levels":
                    datastream_found = True

                    datastream_id = datastream["@iot.id"]

                    datastreams_list = self._service.datastreams().query().filter(f"id eq {datastream_id}").list()

                    for a_datastream in datastreams_list:
                        datastream_object = a_datastream
                        pass 


        else:
            logger.error(f"Error retrieving Datastream URL {datastream_url}. Status code {r.status_code}")

            query_error = True

            datastream_object = self._make_empty_datastream() 


        return datastream_found, datastream_object, query_error



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
