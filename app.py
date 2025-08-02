import boto3
from botocore import UNSIGNED
from botocore.config import Config
import numpy as np
import rasterio
from stl import mesh
import os


def latlon_to_tile(lat, lon, resolution=90):
    """
    Converts latitude and longitude to Copernicus DEM tile base path.
    Example: Copernicus_DSM_COG_30_S90_00_W156_00_DEM
    """
    lat_prefix = 'N' if lat >= 0 else 'S'
    lon_prefix = 'E' if lon >= 0 else 'W'
    lat_deg = abs(int(lat))
    lon_deg = abs(int(lon))
    return f"Copernicus_DSM_COG_{resolution}_{lat_prefix}{lat_deg:02d}_00_{lon_prefix}{lon_deg:03d}_00_DEM"

def download_tile_files(lat, lon, resolution=90, download_path='.'):
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED), region_name='eu-central-1')
    bucket_name = 'copernicus-dem-90m'
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
        if key.endswith('DEM.tif'):
            local_file = f"{download_path}/{key.replace('/', '_')}"
            if os.path.exists(local_file):
                print(f"File already exists, skipping: {local_file}")
                continue
            try:
                s3.download_file(bucket_name, key, local_file)
                print(f"Downloaded {key} to {local_file}")
            except Exception as e:
                print(f"Error downloading {key}: {e}")
    # Convert the downloaded Elevation Difference GeoTIFF to STL
    tif_files = [f for f in found_files if f.endswith('DEM.tif')]
    for tif_file in tif_files:
        local_tif_path = f"{download_path}/{tif_file.replace('/', '_')}"
        stl_file = local_tif_path.replace('.tif', '.stl')
        '''
        if os.path.exists(stl_file):
            print(f"STL file already exists, skipping: {stl_file}")
            continue
        '''
        print(f"Converting {local_tif_path} to {stl_file}")
        tif_to_stl(local_tif_path, stl_file, scale_z=1.0, sample_step=1, base_height=0.0, clip_min=None, clip_max=None)


def normal_vector(triangle):
    """
    Calculate the normal vector of a triangle (3 points).
    Returns a unit vector.
    """
    a, b, c = triangle
    e1 = np.subtract(a, b).astype(np.float32)
    e2 = np.subtract(b, c).astype(np.float32)
    cp = np.cross(e1, e2)
    mag = np.linalg.norm(cp)
    if mag == 0:
        return np.array([0.0, 0.0, 1.0], dtype=np.float32)
    return cp / mag

def tif_to_stl(tif_path, stl_path, scale_z=1.0, sample_step=5, base_height=0.0, clip_min=None, clip_max=None):
    """
    Converts a GeoTIFF terrain file to a 3D STL mesh using improved normals and clipping.
    """
    with rasterio.open(tif_path) as src:
        elevation = src.read(1)[::sample_step, ::sample_step]
        nodata = src.nodata
        elevation = np.nan_to_num(elevation)
        rows, cols = elevation.shape

    # Optionally clip elevation values
    if clip_min is not None:
        elevation[elevation < clip_min] = clip_min
    if clip_max is not None:
        elevation[elevation > clip_max] = clip_max

    # Centering the grid
    x_offset = cols / 2
    y_offset = rows / 2

    vertices = []
    for y in range(rows):
        for x in range(cols):
            z = elevation[y, x] * scale_z + base_height
            vertices.append([x - x_offset, y_offset - y, z])

    # STL binary writer
    def write_stl(path, vertices, rows, cols):
        facet_count = (rows - 1) * (cols - 1) * 2
        with open(path, 'wb') as f:
            f.write(b'\0' * 80)
            f.write(np.array([facet_count], dtype='<u4').tobytes())
            for y in range(rows - 1):
                for x in range(cols - 1):
                    i = y * cols + x
                    # Get indices for quad corners
                    a = i
                    b = i + cols
                    c = i + 1
                    d = b + 1
                    # Get elevations for nodata skipping
                    av = elevation[y, x]
                    bv = elevation[y + 1, x]
                    cv = elevation[y, x + 1]
                    dv = elevation[y + 1, x + 1]
                    # Skip triangles with nodata
                    if nodata is not None and (av == nodata or bv == nodata or cv == nodata or dv == nodata):
                        continue
                    # First triangle (a, b, c)
                    tri1 = (vertices[a], vertices[b], vertices[c])
                    n1 = normal_vector(tri1)
                    f.write(np.array(n1, dtype='<f4').tobytes())
                    for v in tri1:
                        f.write(np.array(v, dtype='<f4').tobytes())
                    f.write(b'\0\0')
                    # Second triangle (d, c, b)
                    tri2 = (vertices[d], vertices[c], vertices[b])
                    n2 = normal_vector(tri2)
                    f.write(np.array(n2, dtype='<f4').tobytes())
                    for v in tri2:
                        f.write(np.array(v, dtype='<f4').tobytes())
                    f.write(b'\0\0')

    write_stl(stl_path, vertices, rows, cols)
    print(f"✅ STL file saved: {stl_path}")

if __name__ == "__main__":
    # Example usage: download all files for latitude -90, longitude -156, resolution 10m
    latitude = 47
    longitude = 13
    download_tile_files(latitude, longitude, resolution=30, download_path='./tiles')