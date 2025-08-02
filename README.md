# Peak Printer

Peak Printer is a Python project for downloading, processing, and converting Copernicus DEM (Digital Elevation Model) data into 3D printable STL files. The project enables users to select a geographic region, retrieve the corresponding elevation data from the Copernicus DEM S3 bucket, and generate a 3D terrain model suitable for visualization or 3D printing.

## Purpose

The main goal of PeakPrinter is to make it easy for researchers, educators, hobbyists, and makers to create physical models of real-world terrain. By automating the process of downloading DEM data and converting it to STL format, PeakPrinter helps users quickly turn geographic elevation data into tangible 3D objects.

## Background

The Copernicus DEM is a global digital elevation model produced by the European Space Agency (ESA) as part of the Copernicus Programme. It provides high-resolution elevation data derived from satellite imagery, supporting applications in earth observation, environmental monitoring, and geospatial analysis.

PeakPrinter uses the Copernicus DEM data hosted on AWS S3, specifically the `copernicus-dem-90m` and `copernicus-dem-30m` buckets, which contain elevation tiles in GeoTIFF format. These tiles can be programmatically accessed and processed to extract elevation information for any region of interest.

## Data Source

The elevation data used in this project comes from the Copernicus DEM collection, available at:

[Copernicus DEM Data Collection](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM)

Please refer to the official website for more details about the data, licensing, and usage restrictions.

## AWS S3 Buckets

The Copernicus DEM files are hosted on AWS S3. You can find a list of the available buckets and further information at:

[AWS Open Data Registry: Copernicus DEM](https://registry.opendata.aws/copernicus-dem/)

## Example: Austria (Gmunden Region, Lat: 47 Lon: 13)

Below is a screenshot of a 3D terrain model generated for an area in Austria around Gmunden using PeakPrinter and Copernicus DEM data:

![Austria Gmunden Terrain Model](./screenshots/austria_gmunden_example.png)

## Example: Austria (Hallstadt Region, Lat: 47 Lon: 13)

Below is a screenshot of a 3D terrain model generated for an area in Austria around Gmunden using PeakPrinter and Copernicus DEM data:

![Austria Gmunden Terrain Model](./screenshots/austria_gmunden_example.png)

*This example demonstrates how you can use PeakPrinter to visualize and 3D print real-world terrain data for any region.*

## Features

- Download Copernicus DEM tiles for a given latitude and longitude
- List available files in the DEM S3 bucket
- Convert GeoTIFF elevation data to STL 3D models
- Skip already downloaded or processed files to save time and bandwidth

## Requirements

- Python 3.8+
- boto3
- rasterio
- numpy
- numpy-stl

## Usage

1. Clone the repository.
2. Install the required Python packages.
3. Run the provided scripts to list, download, and convert DEM data.

## License

This project is provided for educational and research purposes. Please check the Copernicus DEM data license before using the data for commercial applications.

---

## Kudos to ESA Copernicus and Open Data!

**A huge thank you and endless kudos to the European Space Agency (ESA) and the Copernicus mission for their visionary commitment to open data!**  
The Copernicus Programme's open data policy empowers researchers, educators, makers, and innovators around the world to access high-quality earth observation data for free. This openness fuels countless scientific discoveries, educational initiatives, and creative projects—like PeakPrinter—that would not be possible without such generous access.

Copernicus stands as a shining example of how open data can drive progress, collaboration, and inspiration across borders and disciplines.  
**Thank you, ESA Copernicus, for making the world a better, smarter, and more connected place through your dedication to open data!**