import logging
from random import randint, random
from typing import Sequence
from azure import functions
from azure.messaging.webpubsubservice import WebPubSubServiceClient
from azure.core.credentials import AzureKeyCredential
from collections import namedtuple
import azure.cosmos.cosmos_client as cosmos_client
import azure.cosmos.exceptions as exceptions
import enum
import os

from elevatorRunner import NUMBER_OF_FLOORS

COSHOST = os.environ['COSHOST']
COSMASTER_KEY = os.environ['COSMASTER_KEY']
COSDATABASE_ID = os.environ['COSDATABASE_ID']


class ElevatorDirection(enum.IntEnum):
    UP = 1
    DOWN = 2,
    NONE = 3


class ElevatorStatus(enum.IntEnum):
    MOVING = 1
    ATFLOOR = 2,
    DOORSOPENING = 3,
    DOORSCLOSING = 4


class ElevatorState:
    def __init__(self, atFloor: int, floorQueue: list, id: str, elevatorStatus: ElevatorStatus, elevatorDirection: ElevatorDirection):
        self.atFloor = atFloor
        self.floorQueue = floorQueue
        self.id = id
        self.elevatorNumber = id
        self.elevatorStatus = elevatorStatus
        self.elevatorDirection = elevatorDirection


def main(req: functions.HttpRequest) -> functions.HttpResponse:
    elevator_id = req.params.get('id')
    number_of_floors = int(req.params.get('numberOfFloors'))
    changed = False
    client = cosmos_client.CosmosClient(COSHOST, {'masterKey': COSMASTER_KEY})
    elevators_db = client.get_database_client(database=COSDATABASE_ID)
    elevators_container = elevators_db.get_container_client(
        container="elevator")

    try:
        elevator_status = elevators_container.read_item(
            item=str(elevator_id), partition_key=str(elevator_id))
    except Exception as e:
        logging.warning("elevator "+str(elevator_id)+" not found")
        elevator_status = {}
        elevator_status['atFloor'] = 1
        elevator_status['floorQueue'] = []
        elevator_status['id'] = str(elevator_id)
        elevator_status['elevatorStatus'] = ElevatorStatus.ATFLOOR
        elevator_status['elevatorDirection'] = ElevatorDirection.NONE
        changed = True

    elevator_status['elevatorNumber'] = int(elevator_id)
    create_queue = randint(0, 9)
    random_floor = randint(1, number_of_floors)

    if create_queue == 4 and random_floor not in elevator_status['floorQueue']:
        elevator_status['floorQueue'].append(random_floor)
        changed = True
    if elevator_status['atFloor']:
        original_at_floor = elevator_status['atFloor']
    if elevator_status['elevatorStatus'] == ElevatorStatus.DOORSCLOSING:
        elevator_status['elevatorStatus'] = ElevatorStatus.ATFLOOR
        changed = True
    elif elevator_status['elevatorStatus'] == ElevatorStatus.DOORSOPENING:
        elevator_status['elevatorStatus'] = ElevatorStatus.DOORSCLOSING
        changed = True
    elif elevator_status['atFloor'] in elevator_status['floorQueue']:
        changed = True
        elevator_status['elevatorStatus'] = ElevatorStatus.DOORSOPENING
        elevator_status['floorQueue'].remove(elevator_status['atFloor'])
        if not elevator_status['floorQueue']:
            elevator_status['elevatorDirection'] = ElevatorDirection.NONE
    elif elevator_status['floorQueue']:
        changed = True
        elevator_status['elevatorStatus'] = ElevatorStatus.MOVING
        # if elevator_status['atFloor'] == NUMBER_OF_FLOORS:
        #     elevator_status['elevatorDirection'] = ElevatorDirection.DOWN
        #     find_closest_floor(elevator_status)
        # elif elevator_status['atFloor'] == 1:
        #     elevator_status['elevatorDirection'] = ElevatorDirection.UP
        #     find_closest_floor(elevator_status)

        if elevator_status['elevatorDirection'] == ElevatorDirection.NONE:
            find_closest_floor(elevator_status)
        elif elevator_status['elevatorDirection'] == ElevatorDirection.UP:
            filtered_floor = filter(
                lambda floor: floor > elevator_status['atFloor'],                                                     elevator_status['floorQueue'])
            list_filtered_floor = list(filtered_floor)
            list_filtered_floor.sort(reverse=True)
            if list_filtered_floor == None or len(list_filtered_floor) == 0:
                elevator_status['atFloor'] -= 1
                elevator_status['elevatorDirection'] = ElevatorDirection.DOWN
            else:
                elevator_status['atFloor'] += 1
        elif elevator_status['elevatorDirection'] == ElevatorDirection.DOWN:
            filtered_floor = filter(
                lambda floor: floor < elevator_status['atFloor'],                                                     elevator_status['floorQueue'])
            list_filtered_floor = list(filtered_floor)
            list_filtered_floor.sort()
            if list_filtered_floor == None or len(list_filtered_floor) == 0:
                elevator_status['atFloor'] += 1
                elevator_status['elevatorDirection'] = ElevatorDirection.UP
            else:
                elevator_status['atFloor'] -= 1

        # if "atFloor" in elevator_status and priqueue['toFloor'] == elevator_status['atFloor']:
        #     elevator_status['elevatorDirection'] = ElevatorDirection.NONE
        #     elevator_status['elevatorStatus'] = ElevatorStatus.DOORSOPENING
        #     elevator_status['primaryElevatorQueue'] = elevator_status['secondaryElevatorQueue']
        #     elevator_status['secondaryElevatorQueue'] = {}
        # elif priqueue['toFloor'] > elevator_status['atFloor']:
        #     elevator_status['elevatorStatus'] = ElevatorStatus.MOVING
        #     elevator_status['elevatorDirection'] = ElevatorDirection.UP
        #     elevator_status['atFloor'] = elevator_status['atFloor']+1
        # elif priqueue['toFloor'] < elevator_status['atFloor']:
        #     elevator_status['elevatorStatus'] = ElevatorStatus.MOVING
        #     elevator_status['elevatorDirection'] = ElevatorDirection.DOWN
        #     elevator_status['atFloor'] = elevator_status['atFloor']-1

    if changed == True:
        elevator_doors_status = []
        for x in range(1, number_of_floors+1):
            adddoor = {'elevatorShaftNumber': int(elevator_id), 'floor': x,
                       'open': True if elevator_status['elevatorStatus'] == ElevatorStatus.DOORSOPENING and x == elevator_status['atFloor'] else False,
                       'elevatorAtFloor': original_at_floor,
                       'elevatorDirection': elevator_status['elevatorDirection']}
            elevator_doors_status.append(adddoor)
        elevators_container.upsert_item(body=elevator_status)
        service = WebPubSubServiceClient(endpoint='https://crazyelevator.webpubsub.azure.com',
                                         hub='elevator', credential=AzureKeyCredential("sx3EtHYQQxPZiAZuHYDiEkDCflnI24Q00M7MJmCCg1k="))
        service.send_to_all(
            message={'elevatorUpdate': elevator_status, 'doorsUpdate': elevator_doors_status})
    return functions.HttpResponse("whatever")


def find_closest_floor(elevator_status):
    next_floor = elevator_status['floorQueue'][min(range(len(elevator_status['floorQueue'])), key=lambda i: abs(
        elevator_status['floorQueue'][i]-elevator_status['atFloor']))]
    if next_floor > elevator_status['atFloor']:
        elevator_status['atFloor'] += 1
        elevator_status['elevatorDirection'] = ElevatorDirection.UP
    else:
        elevator_status['atFloor'] -= 1
        elevator_status['elevatorDirection'] = ElevatorDirection.DOWN

# cause deploy
