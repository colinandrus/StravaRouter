import keyring
import requests
import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import polyline


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
    try:
        if not points or len(points) < 2:
            raise ValueError("Need at least 2 points to find a path")

        # Convert points to numpy array for easier calculations
        points_array = np.array(points)
        
        # Get all nodes within max_deviation meters of the path
        nodes = []
        for point in points:
            try:
                # Get all nodes within max_deviation meters
                nearby_nodes = ox.distance.nearest_nodes(graph, 
                                                       [point[1]],  # longitude
                                                       [point[0]],  # latitude
                                                       return_dist=True)
                if nearby_nodes[0] is not None:
                    nodes.extend(nearby_nodes[0])
            except Exception as e:
                print(f"Error finding nearest nodes for point {point}: {str(e)}")
                continue
        
        if not nodes:
            raise ValueError("No nodes found near the path points")
        
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

    except Exception as e:
        print(f"Error in find_best_path_nodes: {str(e)}")
        raise

def find_optimal_path_order(graph, paths):
    """
    Find the optimal order to traverse multiple paths to minimize total distance.
    
    Args:
        graph: OSMnx graph object
        paths: List of lists, where each inner list contains node IDs representing a path
    
    Returns:
        Tuple of (optimal order of paths, total distance)
    """
    # Create a distance matrix between all path endpoints
    n_paths = len(paths)
    distance_matrix = np.zeros((n_paths, n_paths))
    
    # Calculate distances between all path endpoints
    for i in range(n_paths):
        for j in range(n_paths):
            if i != j:
                # Get the end node of path i and start node of path j
                end_node = paths[i][-1]
                start_node = paths[j][0]
                
                try:
                    # Try to find the shortest path between these nodes
                    path = nx.astar_path(graph, end_node, start_node, 
                                       heuristic=lambda u, v: ox.distance.great_circle(
                                           graph.nodes[u]['y'], graph.nodes[u]['x'],
                                           graph.nodes[v]['y'], graph.nodes[v]['x']
                                       ),
                                       weight='length')
                    
                    # Calculate the total length of this connecting path
                    total_length = sum(graph.edges[path[k], path[k+1], 0]['length'] 
                                     for k in range(len(path)-1))
                    distance_matrix[i, j] = total_length
                except nx.NetworkXNoPath:
                    # If no path exists, use a very large number
                    distance_matrix[i, j] = float('inf')
    
    # Now solve the TSP to find the optimal order
    def solve_tsp(distance_matrix):
        n = len(distance_matrix)
        # Start with path 0
        path = [0]
        unvisited = set(range(1, n))
        
        while unvisited:
            current = path[-1]
            # Find the nearest unvisited path
            nearest = min(unvisited, key=lambda x: distance_matrix[current, x])
            path.append(nearest)
            unvisited.remove(nearest)
        
        return path
    
    # Get the optimal order
    optimal_order = solve_tsp(distance_matrix)
    
    # Calculate total distance
    total_distance = 0
    for i in range(len(optimal_order)-1):
        total_distance += distance_matrix[optimal_order[i], optimal_order[i+1]]
    
    return optimal_order, total_distance

def connect_optimal_path(graph, paths, optimal_order):
    """
    Plot the paths in their optimal order.
    
    Args:
        graph: OSMnx graph object
        paths: List of lists of node IDs
        optimal_order: List indicating the order to traverse the paths
    """
    
    # Plot the connecting paths between segments
    for i in range(len(optimal_order)-1):
        end_node = paths[optimal_order[i]][-1]
        start_node = paths[optimal_order[i+1]][0]
        try:
            connecting_path = nx.astar_path(graph, end_node, start_node,
                                          heuristic=lambda u, v: ox.distance.great_circle(
                                              graph.nodes[u]['y'], graph.nodes[u]['x'],
                                              graph.nodes[v]['y'], graph.nodes[v]['x']
                                          ),
                                          weight='length')
            connecting_lats = [graph.nodes[node]['y'] for node in connecting_path]
            connecting_lons = [graph.nodes[node]['x'] for node in connecting_path]
            ax.plot(connecting_lons, connecting_lats, 'k--', linewidth=3, alpha=0.8,
                   label='Connecting Path' if i == 0 else None)
        except nx.NetworkXNoPath:
            print(f"Warning: No path found between paths {i} and {i+1}")
    
    return connecting_path

def get_best_connected_path(graph, polyline_string, max_deviation=50):
    """
    Convert a polyline to points, find the best path, and plot it.
    
    Args:
        graph: OSMnx graph object
        polyline: Encoded polyline string
        max_deviation: Maximum allowed deviation in meters from original path
    """
    # Decode the polyline to get lat/lon points
    decoded_points = polyline.decode(polyline_string)
    
    # Find the best path through the graph
    paths = find_best_path_nodes(graph, decoded_points, max_deviation)

    optimal_order, total_distance = find_optimal_path_order(graph, paths)

    connecting_path =  connect_optimal_path(graph, paths, optimal_order)

    return connecting_path, total_distance