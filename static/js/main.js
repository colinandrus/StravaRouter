// Initialize the map
var map = L.map('map').setView([40.730610, -73.935242], 13); // Default center (New York City)

// Add a tile layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Create a bounding box (rectangle) with initial coordinates
var bounds = L.latLngBounds([40.7122, -73.9632], [40.7377, -73.9302]);  // Example bounds
var rectangle = L.rectangle(bounds, {color: "#ff7800", weight: 1}).addTo(map);
map.fitBounds(bounds);

// Function to update the coordinates of the rectangle on the page
function updateRectangleCoordinates() {
    var sw = rectangle.getBounds().getSouthWest(); // Get southwest corner of the rectangle
    var ne = rectangle.getBounds().getNorthEast(); // Get northeast corner of the rectangle

    // Update the displayed coordinates on the page
    document.getElementById('sw-coords').innerText = sw.lat.toFixed(4) + ", " + sw.lng.toFixed(4);
    document.getElementById('ne-coords').innerText = ne.lat.toFixed(4) + ", " + ne.lng.toFixed(4);
}

// Update the coordinates when the page is loaded
updateRectangleCoordinates();

// Optional: Update the coordinates when the user interacts with the rectangle (e.g., dragging the box)
rectangle.on('edit', updateRectangleCoordinates);

// Optional: Update the coordinates when the user interacts with the map
map.on('mouseup', updateRectangleCoordinates);
