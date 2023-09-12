#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


from typing import Any, Iterable, Mapping

from airbyte_cdk import AirbyteLogger
from airbyte_cdk.destinations import Destination
from airbyte_cdk.models import AirbyteConnectionStatus, AirbyteMessage, ConfiguredAirbyteCatalog, Status, Type


import frost_sta_client as fsc
#import frost_sta_client.model.ext.unitofmeasurement 


from google.cloud import bigquery
from google.oauth2 import service_account
import os
import requests
from datetime import datetime
import copy
import logging
#import pyproj

logger = logging.getLogger("airbyte")

PROJECTIONS = {}


print ('\n================')
cwd = os.getcwd()

print (cwd)
cred_file = os.path.join(cwd, "secrets/bq_creds.json")

print (cred_file)

print ('\n================')

# Credentials to a GCP BigQuery table
#CREDENTIALS = service_account.Credentials.from_service_account_file("./secrets/bq_creds.json")


CREDENTIALS = service_account.Credentials.from_service_account_file(cred_file)


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

        print ("\n check !!!!!!!!22222")

        print ('\n================')
        print (CREDENTIALS)
        print ('\n================')



        self._config = config
        self._service = fsc.SensorThingsService(config["destination_path"])
        self._validation_service = "https://nmwdistvalidation-dot-waterdatainitiative-271000.appspot.com/"
            
        logger.info(f'========================')

        print ('1111')

        for message in input_messages:

            logger.info(f'Message: {message}')
            logger.info(f'========================')

            if message.type == Type.RECORD:

                logger.info(f'RECORD Message: {message}')
                logger.info(f'========================')

                data = message.record.data

                stream = message.record.stream

                datastream = self._make_datastream(data)

                #self._validate_datastream(datastream)

                #self._make_observation(datastream, data)
                
                #self._validate_observation(datastream)

                yield message

            elif message.type == Type.STATE:
                logger.info(f'STATE Message: {message}')
                logger.info(f'========================')

                yield message


            else:
                logger.info(f'Not Record Message: {message}')
                logger.info(f'========================')

                yield message


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
        #locations = self._service.locations().query().filter(f"source_id eq '{source_id}'").list()

        # Query BigQuery for source_id
        client = bigquery.Client(credentials=CREDENTIALS)

        #source_id_str = str(source_id)
        #source_id_str = str(180)

        print (source_id)

        #sql = 'select * from locations.isc_seven_rivers_monitoring_points '
        #sql = f'select * from locations.isc_seven_rivers_monitoring_points where id = {source_id_str}'

        #Works for isc b/c id is a str
        sql = f'select * from locations.isc_seven_rivers_monitoring_points where id = "{source_id}"'
        
        #Works
        #sql = f'select * from locations.isc_seven_rivers_monitoring_points where id = "180"'

        job = client.query(sql)

        result = job.result()
        
        print ('\n33333333333333================')
        print (result)
        print ('\n33333333333333================')

        for record in result:
            print (record)

            name = self._get_name_from_record(record)


            print ('\n55555555555533333333333333================')
            print (name)
            name = name + "__dju0d39t0m"
            print (name)
            print ('\n55555555555533333333333333================')



        print (source_id)
        print ('\n4444444================')


        # Query SensorThings for location name
        locations = self._service.locations().query().filter(f"name eq '{name}'").list()
        #location_props = self._make_location_properties(data)
        #loc = self._make_location_location(data, name)

        # Check length of list and log error if more than one location with the same name
        if len(locations.entities) > 100000:
        #if len(locations.entities) > 1:
            print ('\n6666666663333333333================')
            print ("Many LOC")
            print ('\n666666666633333333333333================')

            #Log error
            logger.error(f"Multiple locations with the name [{name}] exist")
           
            # Need to grab a single location entity to return from method
            for location in locations: 
                #pass
                print (location.name)


        # Else if one location exists, check if datastream exists
        #elif len(locations.entities) == 1:
        elif len(locations.entities) >= 1:
            print ('\n6666666663333333333================')
            print ("ONE LOC")
            print ('\n666666666633333333333333================')


            for location in locations:
                iotid = location.id
               
                datastream_url, thing = self._query_things_for_datastream_url(iotid)

                print ('\n77777777776666666663333333333================')
                print (datastream_url)
                print (thing)
                print ('\n777777777666666666633333333333333================')


                # Check if datastream exists
                if (self._query_for_datastream_existence(datastream_url)):
                    # Add observations
                    pass
                else:
                    # Create Datastream
                    print ('\n111116666666663333333333================')
                    print ("DS NOT EXIST")
                    print ('\n111116666666663333333333================')


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



                    #TODO: Add phenomenon_time and result_time 
                    datastream = fsc.Datastream(name="Groundwater Levels",
                                            description='Measurement of groundwater depth in a water well, as measured below ground surface',
                                            observation_type="http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Measurement",
                                            observed_area=location.location,
                                            properties={"topic": "Water Quantity", "agency": self._config['agency']},
                                            observed_property=observed_property_obj,
                                            sensor=sensor_obj,
                                            thing=thing,
                                            unit_of_measurement=unit_of_measurement_obj)
                    self._service.create(datastream)



                break



        # Else log error for no location existing
        else:
            print ('\n6666666663333333333================')
            print ("No LOC")
            print ('\n666666666633333333333333================')

            #Log error
            logger.error(f"No location exists with the name [{name}]")



        """
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
                                            observation_type="http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Measurement",
                                            observed_area=location.location,
                                            properties={"topic", "Water Quantity"},
                                            unit_of_measurement=unit_of_measurement_dict)
                    self._service.create(datastream)

        """      



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



    def _query_things_for_datastream_url(self, iotid):

        #location_iotid = location.id

        #location_thing_url = f'{self._service.url}/Locations({location_iotid})/Things'
        location_thing_url = f'{self._service.url}/Locations({iotid})/Things'

       
        print ('\n999996666666663333333333================')
        print (location_thing_url)
        print ('\n9999999666666666633333333333333================')



        r = requests.get(location_thing_url)

        #TODO: Add else or check for water well not found to return alt for datastream
        if r.status_code == 200:
            print ('\n111999996666666663333333333================')
            print ("200")
            print ('\n11119999999666666666633333333333333================')

            datastream_url = ""

            response_json = r.json()

            response_json_values = response_json["value"]

            print ('\n44111999996666666663333333333================')
            print (response_json_values)
            print ('\n4411119999999666666666633333333333333================')

            water_well_thing_found = False

            for thing_value in response_json_values:
                if thing_value["name"] == "Water Well":
                    water_well_thing_found = True

                    print ('\n0000099996666666663333333333================')
                    print ("found water well")
                    print ('\n000009999999666666666633333333333333================')

                    #thing_url = response_json_values[0]["@iot.selfLink"]

                    thing_id = response_json_values[0]["@iot.id"]

                    datastream_url = response_json_values[0]["Datastreams@iot.navigationLink"]

                    print (thing_id)


                #locations = self._service.locations().query().filter(f"name eq '{name}'").list()
                things_list = self._service.things().query().filter(f"id eq {thing_id}").list()

                for thing in things_list:
                    print ('\n777799996666666663333333333================')
                    print (thing)
                    print ('\n777799996666666663333333333================')
                    pass 



            return datastream_url, thing
            #return datastream_url





    def _query_for_datastream_existence(self, datastream_url):
        
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


    def _get_source_id_from_record(self, data):


        print ("1111@@@@@@@@@@@@@@@@@@2222")
        print (self._config['agency'])
        print ("1111@@@@@@@@@@@@@@@@@@2222")


        source_id = 0

        #TODO: Add WellID to nmbgmr ST locations
        if self._config['agency'] == "nmbgmr":
            source_id = data['WellID']
        elif self._config['agency'] == "isc":
            print ("@@@@@@@@@@@@@@@@@@2222")
            source_id = data['monitoring_point_id']
        elif self._config['agency'] == "pvacd":
            source_id = data['locationId']
        elif self._config['agency'] == "ebid":
            source_id = data['site_id']
        #TODO: add cabq and ose roswell basin
        #elif self._config['agency'] == "cabq":
        #    source_id = data['site_id']

        return source_id


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

        print ("\n check !!!!!!!!1")

        try:
            x = requests.request("CONNECT", config["destination_path"])

            return AirbyteConnectionStatus(status=Status.SUCCEEDED)
        except Exception as e:
            return AirbyteConnectionStatus(status=Status.FAILED, message=f"An exception occurred: {repr(e)}")
