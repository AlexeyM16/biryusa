let currentTestResults = [];

async function openTestPanel() {
    document.getElementById('test-panel').classList.add('open');
    document.getElementById('test-content').innerHTML = "<b>Прогоняем модель...</b>";
    backToTable();

    try {
        const res = await fetch('/run-tests');
        const data = await res.json();
        currentTestResults = data.tests;

        let html = `<table class="test-table">
            <thead>
                <tr>
                    <th>Конфигурация</th>
                    <th>Режим</th>
                    <th>Результат Модели</th>
                    <th>Граф</th>
                </tr>
            </thead>
            <tbody>`;

        data.tests.forEach((t) => {
            html += `
            <tr>
                <td><b>${t.config}</b></td>
                <td>${t.mode}</td>
                <td>
                    ⏱ ${t.actual.time_h} ч<br>
                    ⛽ ${t.actual.fuel_l} л<br>
                    ⚠ Риск: ${t.actual.max_risk}<br>
                    <small>${t.actual.route}</small>
                </td>
                <td style="text-align:center;">
                    <button class="btn-show-graph" onclick="window.showGraph('${t.actual.route}')">Показать</button>
                </td>
            </tr>`;
        });

        html += `</tbody></table>`;
        document.getElementById('test-content').innerHTML = html;

    } catch (err) {
        document.getElementById('test-content').innerHTML = "<span style='color:red;'>Ошибка загрузки тестов. Проверьте консоль.</span>";
    }
}

function closeTestPanel() {
    document.getElementById('test-panel').classList.remove('open');
    backToTable();
}

window.showGraph = function(routeString) {
    document.getElementById('test-table-container').classList.add('hidden');
    document.getElementById('graph-view').classList.remove('hidden');

    const canvas = document.getElementById('graph-canvas');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const nodes = {
        "Дивногорск": {x: 60, y: 200},
        "Болото": {x: 200, y: 60},
        "Лёд-1": {x: 200, y: 150},
        "Камни": {x: 200, y: 250},
        "Полынья": {x: 200, y: 340},
        "Узел-М": {x: 350, y: 200},
        "Шуга": {x: 480, y: 120},
        "Чисто": {x: 480, y: 280},
        "Бирюса": {x: 560, y: 200}
    };

    const edges = [
        ["Дивногорск","Полынья"], ["Дивногорск","Лёд-1"],
        ["Дивногорск","Камни"], ["Дивногорск","Болото"],
        ["Полынья","Узел-М"], ["Лёд-1","Узел-М"],
        ["Камни","Узел-М"], ["Болото","Узел-М"],
        ["Узел-М","Шуга"], ["Узел-М","Чисто"],
        ["Шуга","Бирюса"], ["Чисто","Бирюса"]
    ];

    const pathNodes = routeString.split(" → ");

    ctx.lineWidth = 2;
    ctx.strokeStyle = '#e0e0e0';
    edges.forEach(e => {
        if(nodes[e[0]] && nodes[e[1]]) {
            ctx.beginPath();
            ctx.moveTo(nodes[e[0]].x, nodes[e[0]].y);
            ctx.lineTo(nodes[e[1]].x, nodes[e[1]].y);
            ctx.stroke();
        }
    });

    ctx.lineWidth = 4;
    ctx.strokeStyle = '#e74c3c';
    for(let i=0; i < pathNodes.length - 1; i++) {
        const n1 = pathNodes[i];
        const n2 = pathNodes[i+1];
        if(nodes[n1] && nodes[n2]) {
            ctx.beginPath();
            ctx.moveTo(nodes[n1].x, nodes[n1].y);
            ctx.lineTo(nodes[n2].x, nodes[n2].y);
            ctx.stroke();
        }
    }

    Object.keys(nodes).forEach(k => {
        const isActive = pathNodes.includes(k);
        ctx.beginPath();
        ctx.arc(nodes[k].x, nodes[k].y, 8, 0, 2*Math.PI);
        ctx.fillStyle = isActive ? '#e74c3c' : '#95a5a6';
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.fillStyle = '#2c3e50';
        ctx.font = isActive ? 'bold 13px Arial' : '13px Arial';
        ctx.fillText(k, nodes[k].x - 20, nodes[k].y - 12);
    });
};

function backToTable() {
    document.getElementById('graph-view').classList.add('hidden');
    document.getElementById('test-table-container').classList.remove('hidden');
}

function downloadAnswers() {
    if (currentTestResults.length === 0) return;
    const answers = currentTestResults.map(t => ({
        mode: t.mode,
        config: t.config,
        route: t.actual.route,
        time_h: t.actual.time_h,
        fuel_l: t.actual.fuel_l,
        max_risk: t.actual.max_risk,
        remainder_l: t.actual.remainder_l
    }));

    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(answers, null, 2));
    const anchor = document.createElement('a');
    anchor.setAttribute("href", dataStr);
    anchor.setAttribute("download", "answers.json");
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
}