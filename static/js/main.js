// Initialize the map
var map = L.map('map').setView([40.730610, -73.935242], 13); // Default center (New York City)

// Add a tile layer
// Add a grayscale tile layer
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19
}).addTo(map);

// Add Leaflet Draw controls
var drawControl = new L.Control.Draw({
    draw: {
        polyline: false,
        polygon: false,
        circle: false,
        marker: false,
        circlemarker: false,
        rectangle: {
            shapeOptions: {
                color: '#ff7800',
                weight: 2
            }
        }
    }
});

map.addControl(drawControl);

// Create a feature group to store rectangles
var drawnItems = new L.FeatureGroup().addTo(map);

// Function to update rectangle coordinates in the UI
function updateCoordinates(sw, ne) {
    document.getElementById('sw-coords').innerText = `${sw.lat.toFixed(4)}, ${sw.lng.toFixed(4)}`;
    document.getElementById('ne-coords').innerText = `${ne.lat.toFixed(4)}, ${ne.lng.toFixed(4)}`;
}

// Function to send a POST request with the coordinates
function sendPostRequest(data) {
    return fetch('/update-segments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(response => response.json());
}

// Function to handle the response from the server
function handleResponse(result) {
    try {
        let segments = JSON.parse(result['returned-segments']);
        document.getElementById('returned-segments').innerText = segments.length ? segments[0].name : "No segments found";
    } catch (error) {
        console.error("Error parsing segments:", error);
    }
}

// Main function to update rectangle coordinates
function updateRectangleCoordinates(layer) {
    var sw = layer.getBounds().getSouthWest();
    var ne = layer.getBounds().getNorthEast();

    updateCoordinates(sw, ne);

    var data = {
        southwest: { lat: sw.lat, lng: sw.lng },
        northeast: { lat: ne.lat, lng: ne.lng }
    };

    sendPostRequest(data)
        .then(result => handleResponse(result))
        .catch(error => console.error('Error:', error));
}


// Listen for when a rectangle is created
map.on('draw:created', function (e) {
    var layer = e.layer;

    // Clear previously drawn items and add the new rectangle
    drawnItems.clearLayers();
    drawnItems.addLayer(layer);

    // Update coordinates
    updateRectangleCoordinates(layer);
});


