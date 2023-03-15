#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


from typing import Any, Iterable, Mapping

from airbyte_cdk import AirbyteLogger
from airbyte_cdk.destinations import Destination
from airbyte_cdk.models import AirbyteConnectionStatus, AirbyteMessage, ConfiguredAirbyteCatalog, Status, Type


from google.cloud import bigquery
from google.oauth2 import service_account
import os
import requests
from datetime import datetime


AGENCY = 'ISC'


'''
URL = 'http://34.106.60.230:8080/FROST-Server/v1.1/Locations'


obj = {'name': 'Test1 Totalizer Monitoring System',
    'description': 'Test1 ISC Totalizer Observations'
      }

x = requests.post(URL, json=obj)
'''


URL = 'http://34.106.60.230:8080/FROST-Server/v1.1/Things'
OBSERVATIONS_URL = 'http://34.106.60.230:8080/FROST-Server/v1.1/Observations'



def make_geometry_point_from_latlon(lat, lon):
    return {"type": "Point", "coordinates": [float(lon), float(lat)]}


def get_location_data():
    print("get_location_data")

    credentials = service_account.Credentials.from_service_account_file("/home/david/Documents/Keys/waterdatainitiative-271000-2b71521209ba.json")

    client = bigquery.Client(credentials=credentials)

    sql = 'select * from locations.isc_seven_rivers_monitoring_points'

    job = client.query(sql)

    result = job.result()

    #print (result)


    for record in result:

        print (record)

        loc = make_geometry_point_from_latlon(record['latitude'], record['longitude'])

        props = {'source_id': record['id'],
                 'agency': config['agency'],
                 'source_api': 'https://nmisc-wf.gladata.com/api/',
                 'observation_category': 'totalizer'}


        location_obj = {'name': record['name'],
                'description': '4Test No Description',
                'location': loc,
                'properties': props,
                "encodingType": "application/vnd.geo+json", }




        obj = {'name': 'Totalizer Monitoring System',
                'description': 'ISC Totalizer Observations',
                'properties': props,
                'Locations': [location_obj],
                'Datastreams': [datastream_obj_rateKWH,
                                datastream_obj_srfVolumeKWH,
                                datastream_obj_nmiscVolumeKWH,
                                datastream_obj_otherVolumeKWH
                               ]
              }


        x = requests.post(config["destination_path"], json=obj)



        #Unindent return to cycle through all locations
        return







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


        for message in input_messages:
           
            if message.type == Type.RECORD:
                data = message.record.data
                stream = message.record.stream


                print ("\n==============")
                print ("data")
                print (data)
                print ("stream")
                print (stream)


                print ("config")
                print (config)
                print ("\n==============")
                #print (config["destination_path"])
                #print (config['agency'])
                print ("\n==============")
                print ("\n==============")



                loc = make_geometry_point_from_latlon(data['latitude'], data['longitude'])

                props = {'source_id': data['id'],
                         'agency': config['agency'],
                         'source_api': config['source_api'],
                         'observation_category': config['observation_category']}


                location_obj = {'name': data['name'],
                        'description': 'Airbyte ST Destination Test8 - No Description',
                        'location': loc,
                        'properties': props,
                        "encodingType": "application/vnd.geo+json", }


                obj = {'name': config['name'],
                       'description': config['description'],
                       'properties': props,
                       'Locations': [location_obj]
                       #'Locations': [location_obj],
                       #'Datastreams': [datastream_obj_rate,
                       #                datastream_obj_srfVolume,
                       #                datastream_obj_nmiscVolume,
                       #                datastream_obj_otherVolume
                       #               ]
                      }


                x = requests.post(config["destination_path"], json=obj)



        #get_location_data()

        #pass




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
            # TODO
            print ("\n==============")
            print ("check config")
            print (config)
            print ("\n==============")


            #x = requests.request("CONNECT", URL)
            x = requests.request("CONNECT", config["destination_path"])



            return AirbyteConnectionStatus(status=Status.SUCCEEDED)
        except Exception as e:
            return AirbyteConnectionStatus(status=Status.FAILED, message=f"An exception occurred: {repr(e)}")
