import boto3
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

# Use the discovery
REGION = "us-east-005"
ENDPOINT = f"https://s3.{REGION}.backblazeb2.com"
KEY_ID = os.getenv("BACKBLAZE_B2_ACCESS_KEY")
APP_KEY = os.getenv("BACKBLAZE_B2_SECRET_KEY")

def test_b2():
    print(f"--- Final B2 Verification (us-east-005) ---")
    s3 = boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=KEY_ID,
        aws_secret_access_key=APP_KEY,
        region_name=REGION,
    )
    
    try:
        print("Listing buckets...")
        response = s3.list_buckets()
        buckets = [b['Name'] for b in response.get('Buckets', [])]
        print(f"Buckets found: {buckets}")
        
        target = "swaqImages"
        if target in buckets:
            print(f"Bucket '{target}' exists.")
        else:
            print(f"Bucket '{target}' NOT found. You might need to update BACKBLAZE_B2_BUCKET in .env")
            
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_b2()
