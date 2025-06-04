from flask import Flask, render_template, request, jsonify
import strava_api
import polyline
import networkx as nx
import math

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

if __name__ == '__main__':
    app.run(debug=True)
