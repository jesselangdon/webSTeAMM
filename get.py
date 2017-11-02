#-------------------------------------------------------------------------------
# Name:         get.py
#
# Summary:      The modis_preprocess module allows the user to download MODIS LST datasets
#               as HDF files to the user's local computer.  The HDF files are then automatically
#               converted from HDF to geotiff format.
#
# Project:      Stream Temperature Automated Modeler using MODIS (STeAMM)
#
# Author:       Jesse Langdon
#
# References:   McNyset, Kristina M., Carol J. Volk, and Chris E. Jordan. "Developing
#               an Effective Model for Predicting Spatially and Temporally Continuous
#               Stream Temperatures from Remotely Sensed Land Surface Temperatures."
#               Water 7.12 (2015): 6827-6846.
#
# Last Updated: 10/04/2017
# Copyright:    (c) South Fork Research, Inc. 2017
# Licence:      FreeBSD License
# Version:      0.3
#-------------------------------------------------------------------------------

# Import modules
import os
import sys
import shutil
# import gdal
# import gdalconst

# import externals.get_modis.get_modis as gm

#Global constants
PLATFORM = 'MOLT'
MODIS_PRODUCTS = {'Daily':'MOD11A1.006', # Land Surface Temperature/Emissivity Daily L3 Global 1km'
                  '8-day':'MOD11A2.006'} # Land Surface Temperature/Emissivity 8-Day L3 Global 1km'


def build_dir_list(project_dir, product_list, year_list):
    """Create a list of full directory paths for downloaded MODIS files."""
    dir_list = []
    try:
        if os.path.exists(project_dir):
            for product in product_list.itervalues():
                for year in year_list:
                    dir_list.append(os.path.join(project_dir, year, product))
                    #dir_list.append("{}\{}\{}".format(project_dir, year, product))
        return dir_list
    except OSError, e:
        if not os.path.exists(project_dir):
            print('Error creating directory list. Project directory folder not found.')
            sys.exitfunc()
        return dir_list


def make_dirs(dir_list):
    """Creates new directories to store downloaded MODIS files"""
    try:
        if dir_list:
            for dir in dir_list:
                if not os.path.exists(dir):
                    print ("Creating new directory " + dir)
                    os.makedirs(dir, 0777)
                else:
                    print ("Overwriting existing directory with " + dir)
                    shutil.rmtree(dir)
                    os.makedirs(dir, 0777)
    except IndexError as e:
        print("Error making directories. The directory list is empty.")
        sys.exitfunc()
    return


# #FIXME is this necessary? might need to change to something that just connects to the AWS S3 bucket
# def download_hdf(product_list, year_list, swath_list, doy_start, doy_end, project_dir, username, password, proxy=None):
#     """download HDF files for multiple years, using get_modis."""
#     try:
#         for product in product_list.itervalues():
#             for year in year_list:
#                 for swath in swath_list:
#                     hdf_dir = """{}\{}\{}""".format(project_dir, year, product)
#                     gm.get_modisfiles(username, password, PLATFORM, product, year, swath, proxy, doy_start, doy_end, hdf_dir)
#                 message = 'All HDF files downloaded for %d.' % (year)
#                 print message
#     except Exception as e:
#         print e


# FIXME recfactor to get filepaths from AWS S3 buckets
def get_hdf_filepaths(hdf_dir):
    """Get a list of downloaded HDF files which is be used for iterating through hdf file conversion."""
    print "Building list of downloaded HDF files..."
    hdf_filename_list = []
    hdf_filepath_list = []
    try:
        for dir in hdf_dir:
            for file in os.listdir(dir):
                if file.endswith(".hdf"):
                    #hdf_filename_list.append(os.path.splitext(f)[0])
                    hdf_filename_list.append(file)
                    hdf_filepath_list.append(os.path.join(dir, file))
        return hdf_filename_list, hdf_filepath_list
    except TypeError as e:
        print e
        return hdf_filename_list, hdf_filepath_list



def build_file_array(hdf_filename_list):
    """Split HDF file names into array, allowing other functions to access julian dates."""
    print "Creating array based on HDF file names..."
    hdf_file_array = []
    for f in hdf_filename_list:
        hdf_file_array.append(f.split("."))
    return hdf_file_array


def get_file_dates(hdf_file_array):
    """Build list of collection dates from an HDF file array."""
    print "Building list of MODIS HDF file collection dates..."
    hdf_date_list = []
    for f in hdf_file_array:
        hdf_date_list.append(f[1])
    return hdf_date_list


def find_dup_file_dates(hdf_date_list, swath_list):
    """Extracts list of unique days from list of all file dates."""
    print "Extracting list of non-duplicate MODIS HDF collection dates..."
    if len(swath_list) > 1:
        hdf_dates = set([d for d in hdf_date_list if hdf_date_list.count(d)>1])
    else:
        hdf_dates = hdf_date_list
    sorted_dates = sorted(hdf_dates)
    return sorted_dates


# main function, to serve as example
def main(proj_dir,
         data_products,
         process_yr_str,
         swath_id,
         doy_start_str,
         doy_end_str,
         username,
         password):

    # Create download directories and download from HDF files from USGS server
    dirs = build_dir_list(proj_dir, data_products, process_yr)
    make_dirs(dirs)
    download_hdf(MODIS_PRODUCTS, process_yr, swath_id,
                 doy_start, doy_end, data_dir,
                 username, password)

    hdf_filename_list, hdf_filepath_list = get_hdf_filepaths(dirs)
    hdf_file_array = build_file_array(hdf_filename_list)
    hdf_date_list = get_file_dates(hdf_file_array)
    hdf_dates = find_dup_file_dates(hdf_date_list, swath_id)


# testing variables
data_dir = r'C:\JL\Testing\STeAMM\test'
process_yr = [2015, 2016]
swath_id = ['h09v04', 'h10v04']
doy_start = 1
doy_end = 9
username = 'jesselangdon'
password = 'Jw-3i1970'

# call the main function, run the program
if __name__ == '__main__':
    main(data_dir,
         MODIS_PRODUCTS,
         process_yr,
         swath_id,
         doy_start,
         doy_end,
         username, password)