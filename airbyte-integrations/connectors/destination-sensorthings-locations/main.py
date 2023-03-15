#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


import sys

from destination_sensorthings_locations import DestinationSensorthingsLocations

if __name__ == "__main__":
    DestinationSensorthingsLocations().run(sys.argv[1:])
