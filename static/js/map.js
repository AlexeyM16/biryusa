const map = L.map('map').setView([55.88, 92.12], 11);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
}).addTo(map);

const PREDEFINED_POINTS = {
    "Дивногорск": [55.9584, 92.3558],
    "Полынья": [55.9100, 92.2500],
    "Лёд-1": [55.9300, 92.1500],
    "Камни": [55.8500, 92.2800],
    "Болото": [55.8800, 92.1000],
    "Узел-М": [55.8200, 92.0500],
    "Шуга": [55.7800, 92.1200],
    "Чисто": [55.7900, 91.9500],
    "Бирюса": [55.7500, 91.9000]
};

for (const [name, coords] of Object.entries(PREDEFINED_POINTS)) {
    L.circleMarker(coords, {
        color: '#64748b',
        fillColor: '#cbd5e1',
        fillOpacity: 0.8,
        radius: 6
    }).addTo(map).bindPopup(`<b>${name}</b>`);
}

let startPoint = null, endPoint = null;
let startMarker = null, endMarker = null, routeLine = null;

function updateMapMarkers(startVal, endVal) {
    if (startMarker) map.removeLayer(startMarker);
    if (endMarker) map.removeLayer(endMarker);
    if (routeLine) map.removeLayer(routeLine);

    if (startVal) {
        const [lat, lon] = startVal.split(',').map(Number);
        startPoint = { lat, lon };
        startMarker = L.circleMarker([lat, lon], {
            color: '#0284c7',
            fillColor: '#0ea5e9',
            fillOpacity: 1,
            radius: 8
        }).addTo(map);
    } else startPoint = null;

    if (endVal) {
        const [lat, lon] = endVal.split(',').map(Number);
        endPoint = { lat, lon };
        endMarker = L.circleMarker([lat, lon], {
            color: '#0f172a',
            fillColor: '#334155',
            fillOpacity: 1,
            radius: 8
        }).addTo(map);
    } else endPoint = null;
}

function handleMapClick(e, clearSelectsCallback) {
    clearSelectsCallback();
    if (routeLine) map.removeLayer(routeLine);

    if (!startPoint || (startPoint && endPoint)) {
        startPoint = { lat: e.latlng.lat, lon: e.latlng.lng };
        endPoint = null;
        if (startMarker) map.removeLayer(startMarker);
        if (endMarker) map.removeLayer(endMarker);
        startMarker = L.circleMarker([startPoint.lat, startPoint.lon], {
            color: '#0284c7',
            fillColor: '#0ea5e9',
            fillOpacity: 1,
            radius: 8
        }).addTo(map);
    } else {
        endPoint = { lat: e.latlng.lat, lon: e.latlng.lng };
        endMarker = L.circleMarker([endPoint.lat, endPoint.lon], {
            color: '#0f172a',
            fillColor: '#334155',
            fillOpacity: 1,
            radius: 8
        }).addTo(map);
    }
}

function drawRouteLine(coords) {
    if (routeLine) map.removeLayer(routeLine);
    routeLine = L.polyline(coords, {
        color: '#0284c7',
        weight: 4,
        opacity: 0.9,
        lineCap: 'square'
    }).addTo(map);
    map.fitBounds(routeLine.getBounds());
}