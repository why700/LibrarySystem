// static/js/admin.js
import { apiCall, showMessage } from './api.js';

export async function scanAndFreeze() {
    const result = await apiCall('/api/admin/scan_and_freeze', 'POST');
    showMessage('adminResult', result.message, result.success ? 'success' : 'danger');
    loadViolators();
}

export async function loadViolators() {
    const data = await apiCall('/api/violators');
    const container = document.getElementById('violatorList');
    if (!container) return;
    if (!Array.isArray(data) || data.length === 0) {
        container.innerHTML = '<div class="alert alert-success">🎉 暂无违规账号</div>';
        return;
    }
    container.innerHTML = data.map(v => `
        <div class="card mb-2 p-2">
            <div class="d-flex justify-content-between align-items-center">
                <span><strong>${v.姓名}</strong> (${v.联系电话 || '无'})</span>
                <span class="badge bg-danger">${v.账号状态}</span>
            </div>
        </div>
    `).join('');
}