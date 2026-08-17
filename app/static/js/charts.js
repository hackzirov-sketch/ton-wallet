const chartColors = {
    incoming: '#10b981',
    incomingBg: 'rgba(16, 185, 129, 0.15)',
    outgoing: '#ef4444',
    outgoingBg: 'rgba(239, 68, 68, 0.15)',
    net: '#6366f1',
    netBg: 'rgba(99, 102, 241, 0.1)',
    grid: 'rgba(30, 41, 59, 0.6)',
    text: '#64748b',
    textLight: '#94a3b8',
};

const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            labels: {
                color: chartColors.textLight,
                font: { size: 11, family: 'Inter' },
                padding: 16,
                usePointStyle: true,
                pointStyleWidth: 8,
            }
        },
        tooltip: {
            backgroundColor: '#1a1f2e',
            titleColor: '#f1f5f9',
            bodyColor: '#94a3b8',
            borderColor: '#334155',
            borderWidth: 1,
            cornerRadius: 8,
            padding: 10,
            titleFont: { size: 12, weight: 600 },
            bodyFont: { size: 11 },
        }
    },
    scales: {
        x: {
            ticks: { color: chartColors.text, font: { size: 10 } },
            grid: { color: chartColors.grid, drawBorder: false },
            border: { display: false },
        },
        y: {
            beginAtZero: true,
            ticks: { color: chartColors.text, font: { size: 10 } },
            grid: { color: chartColors.grid, drawBorder: false },
            border: { display: false },
        }
    }
};

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

    const labels = activity.map(a => {
        const d = new Date(a.date);
        return d.toLocaleDateString('en', { month: 'short', day: 'numeric' });
    });
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
                    backgroundColor: chartColors.incoming,
                    borderRadius: 4,
                    borderSkipped: false,
                },
                {
                    label: 'Outgoing',
                    data: outgoing,
                    backgroundColor: chartColors.outgoing,
                    borderRadius: 4,
                    borderSkipped: false,
                }
            ]
        },
        options: {
            ...chartDefaults,
            plugins: {
                ...chartDefaults.plugins,
                legend: {
                    ...chartDefaults.plugins.legend,
                    position: 'top',
                    align: 'end',
                }
            },
            scales: {
                ...chartDefaults.scales,
                x: {
                    ...chartDefaults.scales.x,
                    ticks: { ...chartDefaults.scales.x.ticks, maxRotation: 0, autoSkip: true, maxTicksLimit: 10 },
                },
                y: {
                    ...chartDefaults.scales.y,
                    ticks: { ...chartDefaults.scales.y.ticks, stepSize: 1 },
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
            labels: ['Received', 'Sent'],
            datasets: [{
                data: [incoming, outgoing],
                backgroundColor: [chartColors.incoming, chartColors.outgoing],
                borderWidth: 0,
                hoverOffset: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '72%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: chartColors.textLight,
                        font: { size: 11, family: 'Inter' },
                        padding: 16,
                        usePointStyle: true,
                    }
                },
                tooltip: chartDefaults.plugins.tooltip,
            }
        }
    });
}

function renderMonthlyChart(monthly) {
    const ctx = document.getElementById('monthlyChart');
    if (!ctx) return;

    if (window._monthlyChart) window._monthlyChart.destroy();

    const labels = monthly.map(m => {
        const [y, mo] = m.label.split('-');
        const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return months[parseInt(mo) - 1] + ' ' + y.slice(2);
    });
    const incoming = monthly.map(m => m.incoming);
    const outgoing = monthly.map(m => -Math.abs(m.outgoing));
    const net = monthly.map(m => m.net);

    window._monthlyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Received',
                    data: incoming,
                    backgroundColor: chartColors.incoming,
                    borderRadius: 4,
                    borderSkipped: false,
                },
                {
                    label: 'Sent',
                    data: outgoing,
                    backgroundColor: chartColors.outgoing,
                    borderRadius: 4,
                    borderSkipped: false,
                },
                {
                    label: 'Net',
                    data: net,
                    type: 'line',
                    borderColor: chartColors.net,
                    backgroundColor: chartColors.netBg,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBackgroundColor: chartColors.net,
                    pointBorderColor: chartColors.net,
                    fill: true,
                    tension: 0.3,
                }
            ]
        },
        options: {
            ...chartDefaults,
            plugins: {
                ...chartDefaults.plugins,
                legend: {
                    ...chartDefaults.plugins.legend,
                    position: 'top',
                    align: 'end',
                }
            },
            scales: {
                ...chartDefaults.scales,
                x: {
                    ...chartDefaults.scales.x,
                    ticks: { ...chartDefaults.scales.x.ticks, maxRotation: 0, autoSkip: true, maxTicksLimit: 12 },
                }
            }
        }
    });
}
