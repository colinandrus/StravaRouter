// Initialize the map
var map = L.map('map').setView([40.730610, -73.935242], 13); // Default center (New York City)

// Add a tile layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
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
    },
    edit: {
        featureGroup: new L.FeatureGroup() // Empty layer group to store editable layers
    }
});
map.addControl(drawControl);

// Create a feature group to store rectangles
var drawnItems = new L.FeatureGroup().addTo(map);

// Function to update rectangle coordinates
function updateRectangleCoordinates(layer) {
    var sw = layer.getBounds().getSouthWest();
    var ne = layer.getBounds().getNorthEast();

    document.getElementById('sw-coords').innerText = sw.lat.toFixed(4) + ", " + sw.lng.toFixed(4);
    document.getElementById('ne-coords').innerText = ne.lat.toFixed(4) + ", " + ne.lng.toFixed(4);
}

// Listen for when a rectangle is created
map.on('draw:created', function (e) {
    var layer = e.layer;

    // Clear previously drawn items and add the new rectangle
    drawnItems.clearLayers();
    drawnItems.addLayer(layer);

    // Update coordinates
    updateRectangleCoordinates(layer);

    // Add listeners for drag and resize
    layer.on('edit', function () {
        updateRectangleCoordinates(layer);
    });
});

// Add edit capabilities to the rectangle
map.on('draw:edited', function (e) {
    e.layers.eachLayer(function (layer) {
        updateRectangleCoordinates(layer);
    });
});
