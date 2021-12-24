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
NUMBER_OF_ELEVATORS = 4
NUMBER_OF_FLOORS = 6


class ElevatorDirection(enum.IntEnum):
    UP = 1
    DOWN = 2


class ElevatorStatus(enum.IntEnum):
    MOVING = 1
    ATFLOOR = 2


def orchestrator_function(context: df.DurableOrchestrationContext):
    service = WebPubSubServiceClient(endpoint='https://crazyelevator.webpubsub.azure.com',
                                     hub='elevator', credential=AzureKeyCredential("sx3EtHYQQxPZiAZuHYDiEkDCflnI24Q00M7MJmCCg1k="))
    client = cosmos_client.CosmosClient(COSHOST, {'masterKey': COSMASTER_KEY})
    elevators_db = client.get_database_client(database="elevatorSystem")

    elevators_container = elevators_db.get_container_client(
        container="elevator")
    elevators_query = "SELECT * FROM c WHERE c.elevatorNumber<=" + \
        str(NUMBER_OF_ELEVATORS)
    # elevator_states = list(elevators_container.query_items(query=elevators_query, enable_cross_partition_query=True))
    elevator_door_states = []
    for i in range(NUMBER_OF_FLOORS*NUMBER_OF_ELEVATORS):
        elevator_door_states.append({"elevatorShaftNumber": i %
                                     NUMBER_OF_ELEVATORS+1, "floor": NUMBER_OF_FLOORS-math.floor(i/NUMBER_OF_ELEVATORS), "open": False, "key": i+3})
    # state = {"elevatorState": elevator_states,
    #         "elevatorDoorState": elevator_door_states}
    # randomElevatorFloorMove(service, elevators_container, elevator_states, state)
    for e in range(1, NUMBER_OF_ELEVATORS+1):
        payload = {'elevatorId': e, 'numberOfFloors': NUMBER_OF_FLOORS}
        yield context.call_activity('elevator', payload)
    return ["nothing"]


def randomElevatorFloorMove(service, elevators_container, elevator_states, state):
    which_elevator_index = randint(0, NUMBER_OF_ELEVATORS-1)
    whichfloor = randint(-1, 1)
    possible_new_floor = elevator_states[which_elevator_index]["atFloor"]+whichfloor
    if possible_new_floor != 0 and possible_new_floor <= NUMBER_OF_FLOORS:
        elevator_states[which_elevator_index]["atFloor"] = possible_new_floor
        service.send_to_all(message=state)
        logging.info('broadcast message')
        elevators_container.upsert_item(
            body=elevator_states[which_elevator_index])


main = df.Orchestrator.create(orchestrator_function)
