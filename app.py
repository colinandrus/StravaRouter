from flask import Flask, render_template, request, jsonify
import strava_api
import polyline

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

if __name__ == '__main__':
    app.run(debug=True)
