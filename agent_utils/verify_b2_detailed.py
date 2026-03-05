import boto3
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

ENDPOINT = os.getenv("BACKBLAZE_B2_ENDPOINT")
KEY_ID = os.getenv("BACKBLAZE_B2_ACCESS_KEY")
APP_KEY = os.getenv("BACKBLAZE_B2_SECRET_KEY")
BUCKET = os.getenv("BACKBLAZE_B2_BUCKET")
REGION = os.getenv("BACKBLAZE_B2_REGION") or "us-west-004"

def test_b2():
    print(f"\n--- Debugging Backblaze B2 ---")
    print(f"Endpoint: {ENDPOINT}")
    print(f"Key ID: {KEY_ID}")
    print(f"Secret (first 5): {APP_KEY[:5]}...")
    print(f"Bucket: {BUCKET}")
    print(f"Region: {REGION}")
    
    s3 = boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=KEY_ID,
        aws_secret_access_key=APP_KEY,
        region_name=REGION,
    )
    
    try:
        print("Attempting to list buckets...")
        response = s3.list_buckets()
        print("B2: SUCCESS! Found buckets:")
        for b in response.get('Buckets', []):
            print(f" - {b['Name']}")
            
        print(f"\nAttempting to access target bucket: {BUCKET}")
        try:
            s3.head_bucket(Bucket=BUCKET)
            print(f"Bucket '{BUCKET}': FOUND and ACCESSIBLE")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                print(f"Bucket '{BUCKET}': NOT FOUND (Does it definitely exist?)")
            else:
                print(f"Bucket access failed: {e}")
                
    except ClientError as e:
        print(f"B2 Connection FAILED: {e}")
        if 'InvalidAccessKeyId' in str(e):
            print("HINT: The 'Key ID' or 'Secret Key' is incorrect, or S3 access is not enabled for this key.")
    except Exception as e:
        print(f"B2 ERROR: {e}")

if __name__ == "__main__":
    test_b2()
