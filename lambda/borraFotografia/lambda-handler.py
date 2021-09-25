import boto3
import os
import json


def main(event, context):
    respuesta = {
        "statusCode": 200,
        "headers": {},
        "body": json.dumps({
            "message": "This is sparta"
        })
    }
    return respuesta