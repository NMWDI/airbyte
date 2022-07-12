#
# Copyright (c) 2021 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from source_nmbgmr_minor_and_trace_chemistry import SourceNmbgmrMinorAndTraceChemistry

if __name__ == "__main__":
    source = SourceNmbgmrMinorAndTraceChemistry()
    launch(source, sys.argv[1:])
