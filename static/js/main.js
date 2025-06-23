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
        let pathDetailsContainer = document.getElementById('path-details');
        let legendContainer = document.getElementById('legend-items');

        // Clear any existing content in the containers
        segmentsContainer.innerHTML = "";
        pathDetailsContainer.innerHTML = "";
        legendContainer.innerHTML = "";

        // Clear any existing segment polylines from the map
        if (window.segmentLayers) {
            window.segmentLayers.clearLayers();
        } else {
            window.segmentLayers = new L.FeatureGroup().addTo(map);
        }

        // Store segments globally for path finding
        window.currentSegments = segments;

        // Define colors for segments
        const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9'];

        // Loop through each segment and create a paragraph for each
        segments.forEach((segment, index) => {
            const color = colors[index % colors.length];
            
            let segmentText = document.createElement('p');
            segmentText.style.marginBottom = '8px';
            segmentText.style.display = 'flex';
            segmentText.style.alignItems = 'center';
            segmentText.innerHTML = `
                <div style="
                    width: 20px; 
                    height: 8px; 
                    background-color: ${color}; 
                    margin-right: 8px;
                    border-radius: 2px;
                "></div>
                <span><strong>${segment.name}</strong>: ${segment.distance} meters</span>
            `;
            segmentsContainer.appendChild(segmentText);

            // Draw the segment on the map
            if (segment.points && segment.points.length > 0) {
                const polyline = L.polyline(segment.points, {
                    color: color,
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

        // Automatically find and display the best path through all segments
        findBestPath();

    } catch (error) {
        console.error("Error handling response:", error);
    }
}

// Function to find the best path through all segments
async function findBestPath() {
    if (!window.currentSegments) return;

    // Get the current bounding box from the UI
    const swText = document.getElementById('sw-coords').innerText.split(',');
    const neText = document.getElementById('ne-coords').innerText.split(',');
    if (swText.length < 2 || neText.length < 2) return;
    const sw = { lat: parseFloat(swText[0]), lng: parseFloat(swText[1]) };
    const ne = { lat: parseFloat(neText[0]), lng: parseFloat(neText[1]) };

    try {
        const response = await fetch('/best-path', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                southwest: sw,
                northeast: ne,
                segments: window.currentSegments
            })
        });
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const result = await response.json();

        // Clear existing path layers
        if (window.pathLayer) {
            window.pathLayer.clearLayers();
        } else {
            window.pathLayer = new L.FeatureGroup().addTo(map);
        }

        // Draw each segment in its assigned color
        if (result.segments && result.path) {
            result.segments.forEach(segment => {
                const segmentPath = result.path.slice(segment.start_idx, segment.end_idx + 1);
                if (segmentPath.length > 1) {
                    const polyline = L.polyline(segmentPath, {
                        color: segment.color,
                        weight: 6,
                        opacity: 0.9
                    }).addTo(window.pathLayer);

                    // Add popup with segment info
                    polyline.bindPopup(`<strong>${segment.name}</strong><br>Order: ${segment.order}<br>Color: ${segment.color}`);
                }
            });
        }

        // Update path information
        let pathDetailsContainer = document.getElementById('path-details');
        let legendContainer = document.getElementById('legend-items');
        
        pathDetailsContainer.innerHTML = `
            <p><strong>Total Distance:</strong> ${(result.total_distance || 0).toFixed(0)} meters</p>
            <p><strong>Segments Covered:</strong> ${result.segments_covered}</p>
        `;

        // Create legend
        legendContainer.innerHTML = '';
        if (result.segments) {
            result.segments.forEach(segment => {
                const legendItem = document.createElement('div');
                legendItem.style.marginBottom = '8px';
                legendItem.style.display = 'flex';
                legendItem.style.alignItems = 'center';
                legendItem.innerHTML = `
                    <div style="
                        width: 20px; 
                        height: 8px; 
                        background-color: ${segment.color}; 
                        margin-right: 8px;
                        border-radius: 2px;
                    "></div>
                    <span><strong>${segment.order}.</strong> ${segment.name}</span>
                `;
                legendContainer.appendChild(legendItem);
            });
        }

    } catch (error) {
        console.error("Error finding best path:", error);
        let pathDetailsContainer = document.getElementById('path-details');
        pathDetailsContainer.innerHTML = `<p>Error finding best path: ${error.message}</p>`;
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
