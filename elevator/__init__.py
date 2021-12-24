# This function is not intended to be invoked directly. Instead it will be
# triggered by an orchestrator function.
# Before running this sample, please:
# - create a Durable orchestration function
# - create a Durable HTTP starter function
# - add azure-functions-durable to requirements.txt
# - run pip install -r requirements.txt

import logging
from random import randint, random
from typing import Sequence
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
    DOWN = 2


class ElevatorStatus(enum.IntEnum):
    MOVING = 1
    ATFLOOR = 2,
    DOORSOPENING = 3,
    DOORSCLOSING = 4


def main(payload: object) -> str:
    elevator_id = payload['elevatorId']
    number_of_floors = payload['numberOfFloors']
    changed = False
    client = cosmos_client.CosmosClient(COSHOST, {'masterKey': COSMASTER_KEY})
    elevators_db = client.get_database_client(database="elevatorSystem")
    elevators_container = elevators_db.get_container_client(
        container="elevator")

    try:
        elevator_status = elevators_container.read_item(
            item=str(elevator_id), partition_key=str(elevator_id))
    except Exception as e:
        logging.warning("elevator "+str(elevator_id)+" not found")
        elevator_status = {'id': str(elevator_id), 'atFloor': 1,
                           'elevator_status': ElevatorStatus.ATFLOOR, 'primary_elevator_queue': {}, 'secondary_elevator_queue': {}}
        changed = True

    # elevators_door_query = "SELECT * FROM c WHERE c.open ==1"
    # elevator_doors_status = elevator_doors_container.query_items()

    priqueue = elevator_status['primary_elevator_queue']
    secqueue = elevator_status['secondary_elevator_queue']
    create_queue = randint(0, 9)
    random_floor = randint(1, number_of_floors)

    if create_queue == 4 and elevator_status['atFloor'] != random_floor:
        if "toFloor" not in priqueue:
            elevator_status['primary_elevator_queue'] = {
                'toFloor': random_floor}
            changed = True
        elif "toFloor" not in secqueue:
            elevator_status['secondary_elevator_queue'] = {
                'toFloor': random_floor}
            changed = True
    if elevator_status['elevator_status'] == ElevatorStatus.DOORSOPENING:
        elevator_status['elevator_status'] = ElevatorStatus.DOORSCLOSING
        changed = True
    elif priqueue != None and "toFloor" in priqueue:
        changed = True
        if "atFloor" in elevator_status and priqueue['toFloor'] == elevator_status['atFloor']:
            elevator_status['elevator_status'] = ElevatorStatus.DOORSOPENING
            elevator_status['primary_elevator_queue'] = elevator_status['secondary_elevator_queue']
            elevator_status['secondary_elevator_queue'] = {}
        elif priqueue['toFloor'] > elevator_status['atFloor']:
            elevator_status['elevator_status'] = ElevatorStatus.MOVING
            elevator_status['atFloor'] = elevator_status['atFloor']+1
        elif priqueue['toFloor'] < elevator_status['atFloor']:
            elevator_status['elevator_status'] = ElevatorStatus.MOVING
            elevator_status['atFloor'] = elevator_status['atFloor']-1

    elevator_doors_status = []
    for x in range(1, number_of_floors+1):
        adddoor = {'elevatorShaftNumber': elevator_id, 'floor': x,
                   'open': True if elevator_status['elevator_status'] == ElevatorStatus.DOORSOPENING and x == elevator_status['atFloor'] else False}
        elevator_doors_status.append(adddoor)

    if changed == True:
        elevators_container.upsert_item(body=elevator_status)
        service = WebPubSubServiceClient(endpoint='https://crazyelevator.webpubsub.azure.com',
                                         hub='elevator', credential=AzureKeyCredential("sx3EtHYQQxPZiAZuHYDiEkDCflnI24Q00M7MJmCCg1k="))
        service.send_to_all(
            message={'elevatorUpdate': elevator_status, 'doorsUpdate': elevator_doors_status})

    return elevator_status
