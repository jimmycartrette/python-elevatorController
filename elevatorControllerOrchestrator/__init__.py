# This function is not intended to be invoked directly. Instead it will be
# triggered by an HTTP starter function.
# Before running this sample, please:
# - create a Durable activity function (default name is "Hello")
# - create a Durable HTTP starter function
# - add azure-functions-durable to requirements.txt
# - run pip install -r requirements.txt
from random import randint, random
import enum
import logging
import math
import json
from azure.messaging.webpubsubservice import WebPubSubServiceClient
from azure.core.credentials import AzureKeyCredential
import azure.functions as func
import azure.durable_functions as df


class ElevatorDirection(enum.IntEnum):
    UP = 1
    DOWN = 2


class ElevatorStatus(enum.IntEnum):
    MOVING = 1
    ATFLOOR = 2


def orchestrator_function(context: df.DurableOrchestrationContext):
    service = WebPubSubServiceClient(endpoint='https://crazyelevator.webpubsub.azure.com',
                                     hub='elevator', credential=AzureKeyCredential("sx3EtHYQQxPZiAZuHYDiEkDCflnI24Q00M7MJmCCg1k="))

    elevatorStates = []
    for i in range(4):
        elevatorStates.append(
            {"elevatorNumber": i+1, "elevatorStatus": ElevatorStatus.ATFLOOR, "atFloor": 1, "key": i})
    elevatorDoorStates = []
    for i in range(6*4):
        elevatorDoorStates.append({"elevatorShaftNumber": i %
                                   4+1, "floor": 6-math.floor(i/4), "open": False, "key": i+3})
    state = {"elevatorState": elevatorStates,
             "elevatorDoorState": elevatorDoorStates}
    whichelevator = randint(1, 4)
    whichfloor = randint(1, 6)
    elevatorStates[whichelevator-1]["atFloor"] = whichfloor
    service.send_to_all(message=state)
    logging.info('broadcast message')
    # result1 = yield context.call_activity('elevator', "Tokyo")
    # result2 = yield context.call_activity('elevator', "Seattle")
    # result3 = yield context.call_activity('elevator', "London")
    return ["nothing"]


main = df.Orchestrator.create(orchestrator_function)
