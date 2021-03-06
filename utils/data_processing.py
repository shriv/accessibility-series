import pandas as pd
import requests
import os
import ast
from shapely.geometry import Point
import geopandas
import osmnx as ox
import utils.util as ut

########################
##  GLOBAL PARAMETERS ##
########################

toblers = [6.0, 3.5, 0.05]
brunsdon = [3.557, 2.03, 0.13]


########################
## GENERAL PROCESSING ##
########################

def convert_list_string(list_string):
    """
    Converts a string list to a list of strings
    u'[a, b, b]' --> ['a', 'b', 'c']
    Needed to expand the nodes columns in ways
    """
    # list_unicode_string =  list_string.decode("utf-8")
    return ast.literal_eval(str(list_string))


def replace_categorical_with_int(df, level):
    level_values = df[level].unique()
    level_lookup = dict(zip(level_values, range(len(level_values))))
    level_lookup_df = pd.DataFrame({'level_id': level_lookup.values(),
                                    'level': level_lookup.keys()})
    return level_lookup


##############
## OVERPASS ##
##############

def generate_overpass_query(tags, objects,
                            osm_bbox,
                            entities=["amenity"]):
    """
    Generate and return Overpass query string
    Permuation of entities, tags and objects.
    So, 2 objects, 3 tags and 2 entities will generate 12 sub-queries

    Args:
     tags: list of tags (e.g. 'fuel')
     objects: list of objects (e.g. nodes, ways)
     osm_bbox: vertex list of OSM bounding box convention. Order is: (S, W, N, E)
     entities: list of entities (amenity by default)

    Returns:
     compactOverpassQLstring: query string
    """

    compactOverpassQLstring = '[out:json][timeout:60];('
    for entity in entities:
        for tag in tags:
            for obj in objects:
                compactOverpassQLstring += '%s["%s"="%s"](%s,%s,%s,%s);' % (obj, entity, tag,
                                                                            osm_bbox[0],
                                                                            osm_bbox[1],
                                                                            osm_bbox[2],
                                                                            osm_bbox[3])
    compactOverpassQLstring += ');out body;>;out skel qt;'
    return compactOverpassQLstring


def get_osm_data(compactOverpassQLstring, osm_bbox):
    """
    Get Data from OSM via Overpass. Convert JSON to Pandas dataframe. Save.
    If data has been downloaded previously, read from csv

    Args:
     compactOverpassQLstring: Query string
     osm_bbox: OSM-spec'd bounding box as list

    Returns:
     osmdf: pandas dataframe of extracted JSON
    """

    # Filename
    bbox_string = '_'.join([str(x) for x in osm_bbox])
    osm_filename = 'data/osm_data_{}.csv'.format(bbox_string)

    if os.path.isfile(osm_filename):
        osm_df = pd.read_csv(osm_filename)

    else:
        # Request data from Overpass
        osmrequest = {'data': compactOverpassQLstring}
        osmurl = 'http://overpass-api.de/api/interpreter'

        # Ask the API
        osm = requests.get(osmurl, params=osmrequest)

        # Convert the results to JSON and get the requested data from the 'elements' key
        # The other keys in osm.json() are metadata guff like 'generator', 'version' of API etc.
        osmdata = osm.json()
        osmdata = osmdata['elements']
        # Convert JSON output to pandas dataframe
        for dct in osmdata:
            if 'tags' in dct.keys():
                for key, val in dct['tags'].items():
                    dct[key] = val
                del dct['tags']
            else:
                pass
        osm_df = pd.DataFrame(osmdata)
    return osm_df


def separate_elevation_graph_by_direction(G):
    """
    """

    # Break graph
    G_undir = G.to_undirected()
    graph_undir_df = ox.graph_to_gdfs(G_undir)
    nodes_gdfs_undir = graph_undir_df[0]
    edges_gdfs_undir = graph_undir_df[1]

    # Create the inverted graph
    edges_gdfs_undir_inv = edges_gdfs_undir.copy()
    edges_gdfs_undir_inv['u'] = edges_gdfs_undir['v']
    edges_gdfs_undir_inv['v'] = edges_gdfs_undir['u']
    edges_gdfs_undir_inv['grade'] = -edges_gdfs_undir['grade']

    # Add the travel times
    edges_gdfs_undir['time_5khr'] = ut.flat_travel_time(edges_gdfs_undir['length'])
    edges_gdfs_undir['time_tobler'] = ut.hiking_time(edges_gdfs_undir['grade'],
                                                     edges_gdfs_undir['length'],
                                                     params_list=toblers)
    edges_gdfs_undir_inv['time_tobler'] = ut.hiking_time(edges_gdfs_undir_inv['grade'],
                                                         edges_gdfs_undir_inv['length'],
                                                         params_list=toblers)

    # Create the expected indices for pandana edges
    edges_gdfs_undir['from_idx'] = edges_gdfs_undir['u']
    edges_gdfs_undir['to_idx'] = edges_gdfs_undir['v']
    edges_gdfs_undir= edges_gdfs_undir.set_index(['from_idx', 'to_idx'])
    edges_gdfs_undir.index.names= ['','']

    # Create the expected indices for pandana edges: for the inverse
    edges_gdfs_undir_inv['from_idx'] = edges_gdfs_undir_inv['u']
    edges_gdfs_undir_inv['to_idx'] = edges_gdfs_undir_inv['v']
    edges_gdfs_undir_inv= edges_gdfs_undir_inv.set_index(['from_idx', 'to_idx'])
    edges_gdfs_undir_inv.index.names= ['','']

    return edges_gdfs_undir_inv, edges_gdfs_undir, nodes_gdfs_undir


##########################
## GEOPANDAS PROCESSING ##
##########################

def extend_ways_to_node_view(osmdf):
    """
    """

    osmdf_ways = osmdf.query('type == "way"')[['id', 'nodes', 'type']]
    osmdf_nodes = osmdf.query('type == "node"')[['id', 'lat', 'lon']]

    # Expanding way node list to one row per node. So many
    osmdf_ways['nodes'] = osmdf_ways['nodes'].apply(convert_list_string)
    osmdf_ways_clean = (osmdf_ways
                        .set_index(['id', 'type'])['nodes']
                        .apply(pd.Series)
                        .stack()
                        .reset_index())
    osmdf_ways_clean.columns = ['way_id', 'type', 'sample_num', 'nodes']

    # Merge cleaned ways with nodes with one row per node.
    # Way df is now has many rows per way_id
    osmdf_clean = pd.merge(osmdf_ways_clean,
                           osmdf_nodes,
                           left_on='nodes',
                           right_on='id').drop(['nodes'], axis=1)

    return osmdf_clean


def coords_df_to_geopandas_points(osmdf, crs={'init': u'epsg:4167'}):
    """
    """

    osmdf['Coordinates'] = list(zip(osmdf.lon, osmdf.lat))
    osmdf['Coordinates'] = osmdf['Coordinates'].apply(Point)
    points_osmdf_clean = geopandas.GeoDataFrame(osmdf, geometry='Coordinates', crs=crs)
    return points_osmdf_clean


def geopandas_points_to_poly(points_df, crs={'init': u'epsg:4167'}):
    """
    """

    points_df['geometry'] = points_df['Coordinates'].apply(lambda x: x.coords[0])
    poly_osmdf_clean = (points_df
                        .groupby('way_id')['geometry']
                        .apply(lambda x: Polygon(x.tolist()))
                        .reset_index())
    poly_osmdf_clean = geopandas.GeoDataFrame(poly_osmdf_clean, crs=crs)
    return poly_osmdf_clean


def getXY(pt):
    return (pt.x, pt.y)


def lat_lon_to_geopandas(df):
    """
    """
    # Convert intersection points to Geopandas
    geometry = [Point(xy) for xy in zip(df.lon, df.lat)]
    gpd_df = geopandas.GeoDataFrame(pd.DataFrame({'geometry': geometry}), crs=None, geometry=geometry)
    gpd_df = gpd_df[['geometry']]
    return gpd_df

def geopandas_to_lat_lon(gpd_df, column):
    x,y = [list(t) for t in zip(*map(getXY, gpd_df[column]))]
    df = pd.DataFrame({'lon': x, 'lat': y})
    return df
