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
import urllib.request
import urllib.error

REGION = 'eu-north-1'
INSTANCE_ID = "i-0ae4c005f434d09bb"
PORT = 8000

ec2 = boto3.client("ec2", region_name=REGION)
ssm = boto3.client("ssm", region_name=REGION)
s3 = boto3.client('s3')

def initialize_shutdown_timer():
    shutdown_time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)).isoformat().replace('+00:00', 'Z')
    s3.put_object(
        Bucket='pharmanet-shutdown-bucket',
        Key='shutdown_timer.json',
        Body=json.dumps({'shutdown_at': shutdown_time}),
        ContentType='application/json'
    )
    print(f"Server will shut down at {shutdown_time}")

def get_public_ip(INSTANCE_ID):
    reservations = ec2.describe_instances(InstanceIds=[INSTANCE_ID])['Reservations']
    instance = reservations[0]['Instances'][0]
    return instance['PublicIpAddress']

def wait_for_django_server(ip, port=8000, timeout=150, interval=5):
    url = f"http://{ip}:{port}"
    print(f"Waiting for Django server at {url} to be ready...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    print("Django server is ready.")
                    return True
        except urllib.error.URLError:
            pass
        time.sleep(interval)
    print("Django server did not respond in time.")
    return False

def lambda_handler(event, context):
    # 1. Start an EC2 instance.
    ec2.start_instances(InstanceIds=[INSTANCE_ID])
    print("Starting EC2 instance...")

    # Wait until the instance is running
    waiter = ec2.get_waiter("instance_running")
    waiter.wait(InstanceIds=[INSTANCE_ID])
    print("EC2 instance is running.")

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
    print(f"Server is available at http://{ip}:{PORT}")
    
    commands = [
        "pkill gunicorn || true",
        "cd /home/ubuntu/PharmaNet2",
        ". /home/ubuntu/PharmaNet2/venv/bin/activate",
        "export DJANGO_ENV=production",

        # 3. Add the public IP to the Django settings for ALLOWED_HOSTS
        f'sed -i -E "s/^ALLOWED_HOSTS=.*/ALLOWED_HOSTS=\\"{ip}\\"/" .env.production',

        # 4. Start a Django Gunicorn server on the instance.
        (
            "nohup /home/ubuntu/PharmaNet2/venv/bin/gunicorn "
            "--bind 0.0.0.0:8000 pharmacy_management.wsgi:application "
            "> /home/ubuntu/PharmaNet2/gunicorn.log 2>&1 &"
        )
    ]

    time.sleep(5)  # Optional: small delay to ensure stability

    response = ssm.send_command(
        InstanceIds=[INSTANCE_ID],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": commands},
    )

    # 5. Set a shutdown timer for the server to stop after 2 hours.
    print("Shutdown timer updated.")
    initialize_shutdown_timer()    

    print("Command sent:", response["Command"]["CommandId"])
    
    # Wait for Django to respond before finishing
    if not wait_for_django_server(ip, PORT):
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "Django server failed to start in time.",
                "public_ip": ip,
                "url": f"http://{ip}:{PORT}"
            })
        }

    return {
        "status": "EC2 instance started and Django server launching.",
        "public_ip": ip,
        "url": f"http://{ip}:{PORT}"
    }