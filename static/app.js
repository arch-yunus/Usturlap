document.getElementById('calculate-btn').addEventListener('click', async () => {
    const datetime = document.getElementById('datetime').value;
    const lat = document.getElementById('lat').value;
    const lon = document.getElementById('lon').value;
    const lang = document.getElementById('lang').value;

    const chartContainer = document.getElementById('chart-visual');
    const interpretContent = document.getElementById('interpret-content');

    chartContainer.innerHTML = '<div class="placeholder">Yükleniyor...</div>';
    interpretContent.innerText = 'Analiz hazırlanıyor...';

    try {
        // 1. Fetch Chart SVG
        const chartUrl = `/api/v1/chart/draw?datetime=${datetime}:00Z&lat=${lat}&lon=${lon}&lang=${lang}`;
        const chartRes = await fetch(chartUrl);
        if (!chartRes.ok) throw new Error('Harita çizilemedi.');
        const svg = await chartRes.text();
        chartContainer.innerHTML = svg;

        // 2. Fetch Interpretation
        // Note: For interpretation we need the full chart data first
        const dataUrl = `/api/v1/chart?datetime=${datetime}:00Z&lat=${lat}&lon=${lon}&lang=${lang}`;
        const dataRes = await fetch(dataUrl);
        const chartData = await dataRes.json();

        const interpretRes = await fetch(`/api/v1/interpret?lang=${lang}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chart_data: chartData, interpretation_type: 'professional' })
        });
        const interpretData = await interpretRes.json();
        interpretContent.innerText = interpretData.interpretation;

    } catch (error) {
        chartContainer.innerHTML = `<div class="placeholder" style="color: #ef4444">Hata: ${error.message}</div>`;
        interpretContent.innerText = 'Hesaplama sırasında bir sorun oluştu.';
    }
});

document.getElementById('download-pdf-btn').addEventListener('click', () => {
    const datetime = document.getElementById('datetime').value;
    const lat = document.getElementById('lat').value;
    const lon = document.getElementById('lon').value;
    const lang = document.getElementById('lang').value;
    window.location.href = `/api/v1/chart/report/pdf?datetime=${datetime}:00Z&lat=${lat}&lon=${lon}&lang=${lang}`;
});

document.getElementById('save-chart-btn').addEventListener('click', async () => {
    const name = prompt("Harita için bir isim girin:");
    if (!name) return;

    const data = {
        name: name,
        datetime: document.getElementById('datetime').value + ":00",
        lat: parseFloat(document.getElementById('lat').value),
        lon: parseFloat(document.getElementById('lon').value),
        house_system: "placidus"
    };

    const res = await fetch('/api/v1/charts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (res.ok) {
        alert("Harita başarıyla kaydedildi!");
        loadHistory();
    }
});

async function loadHistory() {
    const res = await fetch('/api/v1/charts');
    const charts = await res.json();
    const list = document.getElementById('history-list');
    list.innerHTML = charts.length ? '' : '<div class="placeholder">Kayıtlı harita yok.</div>';

    charts.forEach(c => {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.innerHTML = `
            <div>
                <strong>${c.name}</strong><br>
                <button id="calculate-btn" class="primary-btn">Haritayı Hesapla</button>
                <div style="display: flex; gap: 1rem; margin-top: 1rem;">
                    <button id="save-chart-btn" class="secondary-btn">Haritayı Kaydet</button>
                    <button id="download-pdf-btn" class="secondary-btn">PDF Raporu</button>
                </div>

                <div class="history-section glass" style="margin-top: 2rem; padding: 1.5rem;">
                    <h3>Kayıtlı Haritalar</h3>
                    <div id="history-list" class="list-container">
                        <div class="placeholder">Geçmiş yükleniyor...</div>
                    </div>
                </div>
        `;
        list.appendChild(item);
    });
}

window.loadChart = (dt, lat, lon) => {
    document.getElementById('datetime').value = dt.slice(0, 16);
    document.getElementById('lat').value = lat;
    document.getElementById('lon').value = lon;
    document.getElementById('calculate-btn').click();
};

loadHistory();
