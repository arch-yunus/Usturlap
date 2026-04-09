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
