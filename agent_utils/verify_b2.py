import boto3
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

ENDPOINT = os.getenv("BACKBLAZE_B2_ENDPOINT")
KEY_ID = os.getenv("BACKBLAZE_B2_ACCESS_KEY")
APP_KEY = os.getenv("BACKBLAZE_B2_SECRET_KEY")
BUCKET = os.getenv("BACKBLAZE_B2_BUCKET")
REGION = os.getenv("BACKBLAZE_B2_REGION")

def test_b2():
    print(f"\n--- Testing Backblaze B2 ---")
    print(f"Endpoint: {ENDPOINT}")
    print(f"Key ID: {KEY_ID}")
    print(f"Bucket: {BUCKET}")
    
    s3 = boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=KEY_ID,
        aws_secret_access_key=APP_KEY,
        region_name=REGION or "us-west-004",
    )
    
    try:
        # Try to list objects (least intrusive)
        s3.list_objects_v2(Bucket=BUCKET, MaxKeys=1)
        print("B2: SUCCESS (Connection & Permissions ok)")
    except ClientError as e:
        print(f"B2: FAILED: {e}")
    except Exception as e:
        print(f"B2: ERROR: {e}")

if __name__ == "__main__":
    test_b2()
