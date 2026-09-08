"""Publish the generated analytics lake to the production R2 bucket."""
import os
from pathlib import Path
import boto3
from botocore.config import Config

ROOT=Path(__file__).resolve().parent.parent
BUCKET='cricket-wicket-data'

def main():
    client=boto3.client('s3',endpoint_url=os.environ['R2_ENDPOINT'],aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],region_name='auto',config=Config(signature_version='s3v4'))
    for path in sorted((ROOT/'analytics_lake').iterdir(),key=lambda p:(p.name=='manifest.json',p.name)):
        if not path.is_file():continue
        content_type='application/json' if path.suffix=='.json' else 'application/vnd.apache.parquet'
        client.upload_file(str(path),BUCKET,path.name,ExtraArgs={'ContentType':content_type,'CacheControl':('no-cache' if path.name=='manifest.json' else 'public, max-age=31536000, immutable' if '-' in path.stem else 'public, max-age=3600')})
        print(f'Published {path.name} ({path.stat().st_size:,} bytes)')

if __name__=='__main__':main()
