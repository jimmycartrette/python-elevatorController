import requests
import os
import azure.functions as func
import azure.durable_functions as df


def main(mytimer: func.TimerRequest) -> None:
    url = os.environ['ELEVATORSTARTERURL']
    r = requests.get(url)
