import boto3
import os
import json
import base64


def main(event, context):
    if event['httpMethod'] == 'GET':
        authUsr = event['headers']['Authorization']
        jwtSplitted = authUsr.split('.')
        usrInfo = base64.b64decode((jwtSplitted[1] + "========").encode("ascii"))
        objUsr = json.loads(usrInfo.decode("ascii"))
        print(objUsr)
        # Agregar logica para confirmar si el usuario esta en el grupo de administradores permitir borrar cualquier imagen
        print(objUsr['cognito:groups'])

        # obtener el ID del usuario de cognito
        print(objUsr['cognito:username'])

        respuesta = {
            "statusCode": 200,
            "headers": {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET'
            },
            "body": json.dumps({
                "message": "all ok"
            })
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

    return respuesta