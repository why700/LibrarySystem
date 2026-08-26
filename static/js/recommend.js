// static/js/recommend.js
import { apiCall } from './api.js';

export async function loadRecommendForm() {
    const data = await apiCall('/api/readers/all');
    const sel = document.getElementById('recommendReader');
    if (!sel) return;
    if (!Array.isArray(data) || data.length === 0) {
        sel.innerHTML = '<option value="">无有效读者</option>';
        return;
    }
    sel.innerHTML = data.map(r => `<option value="${r.读者编号}">${r.姓名}</option>`).join('');
}

export async function getRecommend() {
    const readerId = document.getElementById('recommendReader').value;
    if (!readerId) return;
    const container = document.getElementById('recommendResult');
    container.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">计算中...</span></div>';
    const data = await apiCall(`/api/recommend/${readerId}`);
    if (!Array.isArray(data) || data.length === 0) {
        container.innerHTML = '<div class="alert alert-info">暂无推荐图书</div>';
        return;
    }
    container.innerHTML = `
        <div class="row">
            ${data.map(book => `
                <div class="col-md-4 mb-3">
                    <div class="card h-100 p-3 shadow-sm">
                        <strong class="h6 mb-1">${book.书名}</strong>
                        <small class="text-muted mb-2">作者: ${book.作者}</small>
                        <div>
                            <span class="badge bg-info text-dark">匹配度 ${(book.相似度 * 100).toFixed(1)}%</span>
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}