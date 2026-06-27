if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(reg => console.log('Offline-модуль загружен.', reg.scope))
            .catch(err => console.error('Ошибка Offline-модуля:', err));
    });
}

function updateNetworkStatus() {
    const badge = document.getElementById('network-badge');
    if (navigator.onLine) {
        badge.className = 'badge online';
        badge.innerText = 'СИНХРОНИЗИРОВАНО';
    } else {
        badge.className = 'badge offline';
        badge.innerText = 'АВТОНОМНЫЙ РЕЖИМ';
    }
}

window.addEventListener('online', updateNetworkStatus);
window.addEventListener('offline', updateNetworkStatus);

document.addEventListener("DOMContentLoaded", () => {
    const now = new Date();
    now.setHours(now.getHours() - 2);
    document.getElementById('sync-time').innerText = now.toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
    });
    updateNetworkStatus();

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

    document.getElementById('current-fuel').addEventListener('input', (e) => {
        document.getElementById('fuel-value-display').innerText = e.target.value;
    });

    document.getElementById('calc-btn').addEventListener('click', calculateRouteApi);
    document.getElementById('test-btn').addEventListener('click', openTestPanel);
    document.getElementById('close-test-btn').addEventListener('click', closeTestPanel);
    document.getElementById('back-graph-btn').addEventListener('click', backToTable);
    document.getElementById('download-btn').addEventListener('click', downloadAnswers);
});

async function calculateRouteApi() {
    if (!startPoint || !endPoint) {
        alert("ОШИБКА: Выберите точку отправления и назначения (на карте или в списке).");
        return;
    }

    const payload = {
        s_lat: startPoint.lat,
        s_lon: startPoint.lon,
        e_lat: endPoint.lat,
        e_lon: endPoint.lon,
        config: document.getElementById('boat-config').value,
        mode: document.getElementById('boat-mode').value,
        passengers: parseInt(document.getElementById('passengers').value) || 0,
        temp: parseFloat(document.getElementById('temperature').value) || 0,
        oil: parseFloat(document.getElementById('oil-level').value) || 100,
        current_fuel: parseFloat(document.getElementById('current-fuel').value) || 370
    };

    document.getElementById('results').style.display = 'none';
    const loadingBar = document.getElementById('loading-bar');
    loadingBar.classList.remove('hidden');

    try {
        const response = await fetch('/calculate-route', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        loadingBar.classList.add('hidden');

        if (data.error) {
            alert("ОШИБКА: " + data.error);
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
        warningsDiv.innerHTML = "";

        let routeHtml = "";
        if (data.route_nodes) {
            routeHtml = `<div style="margin-bottom:12px; font-size: 0.85rem; color: #334155;"><b>ПУТЬ:</b> ${data.route_nodes}</div>`;
        }

        if (data.warnings && data.warnings.length > 0) {
            let warningsHtml = data.warnings.map(w => `<div class="warning-item">${w}</div>`).join('');
            warningsDiv.innerHTML = routeHtml + warningsHtml;
        } else {
            warningsDiv.innerHTML = routeHtml + "<div class='status-ok'>СТАТУС: МАРШРУТ БЕЗОПАСЕН</div>";
        }

        document.getElementById('results').style.display = 'block';

    } catch (err) {
        console.error(err);
        loadingBar.classList.add('hidden');
        alert("СИСТЕМНАЯ ОШИБКА: Не удалось связаться с сервером.");
    }
}