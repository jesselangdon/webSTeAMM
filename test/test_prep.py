import os

# Start get module -----------------------------------------------------------
import get

# global constants
PLATFORM = 'MOLT'
#MODIS_PRODUCTS = {'Daily':'MOD11A1.006', # Land Surface Temperature/Emissivity Daily L3 Global 1km'
#                  '8-day':'MOD11A2.006'} # Land Surface Temperature/Emissivity 8-Day L3 Global 1km'
MODIS_PRODUCTS = {'8-day':'MOD11A2.006'} # Land Surface Temperature/Emissivity 8-Day L3 Global 1km'

# testing variables for get module
data_dir = os.path.join('/','media', 'sf_vmshare', 'testing', 'webSTeAMM', 'test')
process_yr = ['2016']
swath_id = ['h09v04', 'h10v04']
doy_start = 1
doy_end = 9
username = 'jesselangdon'
password = 'Jw-3i1970'

# copy and organize local HDF tiles
dir_list = get.build_dir_list(data_dir, MODIS_PRODUCTS, process_yr)
#get.make_dirs(dir_list)

hdf_filename_list, hdf_filepath_list = get.get_hdf_filepaths(dir_list)
hdf_file_array = get.build_file_array(hdf_filename_list)
hdf_date_list = get.get_file_dates(hdf_file_array)
hdf_dates = get.find_dup_file_dates(hdf_date_list, swath_id)

# End get module ------------------------------------------------------------


# Start prep module ---------------------------------------------------------
import prep

# testing variables for prep module
geo_rca = os.path.join("/", "media", "sf_vmshare", "testing", "webSTeAMM", "MODIS_DataSource", "RCAs", "Yankee_Fork_RCAs.shp")

# File conversion
geotiff_list, xres, yres = prep.convert_hdf(data_dir, dir_list, hdf_filepath_list, hdf_filename_list)
poly_wkt = prep.get_poly_wkt(geo_rca)
bbox_list = prep.get_bbox(geo_rca)
mosaic_io_array = prep.build_mosaic_io_array(geotiff_list, hdf_dates)
modis_wkt = prep.get_modis_wkt("MODIS_sin.wkt")
vrt_list = prep.convert_to_vrt(mosaic_io_array, swath_id, dir_list, modis_wkt)
reprj_list = prep.reproject_rasters(vrt_list, data_dir, dir_list, modis_wkt, poly_wkt, bbox_list, xres, yres, geo_rca)
csv_list = prep.LST_to_xyz(reprj_list, data_dir, dir_list)
julian_csv_array = prep.build_julian_csv_array(csv_list)
LST_csv = prep.compile_LST_table(julian_csv_array, data_dir, dir_list)

# End prep module -----------------------------------------------------------