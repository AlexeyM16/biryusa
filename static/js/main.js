document.addEventListener("DOMContentLoaded", () => {
    const startSelect = document.getElementById('start-point');
    const endSelect = document.getElementById('end-point');

    startSelect.addEventListener('change', () => {
        updateMapMarkers(startSelect.value, endSelect.value);
        document.getElementById('results').style.display = 'none';
    });

    endSelect.addEventListener('change', () => {
        updateMapMarkers(startSelect.value, endSelect.value);
        document.getElementById('results').style.display = 'none';
    });

    map.on('click', (e) => {
        handleMapClick(e, () => {
            startSelect.value = "";
            endSelect.value = "";
            document.getElementById('results').style.display = 'none';
        });
    });

    // Навешиваем обработчики кнопок
    document.getElementById('calc-btn').addEventListener('click', calculateRouteApi);
    document.getElementById('test-btn').addEventListener('click', openTestPanel);
    document.getElementById('close-test-btn').addEventListener('click', closeTestPanel);
    document.getElementById('back-graph-btn').addEventListener('click', backToTable);
    document.getElementById('download-btn').addEventListener('click', downloadAnswers);
});

async function calculateRouteApi() {
    if (!startPoint || !endPoint) {
        alert("Пожалуйста, выберите точку отправления и назначения (на карте или в списке)!");
        return;
    }

    const BIRYUSA_DEFAULT_LAT = 55.859435;
    const BIRYUSA_DEFAULT_LON = 92.249132;
    const ADMIRAL_DEFAULT_LAT = 55.928746;
    const ADMIRAL_DEFAULT_LON = 92.275371;

    const BIRYUSA_PIER_LAT = 55.858841;
    const BIRYUSA_PIER_LON = 92.244493;
    const ADMIRAL_PIER_LAT = 55.928746;
    const ADMIRAL_PIER_LON = 92.275371;

    function snapToPier(lat, lon) {
        if (Math.hypot(lat - BIRYUSA_DEFAULT_LAT, lon - BIRYUSA_DEFAULT_LON) < 0.015) {
            return { lat: BIRYUSA_PIER_LAT, lon: BIRYUSA_PIER_LON };
        }
        if (Math.hypot(lat - ADMIRAL_DEFAULT_LAT, lon - ADMIRAL_DEFAULT_LON) < 0.015) {
            return { lat: ADMIRAL_PIER_LAT, lon: ADMIRAL_PIER_LON };
        }
        return { lat: lat, lon: lon };
    }

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

        drawRouteLine(data.coords);

        document.getElementById('res-km').innerText = data.km;
        document.getElementById('res-time').innerText = data.time_h;
        document.getElementById('res-fuel').innerText = data.fuel_l;
        document.getElementById('res-rem').innerText = data.remainder_l;
        document.getElementById('res-depth').innerText = data.avg_depth_m;
        document.getElementById('res-oil').innerText = data.oil_end_pct;
        document.getElementById('res-risk').innerText = data.max_risk;

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