import boto3
import os
import json


def main(event, context):
    print(event)
    respuesta = {
        "statusCode": 200,
        "headers": {},
        "body": json.dumps({
            "message": "This is sparta"
        })
    }
    return respuesta