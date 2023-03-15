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
import requests
from datetime import datetime
import copy
import logging


logger = logging.getLogger("airbyte")


#Probably need different implmentations of this for different sources
def make_geometry_point_from_latlon(lat, lon):
    return {"type": "Point", "coordinates": [float(lon), float(lat)]}


class DestinationSensorthingsLocations(Destination):
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

        service = fsc.SensorThingsService(config["destination_path"])

        for message in input_messages:
           
            if message.type == Type.RECORD:
                data = message.record.data
                stream = message.record.stream

                loc = make_geometry_point_from_latlon(data['latitude'], data['longitude'])

                # Location base properties
                location_props = {'source_id': data['id'],
                         'agency': config['agency']}

                # Thing base properties
                thing_props = {'source_id': data['id'],
                         'agency': config['agency']}


                # If the agency is ISC_SEVEN_RIVERS, then add groundSurfaceElevationFeet and
                # source_api to location properties
                if config['agency'] == "ISC_SEVEN_RIVERS":
                    location_props['groundSurfaceElevationFeet'] = data['groundSurfaceElevationFeet']
                    location_props['source_api'] = config['source_api']
                    thing_props['type'] = data['type']



                # If the agency is NMBGMR, then add WellID, PointID, and geoconnex to properties
                elif config['agency'] == "NMBGMR":
                    location_props['WellID'] = data['WellID'] 
                    location_props['PointID'] = data['PointID']
                    location_props['Altitude'] = data['Altitude']
                    location_props['geoconnex'] = data['geoconnex'] 
                    thing_props['WellID'] = data['WellID'] 
                    thing_props['PointID'] = data['PointID']
                    thing_props['WellDepth'] = data['WellDepth']
                    thing_props['GeologicFormation'] = data['GeologicFormation']



                # If the agency is PVACD, then add WellID, PointID, and geoconnex to properties
                elif config['agency'] == "PVACD":
                    #location_props['WellID'] = data['WellID'] 
                    thing_props['aquifer'] = data['aquifer']
                    thing_props['aquifer_group'] = data['aquifer_group']
                    thing_props['model_formation'] = data['model_formation']





                # If the agency is EBID, then add WellID, PointID, and geoconnex to properties
                elif config['agency'] == "EBID":
                    location_props['site_id'] = data['site_id'] 
                    location_props['location'] = data['location'] 
                    location_props['elevation'] = data['elevation'] 
                    location_props['geoconnex'] = data['geoconnex'] 
                    location_props['or_site_id'] = data['or_site_id'] 
                    location_props['latitude_dec'] = data['latitude_dec'] 
                    location_props['longitude_dec'] = data['longitude_dec'] 
                



                # ALSO ADD AND SEPARATE LOC AND THING PROPS 
                #'observation_category': config['observation_category'] - needed??


                # Location dict for patch
                location_obj = {'name': data['name'],
                        'description': config['description'],
                        'location': loc,
                        'properties': location_props,
                        "encodingType": "application/vnd.geo+json", }

                # Location entity for create
                location = fsc.Location(name=data['name'], 
                           description='Location of well where measurements are made', 
                           location=loc,
                           properties=location_props,
                           encoding_type="application/vnd.geo+json")

                # Thing dict for patch
                #thing_obj = {'name': config['name'],
                thing_obj = {'name': "Water Well",
                       #'description': config['description'],
                       'description': "Well drilled or set into subsurface for the purposes of pumping water or monitoring groundwater",
                       'properties': thing_props,
                      }

                # Thing entity for create
                #thing = fsc.Thing(name = config['name'],
                thing = fsc.Thing(name = "Water Well",
                        #description = config['description'],
                        description = "Well drilled or set into subsurface for the purposes of pumping water or monitoring groundwater",
                        properties = thing_props)

                # Add location entity to thing entity
                thing.locations = [location]

                name = data['name']

                # Query SensorThings for location name
                locations_list = service.locations().query().filter(f"name eq '{name}'").list()

                # Check length of list and log error if more than one location with the same name
                if len(locations_list.entities) > 1:
                    #Log error
                    logger.error(f"Multiple locations with the name [{name}] exist")

                # Else if one location exists, patch location and associated thing(s)
                elif len(locations_list.entities) == 1:
                    for location in locations_list:
                        location_url = copy.deepcopy(service.url)
                        
                        location_url.path.add(service.locations().entity_path(location.id))
                      
                        location_thing_url = copy.deepcopy(location_url)

                        location_thing_url.path.add("/Things")

                        r = requests.get(location_thing_url)
                        
                        response_json = r.json()

                        response_json_values = response_json["value"]

                        # TODO: Ability to parse and patch multiple things per location if exist
                        thing_url = response_json_values[0]["@iot.selfLink"]

                        # Location Patch
                        loc_resp = requests.patch(location_url, json = location_obj)

                        # Log error if patch fails
                        if loc_resp.status_code != 200:
                            logger.error(f"Patch error for location [{name}]: {loc_resp.content}")

                        # Thing Patch
                        thing_resp = requests.patch(thing_url, json = thing_obj)

                        # Log error if patch fails
                        if thing_resp.status_code != 200:
                            logger.error(f"Patch error for thing associated with location [{name}]: {thing_resp.content}")



                # Else create new location and associated thing(s)
                else:
                    # Create entity
                    service.create(thing)





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
