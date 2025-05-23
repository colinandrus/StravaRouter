// Initialize the map
var map = L.map('map').setView([40.730610, -73.935242], 13); // Default center (New York City)

// Add a tile layer
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
async function sendPostRequest(data) {
    try {
        const response = await fetch('/update-segments', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Error during POST request:", error);
        throw error;
    }
}

// Function to handle the response from the server
function handleResponse(segments) {
    try {
        let segmentsContainer = document.getElementById('returned-segments');

        // Clear any existing content in the container before appending new segments
        segmentsContainer.innerHTML = "";

        // Clear any existing segment polylines from the map
        if (window.segmentLayers) {
            window.segmentLayers.clearLayers();
        } else {
            window.segmentLayers = new L.FeatureGroup().addTo(map);
        }

        // Loop through each segment and create a paragraph for each
        segments.forEach(segment => {
            let segmentText = document.createElement('p');
            segmentText.innerHTML = `<strong>${segment.name}</strong>: ${segment.distance} meters`;
            segmentsContainer.appendChild(segmentText);

            // Draw the segment on the map
            if (segment.points && segment.points.length > 0) {
                const polyline = L.polyline(segment.points, {
                    color: '#ff7800',
                    weight: 3,
                    opacity: 0.7
                }).addTo(window.segmentLayers);

                // Add popup with segment info
                polyline.bindPopup(`<strong>${segment.name}</strong><br>Distance: ${segment.distance} meters`);
            }
        });

        // If no segments are found, display a message
        if (segments.length === 0) {
            segmentsContainer.innerHTML = "No segments found.";
        }

    } catch (error) {
        console.error("Error handling response:", error);
    }
}

// Main function to update rectangle coordinates
async function updateRectangleCoordinates(layer) {
    var sw = layer.getBounds().getSouthWest();
    var ne = layer.getBounds().getNorthEast();

    updateCoordinates(sw, ne);

    var data = {
        southwest: { lat: sw.lat, lng: sw.lng },
        northeast: { lat: ne.lat, lng: ne.lng }
    };

    try {
        const result = await sendPostRequest(data);
        handleResponse(result);
    } catch (error) {
        console.error("Error during updateRectangleCoordinates:", error);
    }
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
