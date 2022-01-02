import os
import requests
import logging

import azure.functions as func


def main(mytimer: func.TimerRequest) -> None:
    turnoffurl = os.environ['TURNOFFELEVATORCONTROLLERURL']
    r = requests.get(turnoffurl)
    logging.info(r.text)

# make deploy
