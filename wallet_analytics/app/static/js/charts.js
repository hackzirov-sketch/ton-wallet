document.addEventListener('DOMContentLoaded', function() {
    initCharts();
    initActivityRange();
});

function initActivityRange() {
    const btns = document.querySelectorAll('#activityRange button');
    btns.forEach(btn => {
        btn.addEventListener('click', function() {
            btns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            loadActivityChart(parseInt(this.dataset.days));
        });
    });
    loadActivityChart(30);
}

async function loadActivityChart(days) {
    try {
        const resp = await fetch(`/api/analytics/activity?days=${days}`);
        const data = await resp.json();
        renderActivityChart(data.activity || []);
    } catch (e) {
        console.error('Failed to load activity:', e);
    }
}

async function initCharts() {
    try {
        const [monthlyResp, dashboardResp] = await Promise.all([
            fetch('/api/analytics/monthly'),
            fetch('/api/dashboard')
        ]);
        const monthlyData = await monthlyResp.json();
        const dashData = await dashboardResp.json();

        renderMonthlyChart(monthlyData.monthly_flow || []);
        renderIncomingOutgoingChart(dashData.stats || {});
    } catch (e) {
        console.error('Failed to load chart data:', e);
    }
}

function renderActivityChart(activity) {
    const ctx = document.getElementById('activityChart');
    if (!ctx) return;

    if (window._activityChart) window._activityChart.destroy();

    const labels = activity.map(a => a.date);
    const incoming = activity.map(a => a.incoming);
    const outgoing = activity.map(a => a.outgoing);

    window._activityChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Incoming',
                    data: incoming,
                    backgroundColor: 'rgba(63, 185, 80, 0.7)',
                    borderRadius: 3,
                },
                {
                    label: 'Outgoing',
                    data: outgoing,
                    backgroundColor: 'rgba(248, 81, 73, 0.7)',
                    borderRadius: 3,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#8b949e', font: { size: 11 } } }
            },
            scales: {
                x: {
                    ticks: { color: '#8b949e', maxRotation: 45, font: { size: 10 } },
                    grid: { color: 'rgba(48,54,61,0.5)' }
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: '#8b949e', font: { size: 10 } },
                    grid: { color: 'rgba(48,54,61,0.5)' }
                }
            }
        }
    });
}

function renderIncomingOutgoingChart(stats) {
    const ctx = document.getElementById('incomingOutgoingChart');
    if (!ctx) return;

    const incoming = parseFloat(stats.total_incoming) || 0;
    const outgoing = parseFloat(stats.total_outgoing) || 0;

    if (window._ioChart) window._ioChart.destroy();

    window._ioChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Incoming', 'Outgoing'],
            datasets: [{
                data: [incoming, outgoing],
                backgroundColor: ['rgba(63, 185, 80, 0.8)', 'rgba(248, 81, 73, 0.8)'],
                borderColor: ['#3fb950', '#f85149'],
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#8b949e', font: { size: 11 }, padding: 15 }
                }
            }
        }
    });
}

function renderMonthlyChart(monthly) {
    const ctx = document.getElementById('monthlyChart');
    if (!ctx) return;

    if (window._monthlyChart) window._monthlyChart.destroy();

    const labels = monthly.map(m => m.label);
    const incoming = monthly.map(m => m.incoming);
    const outgoing = monthly.map(m => m.outgoing.map ? -m.outgoing : -(m.outgoing));
    const net = monthly.map(m => m.net);

    window._monthlyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Incoming',
                    data: incoming,
                    backgroundColor: 'rgba(63, 185, 80, 0.7)',
                    borderRadius: 3,
                },
                {
                    label: 'Outgoing',
                    data: outgoing,
                    backgroundColor: 'rgba(248, 81, 73, 0.7)',
                    borderRadius: 3,
                },
                {
                    label: 'Net',
                    data: net,
                    type: 'line',
                    borderColor: '#58a6ff',
                    backgroundColor: 'rgba(88, 166, 255, 0.1)',
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBackgroundColor: '#58a6ff',
                    fill: true,
                    tension: 0.3,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#8b949e', font: { size: 11 } } }
            },
            scales: {
                x: {
                    ticks: { color: '#8b949e', font: { size: 10 } },
                    grid: { color: 'rgba(48,54,61,0.5)' }
                },
                y: {
                    ticks: { color: '#8b949e', font: { size: 10 } },
                    grid: { color: 'rgba(48,54,61,0.5)' }
                }
            }
        }
    });
}
