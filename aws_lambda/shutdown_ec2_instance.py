# Run this script to
# 1. Check if the shutdown timer has passed. If it has, stop the EC2 instance.
# 2. Check if there is any active connection to the app on the EC2 instance.
# 3. If there is no active connection, update the shutdown timer to 2 minutes from now.

import boto3 # type: ignore
import datetime
from datetime import timezone
import json
import socket

# CONFIGURATION
BUCKET_NAME = 'pharmanet-shutdown-bucket'
TIMER_OBJECT_KEY = 'shutdown_timer.json'
EC2_INSTANCE_ID = 'i-0ae4c005f434d09bb'
EC2_REGION = 'eu-north-1'
EC2_PUBLIC_IP = '13.48.249.163'
APP_PORT = 8000

# Connect to AWS services
s3 = boto3.client('s3')
ec2 = boto3.client('ec2', region_name=EC2_REGION)

def get_shutdown_time():
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=TIMER_OBJECT_KEY)
        data = json.loads(response['Body'].read())
        return datetime.datetime.fromisoformat(data['shutdown_at'].replace('Z', '+00:00'))
    except Exception as e:
        print("Failed to read shutdown timer:", e)
        return None

def update_shutdown_timer(new_time):
    try:
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=TIMER_OBJECT_KEY,
            Body=json.dumps({'shutdown_at': new_time.isoformat().replace('+00:00', 'Z')}),
            ContentType='application/json'
        )
        print(f"Shutdown timer updated to {new_time.isoformat()}")
    except Exception as e:
        print("Failed to update shutdown timer:", e)

def is_port_open(host, port):
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except:
        return False

def stop_instance():
    print(f"Stopping instance {EC2_INSTANCE_ID}...")
    ec2.stop_instances(InstanceIds=[EC2_INSTANCE_ID])

def lambda_handler(event, context):
    now = datetime.datetime.now(timezone.utc)
    shutdown_at = get_shutdown_time()

    # 1. Check if the shutdown timer has passed. If it has, stop the EC2 instance.
    if shutdown_at and now > shutdown_at:
        print("Shutdown time has passed.")
        stop_instance()
        return {"status": "shutdown due to timeout"}

    # 2. Check if there is any active connection to the app on the EC2 instance.
    if not is_port_open(EC2_PUBLIC_IP, APP_PORT):
        print("No active connection to app.")
        # 3. If there is no active connection, update the shutdown timer to 2 minutes from now.
        new_shutdown_time = now + datetime.timedelta(minutes=2)
        update_shutdown_timer(new_shutdown_time)
        return {"status": "shutdown due to no active connection"}

    # Still active connection, do nothing
    return {"status": "connection active, no action taken"}