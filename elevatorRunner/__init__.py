from random import randint, random
import enum
import logging
import math
import requests
import os
from azure.messaging.webpubsubservice import WebPubSubServiceClient
from azure.core.credentials import AzureKeyCredential
import azure.functions as func
import azure.durable_functions as df
import azure.cosmos.cosmos_client as cosmos_client
import azure.cosmos.exceptions as exceptions

COSHOST = os.environ['COSHOST']
COSMASTER_KEY = os.environ['COSMASTER_KEY']
COSDATABASE_ID = os.environ['COSDATABASE_ID']
ELEVATORPYTHONACTOR = os.environ['ELEVATORPYTHONACTOR']
NUMBER_OF_ELEVATORS = 4
NUMBER_OF_FLOORS = 6


class ElevatorDirection(enum.IntEnum):
    UP = 1
    DOWN = 2


class ElevatorStatus(enum.IntEnum):
    MOVING = 1
    ATFLOOR = 2


def main(mytimer: func.TimerRequest) -> None:
    for e in range(1, NUMBER_OF_ELEVATORS+1):
        try:
            nothing = requests.get(ELEVATORPYTHONACTOR+"?id="+str(e) +
                                   "&numberOfFloors="+str(NUMBER_OF_FLOORS), timeout=0.0000000001)
        except requests.exceptions.ReadTimeout:
            pass
