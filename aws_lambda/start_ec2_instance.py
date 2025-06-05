# Run this script to
# 1. Start an EC2 instance.
# 2. Get the public IP from the EC2 API to return it in the Lambda response.
# 3. Add the public IP to the Django settings for ALLOWED_HOSTS
# 4. Start a Django Gunicorn server on the instance.
# 5. Set a shutdown timer for the server to stop after 2 hours.

import boto3 # type: ignore
import time
import datetime
import json
import os

REGION = os.environ["REGION"]
INSTANCE_ID = os.environ["INSTANCE_ID"]
PORT = os.environ["PORT"]

ec2 = boto3.client("ec2", region_name=REGION)
ssm = boto3.client("ssm", region_name=REGION)
s3 = boto3.client('s3')

def initialize_shutdown_timer():
    shutdown_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2) # Will shut down in 2 hours
    shutdown_time = shutdown_dt.isoformat().replace('+00:00', 'Z')

    s3.put_object(
        Bucket='pharmanet-shutdown-bucket',
        Key='shutdown_timer.json',
        Body=json.dumps({'shutdown_at': shutdown_time}),
        ContentType='application/json'
    )

    readable_time = shutdown_dt.strftime('%A, %B %d, %Y at %I:%M %p UTC')
    print(f"Server will shut down on {readable_time}")
    return readable_time

def get_public_ip(instance_id):
    try:
        reservations = ec2.describe_instances(InstanceIds=[instance_id])['Reservations']
        instance = reservations[0]['Instances'][0]
        return instance['PublicIpAddress']
    except (KeyError, IndexError) as e:
        raise RuntimeError("Failed to retrieve public IP address") from e

def check_server_status(instance_id):
    # Check if Gunicorn is already running
    check_response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": ["pgrep -f gunicorn"]},
    )

    command_id = check_response["Command"]["CommandId"]

    # Wait for the command result
    for _ in range(10):  # Retry up to ~10 seconds
        time.sleep(1)
        output = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id,
        )
        if output["Status"] in ("Success", "Failed", "Cancelled", "TimedOut"):
            break

    # Determine if Gunicorn is running
    if output["Status"] == "Success" and output["StandardOutputContent"].strip():
        print("Gunicorn is already running. Skipping restart.")
        return True
    else:
        print("Gunicorn is not running. Will start the server.")
        return False

def lambda_handler(event, context):
    # Check current EC2 instance state
    response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
    current_state = response['Reservations'][0]['Instances'][0]['State']['Name']
    print(f"Current EC2 state: {current_state}")

    if current_state != 'running':
        # 1. Start an EC2 instance.
        ec2.start_instances(InstanceIds=[INSTANCE_ID])
        print("Starting EC2 instance...")

        # Wait until the instance is running
        waiter = ec2.get_waiter("instance_running")
        waiter.wait(InstanceIds=[INSTANCE_ID])
        print("EC2 instance is running.")
    else:
        print("EC2 instance already running.")

    # Wait until instance is online in SSM
    for i in range(30):
        response = ssm.describe_instance_information()
        instances = response.get("InstanceInformationList", [])
        if any(inst["InstanceId"] == INSTANCE_ID for inst in instances):
            print("Instance is ready in SSM.")
            break
        print("Waiting for SSM availability...")
        time.sleep(10)
    else:
        raise TimeoutError("SSM not ready after waiting.")

    # 2. Get the public IP from the EC2 API to return it in the Lambda response.
    ip = get_public_ip(INSTANCE_ID)
    print(f"EC2's Public IP: {ip}")

    print("Starting Django server...")
    duckdns_host = "pharmanet.duckdns.org"
    hosts = {duckdns_host, ip}
    allowed_hosts_value = ",".join(hosts)
    commands = [
        "pkill gunicorn || true",
        "cd /home/ubuntu/PharmaNet2 || exit 1",
        ". /home/ubuntu/PharmaNet2/venv/bin/activate",
        "export DJANGO_ENV=production",

        # 3. Add the public IP to the Django settings for ALLOWED_HOSTS
        f"sed -i -E \"s/^ALLOWED_HOSTS=.*/ALLOWED_HOSTS={allowed_hosts_value}/\" .env.production",

        # 4. Start a Django Gunicorn server on the instance.
        (
            "nohup /home/ubuntu/PharmaNet2/venv/bin/gunicorn "
            "--bind 0.0.0.0:8000 pharmacy_management.wsgi:application "
            "> /home/ubuntu/PharmaNet2/gunicorn.log 2>&1 &"
        )
    ]
    time.sleep(5)  # Small delay to ensure stability
    response = ssm.send_command(
        InstanceIds=[INSTANCE_ID],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": commands},
    )
    print("Django server is running.")
    print("Command sent:", response["Command"]["CommandId"])        

    print(f"Server is available at http://{ip}:{PORT}")

    # 5. Set a shutdown timer for the server to stop after 2 hours.    
    print("Shutdown timer updated.")
    shutdown_at_str = initialize_shutdown_timer()

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "status": "EC2 instance started and Django server launching.",
            "public_ip": ip,
            "url": f"http://{ip}:{PORT}",
            "shutdown_at": shutdown_at_str
        })
    }