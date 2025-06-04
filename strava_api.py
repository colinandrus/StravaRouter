import keyring
import requests
import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt

# Strava API credentials
CLIENT_ID = keyring.get_password('strava_client_id', 'segment_router')
CLIENT_SECRET = keyring.get_password('strava_client_secret', 'segment_router')
REFRESH_TOKEN = keyring.get_password('strava_refresh_token', 'segment_router')
BASE_URL = 'https://www.strava.com/api/v3'

def get_access_token(client_id, client_secret, refresh_token):
    """
    Obtain a new access token using the refresh token.
    """
    auth_url = 'https://www.strava.com/oauth/token'
    response = requests.post(auth_url, data={
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    })
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()['access_token']

def search_segments(lat_min, lon_min, lat_max, lon_max, access_token):
    """
    Search Strava segments within a bounding box defined by coordinates.
    """
    search_url = f"{BASE_URL}/segments/explore"
    params = {
        'bounds': f"{lat_min},{lon_min},{lat_max},{lon_max}",
        'activity_type': 'running',  # Can also use 'running', could modify later to allow
    }
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    response = requests.get(search_url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def calculate_deviation(path_nodes, points, graph):
    """
    Calculate the total deviation for each potential path.
    
    Args:
        path_nodes: List of node IDs in the path
        points: List of (lat, lon) tuples from decoded points
        graph: OSMnx graph object
    """
    total_deviation = 0
    for i in range(len(points)-1):
        # Get the segment of the original path
        start_point = points[i]
        end_point = points[i+1]
        
        # Find the corresponding nodes in our path
        start_node_idx = i
        end_node_idx = min(i+1, len(path_nodes)-1)
        
        # Calculate the distance between the original path and the node path
        original_distance = ox.distance.great_circle(
            start_point[0], start_point[1],
            end_point[0], end_point[1]
        )
        
        node_distance = 0
        for j in range(start_node_idx, end_node_idx):
            node1 = path_nodes[j]
            node2 = path_nodes[j+1]
            
            # Check if there's a direct edge between these nodes
            if graph.has_edge(node1, node2):
                node_distance += graph.edges[node1, node2, 0]['length']
            else:
                # If no direct edge, try to find the shortest path
                try:
                    path = nx.shortest_path(graph, node1, node2, weight='length')
                    # Sum up the lengths of all edges in the path
                    for k in range(len(path)-1):
                        if graph.has_edge(path[k], path[k+1]):
                            node_distance += graph.edges[path[k], path[k+1], 0]['length']
                except nx.NetworkXNoPath:
                    # If no path exists, use the straight-line distance
                    node_distance += ox.distance.great_circle(
                        graph.nodes[node1]['y'], graph.nodes[node1]['x'],
                        graph.nodes[node2]['y'], graph.nodes[node2]['x']
                    )
        
        total_deviation += abs(original_distance - node_distance)
    
    return total_deviation

def find_best_path_nodes(graph, points, max_deviation=50):
    """
    Find the best sequence of nodes that minimizes deviation from the original path.
    
    Args:
        graph: OSMnx graph object
        points: List of (lat, lon) tuples from decoded points
        max_deviation: Maximum allowed deviation in meters from original path
    
    Returns:
        List of node IDs that best approximate the path
    """
    # Convert points to numpy array for easier calculations
    points_array = np.array(points)
    
    # Get all nodes within max_deviation meters of the path
    nodes = []
    for point in points:
        # Get all nodes within max_deviation meters
        nearby_nodes = ox.distance.nearest_nodes(graph, 
                                               [point[1]],  # longitude
                                               [point[0]],  # latitude
                                               return_dist=True)
        nodes.extend(nearby_nodes[0])
    
    # Remove duplicates while preserving order
    nodes = list(dict.fromkeys(nodes))
    
    # Start with the nearest nodes path
    best_path = nodes
    best_deviation = calculate_deviation(best_path, points, graph)
    
    # Try to improve the path by removing nodes that don't help
    improved = True
    while improved:
        improved = False
        for i in range(1, len(best_path)-1):
            # Try removing this node
            test_path = best_path[:i] + best_path[i+1:]
            test_deviation = calculate_deviation(test_path, points, graph)
            
            if test_deviation < best_deviation:
                best_path = test_path
                best_deviation = test_deviation
                improved = True
                break
    
    return best_path
