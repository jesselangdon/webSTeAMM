#-------------------------------------------------------------------------------
# Name:         prep.py
#
# Summary:      The prep module allows the user to convert HDF files to a geotiff
#               format. The files are then mosaicked, reprojected, and finally clipped based on a
#               user-supplied polygon shapefile dataset.
#
# Project:      Stream Temperature Automated Modeler using MODIS (STeAMM)
#
# Author:       Jesse Langdon
#
# References:   McNyset, Kristina  M., Carol J. Volk, and Chris E. Jordan. "Developing
#               an Effective Model for Predicting Spatially and Temporally Continuous
#               Stream Temperatures from Remotely Sensed Land Surface Temperatures."
#               Water 7.12 (2015): 6827-6846.
#
# Last Updated: 10/04/2017
# Copyright:    (c) South Fork Research, Inc. 2017
# Licence:      FreeBSD License
# Version:      0.1
#-------------------------------------------------------------------------------

# Import modules
import os
import sys
import csv
import gdal
import gdalconst
import ogr
import osr
import numpy as np

# Drainage polygon shapefile to summarize values (i.e. watersheds, RCAs, etc.): ')
geo_rca = ""


def convert_hdf(proj_dir, dir_list, hdf_filepath_list, hdf_filename_list):
    """Converts downloaded HDF file into geotiff file format."""
    src_xres = None
    src_yres = None
    geotiff_list = []
    """Converts MODIS HDF files to a geotiff format."""
    print "Converting MODIS HDF files to geotiff format..."
    out_format = 'GTiff'
    local_array = zip(hdf_filepath_list, hdf_filename_list)

    for dir in dir_list:
        for in_filepath, out_filename in local_array:

            # Open the LST_Day_1km dataset
            src_open = gdal.Open(in_filepath, gdalconst.GA_ReadOnly) # open file with all sub-datasets
            src_subdatasets = src_open.GetSubDatasets() # make a list of sub-datasets in the HDF file
            subdataset = gdal.Open(src_subdatasets[0][0])

            # Get parameters from LST dataset
            src_cols = subdataset.RasterXSize
            src_rows = subdataset.RasterYSize
            src_band_count = subdataset.RasterCount
            src_geotransform = subdataset.GetGeoTransform()
            src_xres = src_geotransform[1]
            src_yres = src_geotransform[5]
            src_proj = subdataset.GetProjection()

            # Read dataset to array
            src_band = subdataset.GetRasterBand(1)
            src_array = src_band.ReadAsArray(0, 0, src_cols, src_rows).astype(np.float)

            # Set up output file
            driver = gdal.GetDriverByName(out_format)
            #out_file = "%s\%s.%s" % (dir, out_filename, "tif")
            filename = os.path.splitext(out_filename)
            out_file = os.path.join(dir, filename[0] + ".tif")
            out_geotiff = driver.Create(out_file, src_cols, src_rows, src_band_count, gdal.GDT_Float32)
            out_geotiff.SetGeoTransform(src_geotransform)
            out_geotiff.SetProjection(src_proj)
            out_geotiff.GetRasterBand(1).WriteArray(src_array)
            out_geotiff.FlushCache()

            # Create list of output geotiffs
            geotiff_list.append(out_file)

    return geotiff_list, src_xres, src_yres


def build_mosaic_io_array(geotiff_list, hdf_dates):
    """Builds an array with each list item consisting of 1) file names with duplicate name, and 2) shared collection date."""
    print "Building input/output array from mosaic files..."
    mosaic_io_array = []
    for date in hdf_dates:
        row = [i for i in geotiff_list if date in i]
        row.append(date)
        mosaic_io_array.append(row)
    return mosaic_io_array


def convert_to_vrt(mosaic_io_array, swath_ids, input_dir, dir_list, modis_wkt):
    """Generates mosaics as GDAL VRT files for MODIS tiles collected on the same day."""
    print "Generating GDAL VRT files from geotiffs..."
    out_vrt_list = []
    # iterate through list of geotiff file names
    for row in mosaic_io_array:
        for dir in dir_list:
            if len(swath_ids) > 1: # if more than one geotiff in list, mosaic into a vrt file
                in_rasters = ' '.join(row[0:2])
                out_vrt = os.path.join(dir, row[2] + ".vrt")
                expr = 'gdalbuildvrt -a_srs %s %s %s' % (modis_wkt, out_vrt, in_rasters)
            else:  # otherwise, just convert the geotiff to a vrt file
                out_vrt = os.path.join(dir, row[2] + ".vrt")
                expr = 'gdal_translate -of %s -a_srs %s %s %s' % ("VRT", modis_wkt, row[0], out_vrt)
            os.system(expr)
            out_vrt_list.append(out_vrt)
    return out_vrt_list


def get_poly_wkt(in_poly):
    """Obtain the projection of the drainage polygon dataset as a WKT projection file."""
    print "Getting projection of drainage polygon dataset..."
    driver = ogr.GetDriverByName('ESRI Shapefile')
    open_poly = driver.Open(in_poly)
    lyr = open_poly.GetLayer()
    spatialRef = lyr.GetSpatialRef()
    poly_proj4 = spatialRef.ExportToProj4()
    poly_wkt = '"' + poly_proj4 + '"'
    return poly_wkt


def reproject_rasters(in_vrt_list, input_dir, dir_list, modis_wkt, poly_wkt, bbox_list, xres, yres, in_ply):
    """Re-projects VRT mosaics to same projection as drainage polygons, then clips extent to polygon envelope."""
    print "Reprojecting VRT mosaics..."
    xmin = bbox_list[0]
    xmax = bbox_list[1]
    ymin = bbox_list[2]
    ymax = bbox_list[3]
    out_reprj_list = []
    for in_vrt in in_vrt_list:
        out_file = '%s_%s.%s' % (in_vrt, "reprj", 'tif')
        expr = 'gdalwarp -overwrite -t_srs %s -tr %f %f -r %s -of %s -dstnodata %d -cutline %s -cblend %d %s %s' % \
               (poly_wkt, xres, yres, 'bilinear', 'GTiff', -999, in_ply, 5, in_vrt, out_file)
        """
        expr = 'gdalwarp -overwrite -t_srs %s -te %f %f %f %f -tr %f %f -r %s -of %s -dstnodata %d -cutline %s %s %s' % \
               (poly_wkt, xmin, ymin, xmax, ymax, xres, yres, 'bilinear', 'GTiff', 0, in_ply, in_vrt, out_file)
        """
        os.system(expr)
        out_reprj_list.append(out_file)
    return out_reprj_list


def get_first_acq_date(mosaic_io_array):
    '''Get julian date from the mosaicked geotiff file name array'''
    acq_year = mosaic_io_array[0][1]
    acq_date = acq_year[5:8]
    return acq_date


def LST_to_xyz(in_reprj_list, input_dir, dir_list):
    """Converts a mosaicked, reprojected LST geotiff into XYZ points in a CSV file format."""
    print "Converting a geotiff to a XYZ point file..."
    import lib.gdal2xyz as gdal2xyz
    out_csv_list = []
    if in_reprj_list[0].lower().endswith('.tif'):
        tif_file = in_reprj_list[0]
        tif_name_split = tif_file.split('.')
        acq_date = tif_name_split[1][-3:]
        xyz_filename = '%s_%s.%s' % (tif_name_split[0], 'xyz', 'csv')
        csv_filename = '%s_%s.%s' % (tif_name_split[0], 'tbl', 'csv')
        gdal2xyz.main(tif_file, xyz_filename)
        with open(xyz_filename, 'rb') as input, open(csv_filename, 'wb') as output:
            reader = csv.reader(input, delimiter=' ')
            writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_NONNUMERIC)
            all_rows = []
            all_rows.insert(0, ["UID", "X", "Y", str(acq_date)])
            #row = next(reader)
            for i, row in enumerate(reader):
                if row[2] != '-999':
                    all_rows.append([str(i + 1)] + row)
            writer.writerows(all_rows)
        out_csv_list.append(csv_filename)
    else:
        sys.exit("ERROR: No tif files were found in the file list!")
    return xyz_filename


def cell_centroids(in_lst_raster, out_pnt_shp, out_dir):
    '''Generates a point shapefile of centroids from a LST raster.
    Code derived from example @
    https://gis.stackexchange.com/questions/42790/gdal-and-python-how-to-get-coordinates-for-all-cells-having-a-specific-value'''
    import numpy as np

    in_raster = gdal.Open(in_lst_raster) # in_lst_raster must include full filepath
    (upper_left_x, x_size, x_rotation, upper_left_y, y_rotation, y_size) = in_raster.GetGeoTransform()
    band_LST = in_raster.GetRasterBand(1) # raster bands start at 1
    array_LST = band_LST.ReadAsArray().astype(np.int16)
    (y_index, x_index) = np.nonzero(array_LST) # FIXME should probably filter out no-data values (-36728?)

    # set up parameters for output centroid shapefile
    srs = osr.SpatialReference()
    srs.ImportFromWkt(in_raster.GetProjection())
    point_driver = ogr.GetDriverByName('ESRI Shapefile')
    point_data = point_driver.CreateDataSource(out_pnt_shp)
    point_lyr = point_data.CreateLayer('ogr_pts', srs, ogr.wkbPoint)
    point_lyr_defn = point_lyr.GetLayerDefn()

    # processing loop
    fid = 0
    for x, y in zip(x_index, y_index):
        x_coord = x_index[x] * x_size + upper_left_x + (x_size / 2)  # add half the cell size
        y_coord = y_index[y] * y_size + upper_left_y + (y_size / 2)  # center the point

        point = ogr.Geometry(ogr.wkbPoint)
        point.SetPoint(0, x_coord, y_coord)

        feature = ogr.Feature(point_lyr_defn)
        feature.SetGeometry(point)
        feature.SetFID(i)

        point_lyr.CreateFeature(feature)

        fid += 1

    return


def build_julian_csv_array(in_csv_list):
    """Builds an array made up of julian dates paired with csv files."""
    print "Building acquisition date list..."
    julian_csv_array = []
    for csv in in_csv_list:
        csv_filepath_list = csv.split('.')
        acq_date = csv_filepath_list[0][-7:-4]
        acq_year = csv_filepath_list[0][-11:-7]
        row = [acq_date, acq_year, csv]
        julian_csv_array.append(row)
    return julian_csv_array


def compile_LST_table(julian_csv_array, input_dir, dir_list):
    """Builds a csv table comprised of grid cell LST values from
    each tile. The csv table will serve as input to the LST value
    interpolation process."""
    print "Building LST interpolation input table..."
    acq_year = julian_csv_array[0][1]
    out_dir = '%s\\%s\\' % (input_dir, dir_list[1])
    out_file = '%s%s_%s.%s' % (out_dir, 'LST', acq_year, 'csv')
    first_filename = julian_csv_array[0][2]
    file1_rows = []

    with open(first_filename, 'rb') as file1:
        reader1 = csv.reader(file1)
        for r1 in reader1:
            file1_rows.append(r1)

    for acq_date in julian_csv_array[1:]:  # skips the first csv file in list
        with open(acq_date[2], 'rb') as fileX:
            readerX = csv.reader(fileX, delimiter=',')
            fileX_rows = []
            for rX in readerX:
                fileX_rows.append(rX)
            LST_col_list = [row[3] for row in fileX_rows]
            for (f1, LST_val) in zip(file1_rows, LST_col_list):
                f1.append(LST_val)

    with open(out_file, 'wb') as out_csv:
        writer = csv.writer(out_csv, delimiter=',')
        for f in file1_rows:
            writer.writerow(f)
    print "Data pre-processing complete!"
    return out_csv


def get_modis_wkt(modis_srs):
    """Returns the filepath to the MODIS Sin WKT projection file"""
    print "Finding the file path to the MODIS WKT projection file..."
    module_path = os.path.abspath(__file__)
    steamm_dir = os.path.dirname(module_path)
    modis_wkt_filepath = os.path.join(steamm_dir, "lib", modis_srs)
    return modis_wkt_filepath


def get_bbox(in_poly):
    """Gets the extent envelope values of drainage polygons."""
    print "Calculating the extent envelope vaues of drainage polygon dataset..."
    bbox_list = []
    in_driver = ogr.GetDriverByName("ESRI Shapefile")
    in_ds = in_driver.Open(in_poly, 0)
    in_lyr = in_ds.GetLayer()
    (xmin, xmax, ymin, ymax) = in_lyr.GetExtent()
    bbox_list.append(xmin)
    bbox_list.append(xmax)
    bbox_list.append(ymin)
    bbox_list.append(ymax)
    return bbox_list