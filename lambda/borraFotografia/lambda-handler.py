import boto3
import os
import json
from requests_aws4auth import AWS4Auth
import requests
import base64

region = 'us-east-1'
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
s3_client = boto3.client('s3')


def main(event, context):
    try:
        if event['httpMethod'] == 'DELETE':
            authUsr = event['headers']['Authorization']
            jwtSplitted = authUsr.split('.')
            usrInfo = base64.b64decode((jwtSplitted[1] + "========").encode("ascii"))
            objUsr = json.loads(usrInfo.decode("ascii"))
            print(objUsr['cognito:groups'])
            print(objUsr['cognito:username'])

            puedeBorrar = False

            if 'Admin-Group' in objUsr['cognito:groups']:
                puedeBorrar = True
            elif objUsr['cognito:username'].trim() == event['body']['owner']:
                puedeBorrar = True
            else:
                puedeBorrar = False

            print(puedeBorrar)

            if puedeBorrar:
                r = requests.delete('https://' + os.environ['ELASTIC_SEARCH'] + '/images/_doc/' + event['body']['id'],
                                    auth=awsauth)

                if r.status_code >= 400:
                    respuesta = {
                        "statusCode": r.status_code,
                        "headers": {
                            'Access-Control-Allow-Headers': '*',
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'GET'
                        },
                        "body": json.dumps({
                            "mensaje": r.content
                        })
                    }

                data = r.json()

                print(data)

            respuesta = {
                "statusCode": 200,
                "headers": {
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET'
                }
            }
        else:
            respuesta = {
                "statusCode": 405,
                "headers": {
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET'
                },
                "body": json.dumps({
                    "message": "Method Not Supported"
                })
            }


    except Exception as e:
        print(e)
        respuesta = {
            "statusCode": 501,
            "headers": {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET'
            },
            "body": json.dumps({
                "mensaje": "ocurrio un error al realizar la operacion"
            })
        }

    return respuesta