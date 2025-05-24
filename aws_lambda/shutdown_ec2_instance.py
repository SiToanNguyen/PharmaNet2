# Run this script to check if the shutdown timer has passed. If it has, stop the EC2 instance.

import boto3 # type: ignore
import datetime
from datetime import timezone
import json
import os

# CONFIGURATION
BUCKET_NAME = os.environ["BUCKET_NAME"]
TIMER_OBJECT_KEY = os.environ["TIMER_OBJECT_KEY"]
INSTANCE_ID = os.environ["INSTANCE_ID"]
REGION = os.environ["REGION"]

# Connect to AWS services
s3 = boto3.client('s3')
ec2 = boto3.client('ec2', region_name=REGION)

def get_shutdown_time():
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=TIMER_OBJECT_KEY)
        data = json.loads(response['Body'].read())
        return datetime.datetime.fromisoformat(data['shutdown_at'].replace('Z', '+00:00'))
    except Exception as e:
        print("Failed to read shutdown timer:", e)
        return None

def stop_instance():
    print(f"Stopping instance {INSTANCE_ID}...")
    ec2.stop_instances(InstanceIds=[INSTANCE_ID])

def get_instance_state():
    try:
        response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
        instance = response['Reservations'][0]['Instances'][0]
        return instance['State']['Name']
    except Exception as e:
        print("Error fetching instance state:", e)
        return None

def lambda_handler(event, context):
    # If server already stopped, do nothing
    state = get_instance_state()
    if state != 'running':
        print(f"Instance {INSTANCE_ID} is not running (state: {state}). No action taken.")
        return {"Status": "instance not running"}
    
    now = datetime.datetime.now(timezone.utc)
    shutdown_at = get_shutdown_time()

    # Check if the shutdown timer has passed. If it has, stop the EC2 instance.
    if shutdown_at and now > shutdown_at:
        print("Shutdown time has passed.")
        stop_instance()
        return {"Status": "shutdown due to timeout."}

    return {"Status": "connection active, no action taken."}