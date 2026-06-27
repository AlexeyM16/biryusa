// Инициализация карты (центруем между Дивногорском и Бирюсой)
const map = L.map('map').setView([55.88, 92.12], 11);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
}).addTo(map);

// Предустановленные точки для маркеров
const PREDEFINED_POINTS = {
    "Дивногорск (Адмирал)": [55.928746, 92.275371],
    "Залив Бирюса": [55.859435, 92.249132],
    "Верхняя Бирюса": [55.922724, 91.971605],
    "Царские ворота": [55.840816, 92.164664],
    "залив Кызыреева": [55.822157, 92.133623],
    "Жемчужина": [55.902116, 92.247447]
};

// Добавляем маркеры-подсказки на карту
for (const [name, coords] of Object.entries(PREDEFINED_POINTS)) {
    L.marker(coords).addTo(map).bindPopup(`<b>${name}</b>`);
}

// Глобальные переменные состояния
let startPoint = null;
let endPoint = null;
let startMarker = null;
let endMarker = null;
let routeLine = null;

// Элементы UI
const startSelect = document.getElementById('start-point');
const endSelect = document.getElementById('end-point');

// --- ЛОГИКА ФИЛЬТРОВ И КЛИКОВ ---

// Обновление маркеров на основе селектов
function updateFromSelects() {
    if (startMarker) map.removeLayer(startMarker);
    if (endMarker) map.removeLayer(endMarker);
    if (routeLine) map.removeLayer(routeLine);
    document.getElementById('results').style.display = 'none';

    if (startSelect.value) {
        const [lat, lon] = startSelect.value.split(',').map(Number);
        startPoint = { lat, lon };
        startMarker = L.circleMarker([lat, lon], {color: 'green', radius: 8}).addTo(map);
    } else {
        startPoint = null;
    }

    if (endSelect.value) {
        const [lat, lon] = endSelect.value.split(',').map(Number);
        endPoint = { lat, lon };
        endMarker = L.circleMarker([lat, lon], {color: 'red', radius: 8}).addTo(map);
    } else {
        endPoint = null;
    }
}

// Слушатели для выпадающих списков
startSelect.addEventListener('change', updateFromSelects);
endSelect.addEventListener('change', updateFromSelects);

// Слушатель клика по карте
map.on('click', function(e) {
    // Сбрасываем селекты, так как юзер перешел на ручной выбор
    startSelect.value = "";
    endSelect.value = "";
    document.getElementById('results').style.display = 'none';
    if (routeLine) map.removeLayer(routeLine);

    if (!startPoint || (startPoint && endPoint)) {
        // Ставим старт
        startPoint = { lat: e.latlng.lat, lon: e.latlng.lng };
        endPoint = null;
        if (startMarker) map.removeLayer(startMarker);
        if (endMarker) map.removeLayer(endMarker);
        startMarker = L.circleMarker([startPoint.lat, startPoint.lon], {color: 'green', radius: 8}).addTo(map);
    } else {
        // Ставим финиш
        endPoint = { lat: e.latlng.lat, lon: e.latlng.lng };
        endMarker = L.circleMarker([endPoint.lat, endPoint.lon], {color: 'red', radius: 8}).addTo(map);
    }
});

// --- СВЯЗЬ С БЭКЕНДОМ ---

async function calculateRoute() {
    if (!startPoint || !endPoint) {
        alert("Пожалуйста, выберите точку отправления и назначения (на карте или в списке)!");
        return;
    }

    // Дефолтные координаты для проверки, не промахнулся ли юзер мимо базы
    const BIRYUSA_DEFAULT_LAT = 55.859435;
    const BIRYUSA_DEFAULT_LON = 92.249132;
    const ADMIRAL_DEFAULT_LAT = 55.928746;
    const ADMIRAL_DEFAULT_LON = 92.275371;

    // Точные координаты самих пирсов, куда надо лочить маршрут
    const BIRYUSA_PIER_LAT = 55.858841;
    const BIRYUSA_PIER_LON = 92.244493;
    const ADMIRAL_PIER_LAT = 55.928746; // Базовые координаты Адмирала уже на воде
    const ADMIRAL_PIER_LON = 92.275371;

    // Функция-магнит: если тыкнули в радиусе 1.5 км от базы, возвращаем точные корды пирса
    function snapToPier(lat, lon) {
        if (Math.hypot(lat - BIRYUSA_DEFAULT_LAT, lon - BIRYUSA_DEFAULT_LON) < 0.015) {
            return { lat: BIRYUSA_PIER_LAT, lon: BIRYUSA_PIER_LON };
        }
        if (Math.hypot(lat - ADMIRAL_DEFAULT_LAT, lon - ADMIRAL_DEFAULT_LON) < 0.015) {
            return { lat: ADMIRAL_PIER_LAT, lon: ADMIRAL_PIER_LON };
        }
        return { lat: lat, lon: lon };
    }

    // Применяем притяжение и к старту, и к финишу!
    const finalStart = snapToPier(startPoint.lat, startPoint.lon);
    const finalEnd = snapToPier(endPoint.lat, endPoint.lon);

    const payload = {
        s_lat: finalStart.lat,
        s_lon: finalStart.lon,
        e_lat: finalEnd.lat,
        e_lon: finalEnd.lon,
        config: document.getElementById('boat-config').value,
        mode: document.getElementById('boat-mode').value,
        passengers: parseInt(document.getElementById('passengers').value) || 0,
        temp: parseFloat(document.getElementById('temperature').value) || 0,
        oil: parseFloat(document.getElementById('oil-level').value) || 100
    };

    try {
        const response = await fetch('/calculate-route', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.error) {
            alert("Ошибка: " + data.error);
            return;
        }

        // Отрисовка маршрута на карте (цвет красный)
        if (routeLine) map.removeLayer(routeLine);
        routeLine = L.polyline(data.coords, {color: 'red', weight: 4}).addTo(map);
        map.fitBounds(routeLine.getBounds());

        // Заполнение результатов в UI
        document.getElementById('res-km').innerText = data.km;
        document.getElementById('res-time').innerText = data.time_h;
        document.getElementById('res-fuel').innerText = data.fuel_l;
        document.getElementById('res-rem').innerText = data.remainder_l;
        document.getElementById('res-depth').innerText = data.avg_depth_m;
        document.getElementById('res-oil').innerText = data.oil_end_pct;
        document.getElementById('res-risk').innerText = data.max_risk;

        // Вывод предупреждений
        const warningsDiv = document.getElementById('res-warnings');
        if (data.warnings && data.warnings.length > 0) {
            warningsDiv.innerHTML = "⚠️ " + data.warnings.join('<br>⚠️ ');
        } else {
            warningsDiv.innerHTML = "<span style='color:green;'>✓ Маршрут безопасен</span>";
        }

        document.getElementById('results').style.display = 'block';

    } catch (err) {
        console.error(err);
        alert("Не удалось связаться с сервером.");
    }
}