import logging
from random import randint, random
from typing import Sequence
from azure import functions
from azure.messaging.webpubsubservice import WebPubSubServiceClient
from azure.core.credentials import AzureKeyCredential
import azure.cosmos.cosmos_client as cosmos_client
import azure.cosmos.exceptions as exceptions
import enum
import os

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
    def __init__(self, atFloor: int, primaryElevatorQueue: object, secondaryElevatorQueue: object, id: str, elevatorStatus: ElevatorStatus, elevatorDirection: ElevatorDirection):
        self.atFloor = atFloor
        self.primaryElevatorQueue = primaryElevatorQueue
        self.secondaryElevatorQueue = secondaryElevatorQueue
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
        elevator_status['elevatorNumber'] = int(elevator_id)
    except Exception as e:
        logging.warning("elevator "+str(elevator_id)+" not found")

        elevator_status = ElevatorState(1, {}, {}, str(
            elevator_id), ElevatorStatus.ATFLOOR, ElevatorDirection.NONE)
        changed = True

    priqueue = elevator_status['primaryElevatorQueue']
    secqueue = elevator_status['secondaryElevatorQueue']
    create_queue = randint(0, 9)
    random_floor = randint(1, number_of_floors)

    if create_queue == 4 and elevator_status['atFloor'] != random_floor:
        if "toFloor" not in priqueue:
            elevator_status['primaryElevatorQueue'] = {
                'toFloor': random_floor}
            changed = True
        elif "toFloor" not in secqueue:
            elevator_status['secondaryElevatorQueue'] = {
                'toFloor': random_floor}
            changed = True
    original_at_floor = elevator_status['atFloor']
    if elevator_status['elevatorStatus'] == ElevatorStatus.DOORSOPENING:
        elevator_status['elevatorStatus'] = ElevatorStatus.DOORSCLOSING
        changed = True
    elif priqueue != None and "toFloor" in priqueue:
        changed = True
        if "atFloor" in elevator_status and priqueue['toFloor'] == elevator_status['atFloor']:
            elevator_status['elevatorDirection'] = ElevatorDirection.NONE
            elevator_status['elevatorStatus'] = ElevatorStatus.DOORSOPENING
            elevator_status['primaryElevatorQueue'] = elevator_status['secondaryElevatorQueue']
            elevator_status['secondaryElevatorQueue'] = {}
        elif priqueue['toFloor'] > elevator_status['atFloor']:
            elevator_status['elevatorStatus'] = ElevatorStatus.MOVING
            elevator_status['elevatorDirection'] = ElevatorDirection.UP
            elevator_status['atFloor'] = elevator_status['atFloor']+1
        elif priqueue['toFloor'] < elevator_status['atFloor']:
            elevator_status['elevatorStatus'] = ElevatorStatus.MOVING
            elevator_status['elevatorDirection'] = ElevatorDirection.DOWN
            elevator_status['atFloor'] = elevator_status['atFloor']-1

    elevator_doors_status = []
    for x in range(1, number_of_floors+1):
        adddoor = {'elevatorShaftNumber': int(elevator_id), 'floor': x,
                   'open': True if elevator_status['elevatorStatus'] == ElevatorStatus.DOORSOPENING and x == elevator_status['atFloor'] else False,
                   'elevatorAtFloor': original_at_floor,
                   'elevatorDirection': elevator_status['elevatorDirection']}
        elevator_doors_status.append(adddoor)

    if changed == True:
        elevators_container.upsert_item(body=elevator_status)
        service = WebPubSubServiceClient(endpoint='https://crazyelevator.webpubsub.azure.com',
                                         hub='elevator', credential=AzureKeyCredential("sx3EtHYQQxPZiAZuHYDiEkDCflnI24Q00M7MJmCCg1k="))
        service.send_to_all(
            message={'elevatorUpdate': elevator_status, 'doorsUpdate': elevator_doors_status})
    return functions.HttpResponse("whatever")

# cause deploy
