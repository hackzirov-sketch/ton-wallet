async function syncWallet() {
    const btn = document.getElementById('refreshBtn');
    const status = document.getElementById('syncStatus');
    if (btn) btn.disabled = true;
    if (status) {
        status.style.display = 'block';
        status.innerHTML = '<small class="text-info"><span class="spinner-border spinner-border-sm me-1"></span>Syncing...</small>';
    }

    try {
        const resp = await fetch('/api/sync', { method: 'POST' });
        const data = await resp.json();
        if (data.status === 'success') {
            if (status) status.innerHTML = '<small class="text-success"><i class="bi bi-check-circle me-1"></i>Updated just now</small>';
            setTimeout(() => location.reload(), 800);
        } else {
            if (status) status.innerHTML = '<small class="text-danger"><i class="bi bi-x-circle me-1"></i>Could not update wallet. Existing data is still available.</small>';
        }
    } catch (e) {
        if (status) status.innerHTML = '<small class="text-danger"><i class="bi bi-x-circle me-1"></i>Could not update wallet. Existing data is still available.</small>';
    }

    if (btn) btn.disabled = false;
}
