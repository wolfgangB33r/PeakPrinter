import boto3
from botocore import UNSIGNED
from botocore.config import Config

def list_all_files(bucket_name):
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED), region_name='eu-central-1')
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name)

    all_files = []
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                all_files.append(obj['Key'])
    return all_files

if __name__ == "__main__":
    bucket_name = 'copernicus-dem-90m'
    files = list_all_files(bucket_name)
    with open('copernicus_dem_90m_file_list.txt', 'w') as f:
        for file_name in files:
            f.write(file_name + '\n')
    print(f"Listed {len(files)} files in {bucket_name}.")