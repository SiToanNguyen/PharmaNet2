# Run this script to
# 1. Start an EC2 instance.
# 2. Gets the instance’s own public IP from AWS metadata and add to the Django settings for ALLOWED_HOSTS
# 3. Start a Django Gunicorn server on the instance.
# 4. Set a shutdown timer for the server to stop after 2 hours.
# 5. Gets the public IP from the EC2 API to return it in the Lambda response.
# 6. Open the server URL in a web browser.

# Note: This script runs on AWS Lambda, which includes boto3 by default.
# You may see an import error in your IDE, but it will work correctly on AWS.

import boto3 # type: ignore
import time
import datetime
import json
import webbrowser

region = "eu-north-1"
instance_id = "i-0ae4c005f434d09bb"
REGION = 'eu-north-1'
PORT = 8000

ec2 = boto3.client("ec2", region_name=region)
ssm = boto3.client("ssm", region_name=region)
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

def get_public_ip(instance_id):
    reservations = ec2.describe_instances(InstanceIds=[instance_id])['Reservations']
    instance = reservations[0]['Instances'][0]
    return instance['PublicIpAddress']

def lambda_handler(event, context):
    # 1. Start an EC2 instance.
    ec2.start_instances(InstanceIds=[instance_id])
    print("Starting EC2 instance...")

    # Wait until the instance is running
    waiter = ec2.get_waiter("instance_running")
    waiter.wait(InstanceIds=[instance_id])
    print("EC2 instance is running.")

    # Wait until instance is online in SSM
    for i in range(30):
        response = ssm.describe_instance_information()
        instances = response.get("InstanceInformationList", [])
        if any(inst["InstanceId"] == instance_id for inst in instances):
            print("Instance is ready in SSM.")
            break
        print("Waiting for SSM availability...")
        time.sleep(10)
    else:
        raise TimeoutError("SSM not ready after waiting.")

    commands = [
        "pkill gunicorn || true",
        "cd /home/ubuntu/PharmaNet2",
        ". /home/ubuntu/PharmaNet2/venv/bin/activate",
        "export DJANGO_ENV=production",

        # 2. Gets the instance’s own public IP from AWS metadata and add to the Django settings for ALLOWED_HOSTS
        "PUBLIC_IP=$(curl -s --retry 5 --retry-delay 2 http://169.254.169.254/latest/meta-data/public-ipv4)",
        "echo \"Public IP is: $PUBLIC_IP\"",
        "sed -i -E \"s/^ALLOWED_HOSTS=.*/ALLOWED_HOSTS=\\\"$PUBLIC_IP\\\"/\" .env.production",

        "echo '--- ALLOWED_HOSTS in .env.production ---'",
        "grep '^ALLOWED_HOSTS=' .env.production",
        "echo '--- Full .env.production content after modification ---'",
        "cat .env.production",
        "echo '-----------------------------------------------------'",

        # 3. Start a Django Gunicorn server on the instance.
        (
            "nohup /home/ubuntu/PharmaNet2/venv/bin/gunicorn "
            "--bind 0.0.0.0:8000 pharmacy_management.wsgi:application "
            "> /home/ubuntu/PharmaNet2/gunicorn.log 2>&1 &"
        )
    ]

    time.sleep(5)  # Optional: small delay to ensure stability

    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": commands},
    )

    command_id = response["Command"]["CommandId"]

    time.sleep(5)  # Wait a bit for commands to finish

    invocation_result = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )

    print("SSM command stdout:")
    print(invocation_result.get("StandardOutputContent", ""))

    print("SSM command stderr:")
    print(invocation_result.get("StandardErrorContent", ""))

    # 4. Set a shutdown timer for the server to stop after 2 hours.
    print("Shutdown timer updated.")
    initialize_shutdown_timer()

    # 5. Gets the public IP from the EC2 API to return it in the Lambda response.
    ip = get_public_ip(instance_id)
    print(f"Server is available at http://{ip}:{PORT}")

    print("Command sent:", response["Command"]["CommandId"])
    
    # 6. Open the server URL in a web browser.
    return {
        "status": "EC2 instance started and Django server launching.",
        "public_ip": ip,
        "url": f"http://{ip}:{PORT}"
    }