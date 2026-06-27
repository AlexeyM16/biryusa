const map = L.map('map').setView([55.88, 92.12], 11);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
}).addTo(map);

const PREDEFINED_POINTS = {
    "Дивногорск (Адмирал)": [55.928746, 92.275371],
    "Залив Бирюса": [55.859435, 92.249132],
    "Верхняя Бирюса": [55.922724, 91.971605],
    "Царские ворота": [55.840816, 92.164664],
    "залив Кызыреева": [55.822157, 92.133623],
    "Жемчужина": [55.902116, 92.247447]
};

for (const [name, coords] of Object.entries(PREDEFINED_POINTS)) {
    L.marker(coords).addTo(map).bindPopup(`<b>${name}</b>`);
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
        startMarker = L.circleMarker([lat, lon], {color: 'green', radius: 8}).addTo(map);
    } else startPoint = null;

    if (endVal) {
        const [lat, lon] = endVal.split(',').map(Number);
        endPoint = { lat, lon };
        endMarker = L.circleMarker([lat, lon], {color: 'red', radius: 8}).addTo(map);
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
        startMarker = L.circleMarker([startPoint.lat, startPoint.lon], {color: 'green', radius: 8}).addTo(map);
    } else {
        endPoint = { lat: e.latlng.lat, lon: e.latlng.lng };
        endMarker = L.circleMarker([endPoint.lat, endPoint.lon], {color: 'red', radius: 8}).addTo(map);
    }
}

function drawRouteLine(coords) {
    if (routeLine) map.removeLayer(routeLine);
    routeLine = L.polyline(coords, {color: 'red', weight: 4}).addTo(map);
    map.fitBounds(routeLine.getBounds());
}