
import json
import logging

import boto3
from blocklist import get_ips, add_ips, delete_ips
from config import BUCKET, FILE_PATH, KEY

s3_client = boto3.client('s3')

def lambda_handler(event, context):

    logging.info(f"Received event: path={event.get('path')}, method={event.get('httpMethod')}")
    
    try:
        s3_file = s3_client.get_object(Bucket=BUCKET, Key=KEY)
        s3_file_body = s3_file['Body'].read().decode('utf-8')

        with open(FILE_PATH, "w", encoding='utf-8') as f:
            f.write(s3_file_body)
        logging.info("File written locally.")

    except Exception as e:
        logging.error(f"Error accessing S3 or writing file: {e}")
        return {'statusCode': 500, 'body': json.dumps({'error': 'Internal server error'})}

    if event["path"] == "/blocklist":
        if event["httpMethod"] == "GET":
            queryStringParams = event.get("queryStringParameters")
            if queryStringParams is None:
                queryString = "false"
            else:
                queryString = queryStringParams.get("include_timestamp", "false")
            include_time = queryString.lower() == 'true'
            blocklist_ips = get_ips(include_timestamp=include_time)
            return {
                 'statusCode': 200,
                 'body': blocklist_ips,
                 "headers": {
                    "Content-Type": "text/plain"
                 }
             }
        
        elif event["httpMethod"] == "POST":
            request_body = json.loads(event.get('body', '[]'))
            result = add_ips(ip_list=request_body)
            return {
                'statusCode': 200,
                'body': json.dumps({'result': result})
            }

        elif event["httpMethod"] == "DELETE":
            request_body = json.loads(event.get('body', '[]'))
            result = delete_ips(ip_list=request_body)
            return {
                'statusCode': 200,
                'body': json.dumps({'result': result})
            }

    # Return a default response for unsupported paths
    logging.warning(f"No matching handler for {event['path']} {event['httpMethod']}")
    return {
        'statusCode': 404,
        'body': json.dumps({'error': 'No matching paths or methods'})
    }
