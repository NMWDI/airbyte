#
# Copyright (c) 2021 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from source_nmbgmr_major_chemistry import SourceNmbgmrMajorChemistry

if __name__ == "__main__":
    source = SourceNmbgmrMajorChemistry()
    launch(source, sys.argv[1:])
