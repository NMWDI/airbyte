#
# Copyright (c) 2021 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from source_hydrovu_jir import SourceHydrovuJir

if __name__ == "__main__":
    source = SourceHydrovuJir()
    launch(source, sys.argv[1:])
