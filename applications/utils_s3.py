import os, boto3
from botocore.exceptions import NoCredentialsError, ClientError


def read_attachment_bytes(att):
    """
    Read the S3 object whose key is stored in att.file.name.
    Works even if DEFAULT_FILE_STORAGE is FileSystemStorage.
    """
    bucket = os.getenv("AWS_STORAGE_BUCKET_NAME")
    region = os.getenv("AWS_S3_REGION_NAME", "ap-southeast-1")
    if not bucket:
        raise RuntimeError("AWS_STORAGE_BUCKET_NAME not set")

    s3 = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN") or None,
    )
    try:
        obj = s3.get_object(Bucket=bucket, Key=att.file.name)
        return obj["Body"].read()
    except NoCredentialsError as e:
        raise RuntimeError("AWS credentials not configured") from e
    except ClientError as e:
        msg = e.response.get("Error", {}).get("Message", "unknown S3 error")
        raise RuntimeError(f"S3 get_object failed: {msg}") from e
