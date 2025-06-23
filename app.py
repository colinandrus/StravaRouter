from flask import Flask, render_template, request, jsonify
import strava_api
import polyline
import networkx as nx
import math
import osmnx as ox

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/update-segments', methods=['POST'])
def update_segments():
    data = request.json
    southwest = data.get('southwest')  # {'lat': value, 'lng': value}
    northeast = data.get('northeast')  # {'lat': value, 'lng': value}

    print(f"Received Coordinates - SW: {southwest}, NE: {northeast}")

    # Do something with the coordinates in Python
    # For example, save them to a database, use them in calculations, etc.
    
    lat_min = southwest['lat']
    lon_min = southwest['lng']
    lat_max = northeast['lat']
    lon_max = northeast['lng']

    access_token = strava_api.get_access_token(strava_api.CLIENT_ID, 
                strava_api.CLIENT_SECRET, strava_api.REFRESH_TOKEN)

    # Search for segments
    segments = strava_api.search_segments(lat_min, lon_min, lat_max, lon_max, access_token)
    
    #decode polyline to coordinates
    segments = segments['segments']
    for segment in segments:
        encoded_polyline = segment['points']
        decoded_points = polyline.decode(encoded_polyline)
        segment['points'] = decoded_points

    #return the segment results to page
    return jsonify(segments)

@app.route('/find-path', methods=['POST'])
def find_path():
    data = request.json
    segments = data.get('segments')
    start_point = data.get('start')  # {'lat': value, 'lng': value}
    end_point = data.get('end')      # {'lat': value, 'lng': value}

    # Create a graph from the segments
    G = nx.Graph()
    
    # Add all segment points as nodes and create edges
    for i, segment in enumerate(segments):
        points = segment['points']
        # Add nodes for each point in the segment
        for j in range(len(points) - 1):
            point1 = points[j]
            point2 = points[j + 1]
            
            # Calculate distance between points
            distance = calculate_distance(point1[0], point1[1], point2[0], point2[1])
            
            # Add edge with distance as weight
            G.add_edge(
                f"{i}_{j}", 
                f"{i}_{j+1}", 
                weight=distance,
                segment_id=segment['id']
            )

    # Find closest nodes to start and end points
    start_node = find_closest_node(G, start_point)
    end_node = find_closest_node(G, end_point)

    try:
        # Find shortest path
        path = nx.shortest_path(G, start_node, end_node, weight='weight')
        
        # Get the actual coordinates for the path
        path_coordinates = []
        for node in path:
            segment_idx, point_idx = map(int, node.split('_'))
            point = segments[segment_idx]['points'][point_idx]
            path_coordinates.append([point[0], point[1]])

        return jsonify({
            'path': path_coordinates,
            'distance': sum(G[path[i]][path[i+1]]['weight'] for i in range(len(path)-1))
        })
    except nx.NetworkXNoPath:
        return jsonify({'error': 'No path found'}), 404

@app.route('/best-path', methods=['POST'])
def best_path():
    try:
        data = request.json
        segments = data.get('segments')

        if not segments:
            return jsonify({'error': 'No segments provided'}), 400

        # Calculate bounding box from all segments
        all_points = []
        for segment in segments:
            all_points.extend(segment['points'])
        
        lats = [p[0] for p in all_points]
        lons = [p[1] for p in all_points]
        north, south = max(lats), min(lats)
        east, west = max(lons), min(lons)
        
        # Add padding to ensure we have enough road network
        padding = 0.001  # approximately 100m
        north += padding
        south -= padding
        east += padding
        west -= padding

        print(f"Building graph for bbox: {north}, {south}, {east}, {west}")

        # Get the OSMnx graph for the area using smallest boundary
        graph = get_graph_from_smallest_boundary(north, south, east, west, 'walk')
        
        if len(graph.nodes) == 0:
            return jsonify({'error': 'No road network found in the specified area'}), 404

        # Find the best path through all segments
        result = find_best_path_through_segments(graph, segments)

        return jsonify({
            'path': result['path'],
            'segments': result['segments'],
            'total_distance': result['total_distance'],
            'optimal_order': result['optimal_order'],
            'segments_covered': len(segments)
        })

    except Exception as e:
        print(f"Error in best_path: {str(e)}")
        return jsonify({'error': f'Error finding best path: {str(e)}'}), 500

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate the distance between two points using the Haversine formula"""
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def find_closest_node(G, point):
    """Find the closest node in the graph to a given point"""
    min_distance = float('inf')
    closest_node = None
    
    for node in G.nodes():
        segment_idx, point_idx = map(int, node.split('_'))
        node_point = segments[segment_idx]['points'][point_idx]
        
        distance = calculate_distance(point['lat'], point['lng'], node_point[0], node_point[1])
        if distance < min_distance:
            min_distance = distance
            closest_node = node
    
    return closest_node

def get_graph_from_smallest_boundary(north, south, east, west, network_type='walk'):
    """
    Get a graph from the smallest administrative boundary that contains the bounding box.
    
    Args:
        north, south, east, west: bounding box coordinates
        network_type: 'walk', 'bike', 'drive', etc.
    
    Returns:
        OSMnx graph object
    """
    # Calculate the center point of the bounding box
    center_lat = (north + south) / 2
    center_lon = (east + west) / 2
    
    print(f"Center point: {center_lat}, {center_lon}")
    
    try:
        # Try to get graph from point with a reasonable distance
        # Use 1000 meters radius to get a neighborhood-sized area
        graph = ox.graph.graph_from_point(
            (center_lat, center_lon),
            dist=1000,  # 1km radius
            network_type=network_type,
            simplify=True
        )
        print(f"Found graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges")
        return graph
    except Exception as e:
        print(f"Could not get point-based graph: {e}")
        print("Falling back to bounding box method...")
        
        # Fall back to bounding box method
        bbox = (north, south, east, west)
        graph = ox.graph.graph_from_bbox(*bbox, network_type=network_type)
        return graph

def find_best_path_through_segments(graph, segments):
    """
    Find the best path through all segments using the road network with optimal ordering.
    
    Args:
        graph: OSMnx graph object
        segments: List of segment objects with 'points' field
    
    Returns:
        Dictionary containing path coordinates and segment information
    """
    # Find the best path nodes for each segment
    paths = []
    for segment in segments:
        points = segment['points']
        path_nodes = strava_api.find_best_path_nodes(graph, points)
        paths.append(path_nodes)
    
    # Find the optimal order to traverse the segments
    optimal_order, total_distance = strava_api.find_optimal_path_order(graph, paths)
    
    # Define colors for segments
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
    
    # Build the complete path in optimal order with segment information
    complete_path = []
    segment_info = []
    current_segment_idx = 0
    
    for i, path_idx in enumerate(optimal_order):
        path_nodes = paths[path_idx]
        segment = segments[path_idx]
        color = colors[i % len(colors)]
        
        # Add segment info
        segment_info.append({
            'segment_id': segment.get('id', f'segment_{path_idx}'),
            'name': segment.get('name', f'Segment {i+1}'),
            'order': i + 1,
            'color': color,
            'start_idx': len(complete_path)
        })
        
        # Add the segment path
        for node in path_nodes:
            if node in graph.nodes:
                complete_path.append([graph.nodes[node]['y'], graph.nodes[node]['x']])
        
        # Add connecting path to next segment (except for the last segment)
        if i < len(optimal_order) - 1:
            end_node = path_nodes[-1]
            next_path_nodes = paths[optimal_order[i + 1]]
            start_node = next_path_nodes[0]
            
            try:
                # Find the shortest path between segments
                connecting_path = nx.astar_path(graph, end_node, start_node,
                                              heuristic=lambda u, v: ox.distance.great_circle(
                                                  graph.nodes[u]['y'], graph.nodes[u]['x'],
                                                  graph.nodes[v]['y'], graph.nodes[v]['x']
                                              ),
                                              weight='length')
                
                # Add the connecting path coordinates (in gray)
                for node in connecting_path:
                    if node in graph.nodes:
                        complete_path.append([graph.nodes[node]['y'], graph.nodes[node]['x']])
            except nx.NetworkXNoPath:
                # If no path found, add a straight line
                complete_path.append([graph.nodes[end_node]['y'], graph.nodes[end_node]['x']])
                complete_path.append([graph.nodes[start_node]['y'], graph.nodes[start_node]['x']])
        
        # Update end index for this segment
        segment_info[-1]['end_idx'] = len(complete_path) - 1
    
    return {
        'path': complete_path,
        'segments': segment_info,
        'total_distance': total_distance,
        'optimal_order': optimal_order
    }

if __name__ == '__main__':
    app.run(debug=True)
