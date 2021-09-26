import boto3
import os
import json
import base64
import uuid
import requests

s3 = boto3.resource('s3')
bucket_name = os.environ['BUCKET_NAME']
test_string = ['.jpeg', '.png', '.jpg', '.bmp']


def get_as_base64(url):
    return base64.b64encode(requests.get(url).content)
    print(requests.get(url).content)


def main(event, context):
    if event['httpMethod'] == 'PUT':
        authUsr = event['headers']['Authorization']
        jwtSplitted = authUsr.split('.')
        usrInfo = base64.b64decode((jwtSplitted[1] + "========").encode("ascii"))
        objUsr = json.loads(usrInfo.decode("ascii"))

        for item in json.loads(event['body'])['images']:

            imageData = item['image']
            imageName = str(uuid.uuid4()) + '-' + '_' + objUsr['cognito:username'] + '_' + '.' + \
                        item['mime'].split('/')[1]

            if 'http' in imageData:
                if any(x in imageData for x in test_string):
                    imageData = get_as_base64(imageData)

            obj = s3.Object(bucket_name, imageName)
            obj.put(Body=base64.b64decode(imageData))
            # get bucket location
            location = boto3.client('s3').get_bucket_location(Bucket=bucket_name)['LocationConstraint']
            # get object url
            object_url = "https://%s.s3-%s.amazonaws.com/%s" % (bucket_name, location, imageName)
            print(object_url)
        respuesta = {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({
                "message": "Images uploaded correctly"
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