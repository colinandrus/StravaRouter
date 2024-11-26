from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/update-coordinates', methods=['POST'])
def update_coordinates():
    data = request.json
    southwest = data.get('southwest')  # {'lat': value, 'lng': value}
    northeast = data.get('northeast')  # {'lat': value, 'lng': value}

    print(f"Received Coordinates - SW: {southwest}, NE: {northeast}")

    # Do something with the coordinates in Python
    # For example, save them to a database, use them in calculations, etc.

    print(jsonify({"message": "Coordinates received", "status": "success"}))

if __name__ == '__main__':
    app.run(debug=True)
