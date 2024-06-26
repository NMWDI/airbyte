#
# Copyright (c) 2021 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from source_ose_realtime import SourceOseRealtime

if __name__ == "__main__":
    source = SourceOseRealtime()
    launch(source, sys.argv[1:])
