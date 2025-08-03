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

def download_tile_files(lat, lon, resolution=90, download_path='.', area_km=10):
    # Create the download_path folder if it does not exist
    if not os.path.exists(download_path):
        os.makedirs(download_path)

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
        print(f"Converting {local_tif_path} to {stl_file}")
        tif_to_stl(local_tif_path, stl_file, center_lat=lat, center_lon=lon, area_km=area_km, scale_z=1.0, sample_step=1, base_height=0.0, clip_min=None, clip_max=None)


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

def tif_to_stl(tif_path, stl_path, center_lat, center_lon, area_km=10, scale_z=1.0, sample_step=1, base_height=0.0, clip_min=None, clip_max=None):
    """
    Converts a GeoTIFF terrain file to a 3D STL mesh with a solid base from zero height.
    Crops a square area of area_km x area_km around center_lat, center_lon.
    """
    with rasterio.open(tif_path) as src:
        transform = src.transform

        # Convert area_km to degrees (approximate, works well for small areas)
        km_per_degree = 111.0
        area_deg = area_km / km_per_degree

        # Get pixel coordinates for center point
        center_px, center_py = ~transform * (center_lon, center_lat)
        center_px = int(center_px)
        center_py = int(center_py)

        # Calculate number of pixels for area_deg
        pixel_size_x = abs(transform.a)
        pixel_size_y = abs(transform.e)
        pixels_x = int(area_deg / pixel_size_x)
        pixels_y = int(area_deg / pixel_size_y)
        # calculate the pixel size in km
        pixel_size_km_x = pixel_size_x * km_per_degree
        pixel_size_km_y = pixel_size_y * km_per_degree

        half_x = pixels_x // 2
        half_y = pixels_y // 2
        window = rasterio.windows.Window(
            center_px - half_x, center_py - half_y, pixels_x, pixels_y
        )

        elevation = src.read(1, window=window)[::sample_step, ::sample_step]
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

    # Set scale_z to match horizontal scale (or less for less exaggeration)
    # Default: vertical exaggeration is 1/20th of horizontal scale
    
    scale_z = pixel_size_km_x 

    print("Pixel size X in degree:", pixel_size_x)
    print("Pixel size Y in degree:", pixel_size_y)
    print("Pixel size in km X:", pixel_size_km_x)
    print("Pixel size in km Y:", pixel_size_km_y)   
    print("Scale Z:", scale_z)
    print("Rows:", rows, "Cols:", cols)
    print("Area (km):", area_km, "Approx. Area (degrees):", area_deg)
    print("Center Latitude:", center_lat, "Center Longitude:", center_lon)
    print("Base Height:", base_height)

    vertices = []
    for y in range(rows):
        for x in range(cols):
            z = elevation[y, x] * scale_z + base_height
            vertices.append([x - x_offset, y_offset - y, z])

    # Add base vertices (same x/y, z=0)
    base_vertices = []
    for y in range(rows):
        for x in range(cols):
            base_vertices.append([x - x_offset, y_offset - y, 0.0])

    def write_stl(path, vertices, base_vertices, rows, cols):
        # Top surface facets
        facet_count = (rows - 1) * (cols - 1) * 2
        # Add side and bottom facets
        facet_count += (rows - 1) * 2 * 2  # left/right sides
        facet_count += (cols - 1) * 2 * 2  # front/back sides
        facet_count += (rows - 1) * (cols - 1) * 2  # bottom

        with open(path, 'wb') as f:
            f.write(b'\0' * 80)
            f.write(np.array([facet_count], dtype='<u4').tobytes())
            # Top surface
            for y in range(rows - 1):
                for x in range(cols - 1):
                    i = y * cols + x
                    a = i
                    b = i + cols
                    c = i + 1
                    d = b + 1
                    av = elevation[y, x]
                    bv = elevation[y + 1, x]
                    cv = elevation[y, x + 1]
                    dv = elevation[y + 1, x + 1]
                    if nodata is not None and (av == nodata or bv == nodata or cv == nodata or dv == nodata):
                        continue
                    tri1 = (vertices[a], vertices[b], vertices[c])
                    n1 = normal_vector(tri1)
                    f.write(np.array(n1, dtype='<f4').tobytes())
                    for v in tri1:
                        f.write(np.array(v, dtype='<f4').tobytes())
                    f.write(b'\0\0')
                    tri2 = (vertices[d], vertices[c], vertices[b])
                    n2 = normal_vector(tri2)
                    f.write(np.array(n2, dtype='<f4').tobytes())
                    for v in tri2:
                        f.write(np.array(v, dtype='<f4').tobytes())
                    f.write(b'\0\0')
            # Sides
            # Left side (x=0)
            for y in range(rows - 1):
                top1 = y * cols
                top2 = (y + 1) * cols
                base1 = y * cols
                base2 = (y + 1) * cols
                tri1 = (vertices[top1], base_vertices[base2], base_vertices[base1])
                tri2 = (vertices[top1], vertices[top2], base_vertices[base2])
                for tri in [tri1, tri2]:
                    n = normal_vector(tri)
                    f.write(np.array(n, dtype='<f4').tobytes())
                    for v in tri:
                        f.write(np.array(v, dtype='<f4').tobytes())
                    f.write(b'\0\0')
            # Right side (x=cols-1)
            for y in range(rows - 1):
                top1 = y * cols + (cols - 1)
                top2 = (y + 1) * cols + (cols - 1)
                base1 = y * cols + (cols - 1)
                base2 = (y + 1) * cols + (cols - 1)
                tri1 = (vertices[top1], base_vertices[base1], base_vertices[base2])
                tri2 = (vertices[top1], base_vertices[base2], vertices[top2])
                for tri in [tri1, tri2]:
                    n = normal_vector(tri)
                    f.write(np.array(n, dtype='<f4').tobytes())
                    for v in tri:
                        f.write(np.array(v, dtype='<f4').tobytes())
                    f.write(b'\0\0')
            # Front side (y=0)
            for x in range(cols - 1):
                top1 = x
                top2 = x + 1
                base1 = x
                base2 = x + 1
                tri1 = (vertices[top1], base_vertices[base1], base_vertices[base2])
                tri2 = (vertices[top1], base_vertices[base2], vertices[top2])
                for tri in [tri1, tri2]:
                    n = normal_vector(tri)
                    f.write(np.array(n, dtype='<f4').tobytes())
                    for v in tri:
                        f.write(np.array(v, dtype='<f4').tobytes())
                    f.write(b'\0\0')
            # Back side (y=rows-1)
            for x in range(cols - 1):
                top1 = (rows - 1) * cols + x
                top2 = (rows - 1) * cols + x + 1
                base1 = (rows - 1) * cols + x
                base2 = (rows - 1) * cols + x + 1
                tri1 = (vertices[top1], base_vertices[base2], base_vertices[base1])
                tri2 = (vertices[top1], vertices[top2], base_vertices[base2])
                for tri in [tri1, tri2]:
                    n = normal_vector(tri)
                    f.write(np.array(n, dtype='<f4').tobytes())
                    for v in tri:
                        f.write(np.array(v, dtype='<f4').tobytes())
                    f.write(b'\0\0')
            # Bottom face
            for y in range(rows - 1):
                for x in range(cols - 1):
                    i = y * cols + x
                    a = i
                    b = i + cols
                    c = i + 1
                    d = b + 1
                    tri1 = (base_vertices[a], base_vertices[b], base_vertices[c])
                    tri2 = (base_vertices[d], base_vertices[c], base_vertices[b])
                    for tri in [tri1, tri2]:
                        n = normal_vector(tri)
                        f.write(np.array(n, dtype='<f4').tobytes())
                        for v in tri:
                            f.write(np.array(v, dtype='<f4').tobytes())
                        f.write(b'\0\0')

    write_stl(stl_path, vertices, base_vertices, rows, cols)
    print(f"✅ Solid STL file saved: {stl_path}")

if __name__ == "__main__":
    # Ask user for latitude and longitude (float with decimals)
    try:
        latitude = float(input("Enter latitude (e.g. 47.56): "))
        longitude = float(input("Enter longitude (e.g. 13.64): "))
        area_km = int(input("Enter area size in km (e.g. 30): "))
    except ValueError:
        print("Invalid input. Please enter numeric values for latitude, longitude, and area size.")
        exit(1)
    # You can also ask for resolution if needed
    resolution = 30  # or prompt for this as well
    download_tile_files(latitude, longitude, resolution=resolution, download_path='./tiles', area_km=area_km)