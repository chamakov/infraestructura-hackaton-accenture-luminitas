import boto3
import os
import json
import requests
from requests_aws4auth import AWS4Auth

s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')
dynamodb = boto3.client('dynamodb')

region='us-east-1'
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)


def main(event, context):
    print(event)
    bucket_name = (os.environ['BUCKET_NAME'])
    key = event['Records'][0]['s3']['object']['key']
    image = {
        'S3Object': {
            'Bucket': bucket_name,
            'Name': key
        }
    }

    try:
        # Calls Amazon Rekognition DetectLabels API to classify images in S3
        response = rekognition.detect_labels(Image=image, MaxLabels=10, MinConfidence=70)

        # Print response to console, visible via CloudWatch logs
        print(key, response["Labels"])

        # Write results to JSON file in bucket results folder
        json_labels = json.dumps(response["Labels"])
        filename = os.path.basename(key)
        filename_prefix = os.path.splitext(filename)[0]
        obj = s3.put_object(Body=json_labels, Bucket=bucket_name, Key="results/" + filename_prefix + ".json")

        # Parse the JSON for DynamoDB
        db_result = []
        db_labels = json.loads(json_labels)
        for label in db_labels:
            db_result.append(label["Name"])

        # Write results to DynamoDB
        dynamodb.put_item(TableName=(os.environ['TABLE_NAME']),
                          Item={
                              'image_name': {'S': key},
                              'labels': {'S': str(db_result)},
                              'owner': {'S': key.split('_')[1]}
                          }
                          )

        indexInformation = {
            'image_name': key,
            'labels': db_result,
            'owner': key.split('_')[1]
        }

        indexInfoObj = json.dumps(indexInformation)

        r = requests.post('https://' + os.environ['ELASTIC_SEARCH'] + '/images/_doc', json=indexInformation, auth=awsauth)

        if r.status_code >= 400:
            raise ValueError('Ocurrio un error al mandar la informacion a elasticsearch')

        return response

    except Exception as e:
        print(e)
        print("Error processing object {} from bucket {}. ".format(key, bucket_name))
        raise e