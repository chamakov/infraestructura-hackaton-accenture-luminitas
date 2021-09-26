import boto3
import os
import json
import base64
from requests_aws4auth import AWS4Auth
import requests
from botocore.exceptions import ClientError

region = 'us-east-1'
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
s3_client = boto3.client('s3')


def main(event, context):
    if event['httpMethod'] == 'GET':
        r = requests.get('https://' + os.environ['ELASTIC_SEARCH'] + '/images/_search', auth=awsauth)

        if r.status_code >= 400:
            raise ValueError('Ocurrio un error al mandar la informacion a elasticsearch')

        data = r.json()

        print(data)

        hits = data['hits']['hits']

        body = []

        for image in hits:
            try:
                response = s3_client.generate_presigned_url('get_object',
                                                            Params={'Bucket': os.environ['BUCKET_NAME'],
                                                                    'Key': image['_source']['image_name']},
                                                            ExpiresIn=3600)
            except ClientError as e:
                raise ('Hubo un error al generar la URL para el archivo')

            presignedUrl = response

            imagen = {
                'id': image['_id'],
                'url': presignedUrl,
                'labels': image['_source']['labels'],
                'owner': image['_source']['owner']
            }

            body.append(imagen.copy())

            bodyJson = []
            for data in body:
                bodyJson.append(json.dumps(data))

            print(bodyJson)

        respuesta = {
            "statusCode": 200,
            "headers": {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*'
            },
            "body": json.dumps({"images": body}, indent=4)
        }
    else:
        respuesta = {
            "statusCode": 405,
            "headers": {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*'
            },
            "body": json.dumps({
                "message": "Method Not Supported"
            })
        }

    return respuesta