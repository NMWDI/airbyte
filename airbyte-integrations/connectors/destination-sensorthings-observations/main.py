#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


import sys

from destination_sensorthings_observations import DestinationSensorthingsObservations

if __name__ == "__main__":
    DestinationSensorthingsObservations().run(sys.argv[1:])
