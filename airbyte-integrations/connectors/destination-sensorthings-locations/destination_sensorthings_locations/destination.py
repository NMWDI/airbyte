#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#

from typing import Any, Iterable, Mapping

from airbyte_cdk import AirbyteLogger
from airbyte_cdk.destinations import Destination
from airbyte_cdk.models import AirbyteConnectionStatus, AirbyteMessage, ConfiguredAirbyteCatalog, Status, Type

import frost_sta_client as fsc

import os
import requests
from datetime import datetime
import copy
import logging
import pyproj
import time

logger = logging.getLogger("airbyte")

PROJECTIONS = {}


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

        self._config = config
        self._service = fsc.SensorThingsService(config["destination_path"])
        self._validation_service = "https://nmwdistvalidation-dot-waterdatainitiative-271000.appspot.com/"

        for message in input_messages:

            if message.type == Type.RECORD:

                data = message.record.data

                stream = message.record.stream

                location = self._make_location(data)

                self._validate_location(location)

                self._make_thing(location, data)
                
                self._validate_thing(location)


            elif message.type == Type.STATE:
                yield message

            else:
                yield message


    def _make_location(self, data):
        # does this location exist
        name = self._get_name_from_record(data)

        # Query SensorThings for location name
        locations = self._service.locations().query().filter(f"name eq '{name}'").list()
        location_props = self._make_location_properties(data)
        loc = self._make_location_location(data, name)

        # Check length of list and log error if more than one location with the same name
        if len(locations.entities) > 1:
            #Log error
            logger.error(f"Multiple locations with the name [{name}] exist")
           
            # Need to grab a single location entity to return from method
            for location in locations: 
                pass


        # Else if one location exists, patch location and associated thing(s)
        elif len(locations.entities) == 1:
            for location in locations: 
                iotid = location.id

                total_location_props = location.properties

                total_location_props.update(location_props)

                # patch the location
                self._patch_location(location, name, total_location_props, loc)


        # Else make the location and add to ST
        else:
            location = fsc.Location(name=name,
                                    description='Location of well where measurements are made',
                                    location=loc,
                                    properties=location_props,
                                    encoding_type="application/vnd.geo+json")
            self._service.create(location)

            locations = self._service.locations().query().filter(f"name eq '{name}'").list()

            # get the iot.id for the newly created location
            for a_location in locations: 
                iotid = a_location.id

            # Add geoconnex url to properties 
            location_props['geoconnex'] = f'https://geoconnex.us/nmwdi/st/locations/{iotid}'

            # Patch geoconnex url
            self._patch_location(location, name, location_props, loc)

        return location


    def _make_thing(self, location, data):
        # does the thing exist?

        thing_props = self._make_thing_properties(data)

        location_iotid = location.id

        location_thing_url = f'{self._service.url}/Locations({location_iotid})/Things'

        r = requests.get(location_thing_url)

        if r.status_code == 200:
            response_json = r.json()

            response_json_values = response_json["value"]

            water_well_thing_found = False

            for thing in response_json_values:
                if thing["name"] == "Water Well":
                    water_well_thing_found = True
                   
                    thing_url = response_json_values[0]["@iot.selfLink"]

                    # Thing dict for patch
                    thing_obj = {'name': "Water Well",
                                 'description': "Well drilled or set into subsurface for the purposes of pumping water or monitoring groundwater",
                                  'properties': thing_props,
                                }

                    # patch the thing
                    self._patch_thing(thing_url, thing_obj)

                    break

            
            if not water_well_thing_found:
                # Thing entity for create
                thing = fsc.Thing(name = "Water Well",
                                  description = "Well drilled or set into subsurface for the purposes of pumping water or monitoring groundwater",
                                  properties = thing_props)

                # Add location entity to thing entity
                thing.locations = [location]

                self._service.create(thing)


        else:
            # Thing entity for create
            thing = fsc.Thing(name = "Water Well",
                              description = "Well drilled or set into subsurface for the purposes of pumping water or monitoring groundwater",
                              properties = thing_props)

            # Add location entity to thing entity
            thing.locations = [location]

            self._service.create(thing)


    def _patch_location(self, location, name, props, loc):
        iotid = location.id

        location_url = f'{self._service.url}/Locations({iotid})'

        # Location dict for patch
        location_obj = {'name': name,
                        'description': 'Location of well where measurements are made',
                        'location': loc,
                        'properties': props,
                        'encodingType': "application/vnd.geo+json", }
        
        # Location Patch
        loc_resp = requests.patch(location_url, json = location_obj)

        # Log error if patch fails
        if loc_resp.status_code != 200:
            logger.error(f"Patch error for location [{name}]: {loc_resp.content}")


    def _patch_thing(self, thing_url, thing_obj):
        # Thing Patch
        thing_resp = requests.patch(thing_url, json = thing_obj)

        # Log error if patch fails
        if thing_resp.status_code != 200:
            logger.error(f"Patch error for thing associated with location [{name}]: {thing_resp.content}")


    def _validate_location(self, location):
        location_iotid = location.id

        validation_resp = requests.get(f'{self._validation_service}validate_location?url={self._service.url}/Locations({location_iotid})')

        response_json = validation_resp.json()

        try:
            validation_json = response_json[0]
            validation_error = True
        except:
            validation_error = False

        # Log error if call to validation service fails
        if validation_resp.status_code != 200:
            logger.error(f"Validation service error call for location {self._service.url}/Locations({location_iotid}) - {validation_resp.content}")
 
        elif validation_error and "validation_error" in validation_json:
            logger.error(f"Validation error for location {self._service.url}/Locations({location_iotid}) -  {validation_json}")


    def _validate_thing(self, location):
        location_iotid = location.id

        location_thing_url = f'{self._service.url}/Locations({location_iotid})/Things'

        r = requests.get(location_thing_url)

        response_json = r.json()

        response_json_values = response_json["value"]

        for thing in response_json_values:
            if thing["name"] == "Water Well":
                thing_url = response_json_values[0]["@iot.selfLink"]

                validation_resp = requests.get(f'{self._validation_service}validate_thing?url={thing_url}')

                response_json = validation_resp.json()

                try:
                    validation_json = response_json[0]
                    validation_error = True
                except:
                    validation_error = False

                # Log error if call to validation service fails
                if validation_resp.status_code != 200:
                    logger.error(f"Validation service error call for thing {thing_url} - {validation_resp.content}")
         
                elif validation_error and "validation_error" in validation_json:
                    logger.error(f"Validation error for thing {thing_url} - {validation_json}")


    def _make_location_properties(self, data):

        # Location base properties
        location_props = {'agency': self._config['agency'],
                         'collection_agency': self._config['agency']}


        if self._config['agency'] == "isc":
            location_props['location_source'] = "unknown"
            if data['groundSurfaceElevationFeet'] != None:
                location_props['elevation'] = {"accuracy": 0, "source": "unknown"}
            else:
                location_props['elevation'] = {"accuracy": 0, "source": "https://epqs.national_map.gov/v1/"}


        elif self._config['agency'] == "nmbgmr":
            location_props['location_source'] = "gps"
            if data['AltitudeAccuracy'] != None:
                location_props['elevation'] = {"accuracy": data['AltitudeAccuracy'], "source": "gps"}
            else:
                if data['Altitude'] != None:
                    location_props['elevation'] = {"accuracy": 0, "source": "gps"}
                else:
                    location_props['elevation'] = {"accuracy": 0, "source": "https://epqs.national_map.gov/v1/"}

                    
        elif self._config['agency'] == "pvacd":
            location_props['location_source'] = "unknown"
            location_props['elevation'] = {"accuracy": 0, "source": "https://epqs.national_map.gov/v1/"}


        elif self._config['agency'] == "ebid":
            location_props['location_source'] = 'unknown'
            if data['elevation'] != None:
                location_props['elevation'] = {"accuracy": 0, "source": "unknown"}
            else:
                location_props['elevation'] = {"accuracy": 0, "source": "https://epqs.national_map.gov/v1/"}
            if 'site_id' in data:
                location_props['site_id'] = data['site_id']
            if 'location' in data:
                location_props['location'] = data['location']
            if 'or_site_id':
                location_props['or_site_id'] = data['or_site_id']


        elif config['agency'] == "cabq":
            location_props['location_source'] = 'unknown'
            if data['reference_elev'] != None:
                location_props['elevation'] = {"accuracy": 0, "source": "unknown"}
            else:
                location_props['elevation'] = {"accuracy": 0, "source": "https://epqs.national_map.gov/v1/"}
            if 'facility_id' in data:
                location_props['facility_id'] = data['facility_id']
            if 'facility_code' in data:
                location_props['facility_code'] = data['facility_code']
            if 'depth_units' in data:
                location_props['altitude_units'] = data['depth_units']

        return location_props


    def _make_thing_properties(self, data):
        # Thing base properties
        thing_props = {'agency': self._config['agency'],
                 'well_depth': {"value": -1, "units": "mbgs"},
                 'kind': "unknown",
                 'current_use': "unknown",
                 'status': "unknown"
                 }


        if self._config['agency'] == "isc":
            if 'type' in data:
                thing_props['type'] = data['type']


        elif self._config['agency'] == "nmbgmr":
            if data['WellDepth'] != None:
                thing_props['well_depth'] = {"value": self._feet_to_meters(data['WellDepth']), "units": "mbgs"}

            if "SiteType" in data:
                thing_props['kind'] = data['SiteType']

            if "CurrentUseDescription" in data:
                thing_props['current_use'] = data['CurrentUseDescription']

            if "StatusDescription" in data:
                thing_props['status'] = data['StatusDescription']

            if "OSEWelltagID" in data:
                thing_props['ose_well_tag'] = data['OSEWelltagID']

            if "CompletionDate" in data:
                thing_props['completion_date'] = data['CompletionDate']

            if "ConstructionMethod" in data:
                thing_props['construction_method'] = data['ConstructionMethod']

            if 'GeologicFormation' in data:
                thing_props['geologic_formation'] = data['GeologicFormation']

            if data['CasingDiameter'] != None:
                thing_props['casing'] = {"diameter": self._feet_to_meters(data['CasingDiameter']), "units": "meters"} 
            else:
                thing_props['casing'] = {"value": -1, "units": "meters"}
               
            if "AquiferType" in data:
                thing_props['aquifer'] = data['AquiferType']

            if data['HoleDepth'] != None:
                thing_props['hole_depth'] = {"value": self._feet_to_meters(data['HoleDepth']), "units": "mbgs"}
            else:
                thing_props['hole_depth'] = {"value": -1, "units": "mbgs"}

            if 'CurrentUseDescription' in data:
                thing_props['use'] = data['CurrentUseDescription']
            

        elif self._config['agency'] == "pvacd":
            thing_props['kind'] = "groundwater_well"
            thing_props['current_use'] = "monitoring"

            # Below are not in BQ but in ST
            # Put this info into BQ
            if 'aquifer' in data:
                thing_props['aquifer'] = data['aquifer']
            if 'aquifer_group' in data:
                thing_props['aquifer_group'] = data['aquifer_group']
            if 'model_formation' in data:
                thing_props['model_formation'] = data['model_formation']


        elif self._config['agency'] == "ebid":
            pass

        elif self._config['agency'] == "cabq":
            # Check empty str w/ more data
            if data['measured_depth_of_well'] != '""':
                thing_props['well_depth'] = {"value": self._feet_to_meters(data['measured_depth_of_well']), "units": "mbgs"}

        return thing_props


    # Add elevation as the 3rd coord and convert ft above sea level to meters above sea level
    def _make_location_location(self, data, name):
        if self._config['agency'] == "isc":
            if data['groundSurfaceElevationFeet'] != None and data['groundSurfaceElevationFeet'] > 0.0:
                elev_m = self._feet_to_meters(data['groundSurfaceElevationFeet'])
            else:
                # Query elevation service
                elev_m = self._get_elevation(data['latitude'], data['longitude'], name)

            loc = self._make_geometry_point_from_lat_lon_elev(data['latitude'], data['longitude'], elev_m)


        elif self._config['agency'] == 'nmbgmr':
            e = data['Easting']
            n = data['Northing']
            z = 13
            loc = self._make_geometry_point_from_utm(e, n, data['Altitude'], name, z)
       

        elif self._config['agency'] == "ebid":
            if data['elevation'] != None and data['elevation'] > 0.0:
                elev_m = self._feet_to_meters(data['elevation'])
            else:
                # Query elevation service
                elev_m = self._get_elevation(data['latitude_dec'], data['longitude_dec'], name)
            
            loc = self._make_geometry_point_from_lat_lon_elev(data['latitude_dec'], data['longitude_dec'], elev_m)


        elif self._config['agency'] == "pvacd":
            # Query elevation service
            elev_m = self._get_elevation(data['latitude'], data['longitude'], name)
            loc = self._make_geometry_point_from_lat_lon_elev(data['latitude'], data['longitude'], elev_m)


        # Currently just query elevation service for else
        else:
            # Query elevation service
            elev_m = self._get_elevation(data['latitude'], data['longitude'], name)
            loc = self._make_geometry_point_from_lat_lon_elev(data['latitude'], data['longitude'], elev_m)


        return loc


    def _feet_to_meters(self, ft):
        return ft * 0.3048


    def _make_geometry_point_from_lat_lon_elev(self, lat, lon, elev):
        return {"type": "Point", "coordinates": [float(lon), float(lat), float(elev)]}


    def _make_geometry_point_from_utm(self, e, n, altitude, zone=None, ellps=None, srid=None):
        if zone:
            if zone in PROJECTIONS:
                p = PROJECTIONS[zone]
            else:
                if ellps is None:
                    ellps = "WGS84"
                p = pyproj.Proj(proj="utm", zone=int(zone), ellps=ellps)
                PROJECTIONS[zone] = p
        elif srid:
            # get zone
            if srid in PROJECTIONS:
                p = PROJECTIONS[srid]
                PROJECTIONS[srid] = p
            else:
                # p = pyproj.Proj(proj='utm', zone=int(zone), ellps='WGS84')
                p = pyproj.Proj("EPSG:{}".format(srid))

        lon, lat = p(e, n, inverse=True)

        if altitude != None and altitude > 0.0:
            elev_m = self._feet_to_meters(altitude)
        else:
            # Query elevation service
            elev_m = self._get_elevation(lat, lon, name)

        return self._make_geometry_point_from_lat_lon_elev(lat, lon, elev_m)


    def _get_elevation(self, lat, lon, name):
        url = 'https://epqs.nationalmap.gov/v1/json'
        max_retries = 10

        for attempt in range(max_retries):
            try:
                r = requests.get(url, params={'x': lon, 'y': lat, 'units': 'Meters', 'output': 'json'})
                data = r.json()
                elevation = data['value']
                return elevation

            except:
                time.sleep(5)

        #Log error
        logger.error(f"Error querying USGS EPQS for elevation of [{name}]")

        return -1.0


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
