import boto3
from botocore import UNSIGNED
from botocore.config import Config

def latlon_to_tile(lat, lon, resolution=10):
    """
    Converts latitude and longitude to Copernicus DEM tile base path.
    Example: Copernicus_DSM_COG_10_S90_00_W156_00_DEM
    """
    lat_prefix = 'N' if lat >= 0 else 'S'
    lon_prefix = 'E' if lon >= 0 else 'W'
    lat_deg = abs(int(lat))
    lon_deg = abs(int(lon))
    return f"Copernicus_DSM_COG_{resolution}_{lat_prefix}{lat_deg:02d}_00_{lon_prefix}{lon_deg:03d}_00_DEM"

def download_tile_files(lat, lon, resolution=10, download_path='.'):
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED), region_name='eu-central-1')
    bucket_name = 'copernicus-dem-30m'
    tile_base = latlon_to_tile(lat, lon, resolution)
    print(f"Searching for files with base: {tile_base}")

    # List all objects with Prefix
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=tile_base)

    found_files = []
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                found_files.append(obj['Key'])

    if not found_files:
        print("No files found for this tile.")
        return

    for key in found_files:
        local_file = f"{download_path}/{key.replace('/', '_')}"
        try:
            s3.download_file(bucket_name, key, local_file)
            print(f"Downloaded {key} to {local_file}")
        except Exception as e:
            print(f"Error downloading {key}: {e}")

if __name__ == "__main__":
    # Example usage: download all files for latitude -90, longitude -156, resolution 10m
    latitude = 47
    longitude = 13
    download_tile_files(latitude, longitude, resolution=10, download_path='./tiles')