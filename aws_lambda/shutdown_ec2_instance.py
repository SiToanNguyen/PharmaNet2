# Run this script to
# 1. Check if the shutdown timer has passed. If it has, stop the EC2 instance.
# 2. Check if there is any active connection to the app on the EC2 instance.
# 3. If there is no active connection, update the shutdown timer to 2 minutes from now.

import boto3 # type: ignore
import datetime
from datetime import timezone
import json
import socket
import os

# CONFIGURATION
BUCKET_NAME = os.environ["BUCKET_NAME"]
TIMER_OBJECT_KEY = os.environ["TIMER_OBJECT_KEY"]
INSTANCE_ID = os.environ["INSTANCE_ID"]
REGION = os.environ["REGION"]
PORT = os.environ["PORT"]

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
    except (socket.timeout, socket.error):
        return False

def get_instance_info():
    try:
        response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
        instance = response['Reservations'][0]['Instances'][0]
        state = instance['State']['Name']
        public_ip = instance.get('PublicIpAddress')
        return state, public_ip
    except Exception as e:
        print("Error fetching instance info:", e)
        return None, None

def stop_instance():
    print(f"Stopping instance {INSTANCE_ID}...")
    ec2.stop_instances(InstanceIds=[INSTANCE_ID])

def lambda_handler(event, context):
    # If server already stopped, do nothing
    instance_state, public_ip = get_instance_info()
    if instance_state != 'running':
        print(f"Instance {INSTANCE_ID} is not running (state: {instance_state}). No action taken.")
        return {"Status": "instance not running"}
    
    now = datetime.datetime.now(timezone.utc)
    shutdown_at = get_shutdown_time()

    # 1. Check if the shutdown timer has passed. If it has, stop the EC2 instance.
    if shutdown_at and now > shutdown_at:
        print("Shutdown time has passed.")
        stop_instance()
        return {"Status": "shutdown due to timeout."}

    # 2. Check if there is any active connection to the app on the EC2 instance.
    if public_ip and not is_port_open(public_ip, PORT):
        print("No active connection to app.")
        # 3. If there is no active connection, update the shutdown timer to 2 minutes from now.
        new_shutdown_time = now + datetime.timedelta(minutes=2)
        update_shutdown_timer(new_shutdown_time)
        return {"Status": "shutting down due to no active connection."}

    # Still active connection, do nothing
    return {"Status": "connection active, no action taken."}