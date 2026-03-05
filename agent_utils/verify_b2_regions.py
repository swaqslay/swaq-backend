import boto3
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

KEY_ID = os.getenv("BACKBLAZE_B2_ACCESS_KEY")
APP_KEY = os.getenv("BACKBLAZE_B2_SECRET_KEY")

REGIONS = ["us-west-001", "us-west-002", "us-west-004", "eu-central-003", "us-east-005"]

def test_regions():
    print(f"--- Multi-Region B2 Test ---")
    print(f"Key ID: {KEY_ID}")
    
    for region in REGIONS:
        endpoint = f"https://s3.{region}.backblazeb2.com"
        print(f"\nTesting Region: {region} | Endpoint: {endpoint}")
        
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=KEY_ID,
            aws_secret_access_key=APP_KEY,
            region_name=region,
        )
        
        try:
            s3.list_buckets()
            print(f"SUCCESS in region: {region}!")
            return region
        except ClientError as e:
            print(f"Failed in {region}: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
        except Exception as e:
            print(f"Error in {region}: {e}")
            
    return None

if __name__ == "__main__":
    test_regions()
