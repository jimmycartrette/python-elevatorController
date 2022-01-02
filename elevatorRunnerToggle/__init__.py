import logging
import requests
import os
import json
import adal
import azure.functions as func

tenant = os.environ['TENANT']
authority_url = 'https://login.microsoftonline.com/' + tenant
client_id = os.environ['CLIENTID']
client_secret = os.environ['CLIENTSECRET']
resource = 'https://management.azure.com/'
subscription = os.environ['SUBSCRIPTION']
resourcegroup = os.environ['RESOURCEGROUP']
functionappname = os.environ['FUNCTIONAPPNAME']
functiontotoggle = os.environ['FUNCTIONTOTOGGLE']


def main(req: func.HttpRequest) -> func.HttpResponse:
    action = req.params.get('action')
    logging.info("received request for "+action)
    validActions = ['enable', 'disable', 'status']
    if action == None or action not in validActions:
        return "no action specified"

    context = adal.AuthenticationContext(authority_url)
    token = context.acquire_token_with_client_credentials(
        resource, client_id, client_secret)
    headers = {'Authorization': 'Bearer ' +
               token['accessToken'], 'Content-Type': 'application/json'}
    listurl = 'https://management.azure.com/subscriptions/'+subscription+'/resourceGroups/'+resourcegroup + \
        '/providers/Microsoft.Web/sites/'+functionappname + \
        '/config/appsettings/list?api-version=2019-08-01'
    puturl = 'https://management.azure.com/subscriptions/'+subscription+'/resourceGroups/'+resourcegroup + \
        '/providers/Microsoft.Web/sites/'+functionappname + \
        '/config/appsettings?api-version=2019-08-01'
    r = requests.post(listurl, headers=headers)
    if action == 'status':
        status = r.json()['properties']['AzureWebJobs.' +
                                        functiontotoggle+'.Disabled']
        statusreturn = {'enabled': True if status == '0' else False}
        return json.dumps(statusreturn, indent=4, separators=(',', ': '))

    currentsettings = r.json()['properties']
    updaterequestbody = {}
    updaterequestbody['type'] = 'functionapp'
    updaterequestbody['properties'] = currentsettings
    updaterequestbody['properties']['AzureWebJobs.' +
                                    functiontotoggle+'.Disabled'] = 1 if action == 'disable' else 0
    r = requests.put(puturl, data=json.dumps(
        updaterequestbody), headers=headers)
    return json.dumps(r.json(), indent=4, separators=(',', ': '))
