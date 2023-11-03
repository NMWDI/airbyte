#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


from setuptools import find_packages, setup

MAIN_REQUIREMENTS = [
    "airbyte-cdk",
    "frost_sta_client",
    "google-cloud",
    "google.cloud.bigquery",
    "pandas"
]

TEST_REQUIREMENTS = [
        "pytest~=6.2",
        "pytest-mock~=3.6.1"
        ]

setup(
    name="destination_sensorthings_observations",
    description="Destination implementation for Sensorthings Observations.",
    author="Airbyte",
    author_email="contact@airbyte.io",
    packages=find_packages(),
    install_requires=MAIN_REQUIREMENTS,
    package_data={"": ["*.json"]},
    extras_require={
        "tests": TEST_REQUIREMENTS,
    },
)
