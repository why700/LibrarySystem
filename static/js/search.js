// static/js/search.js
import { apiCall } from './api.js';

export async function loadCategories() {
    const data = await apiCall('/api/categories');
    const sel = document.getElementById('categoryFilter');
    if (!sel || !Array.isArray(data)) return;
    sel.innerHTML = '<option value="0">📚 全部分类</option>' + 
        data.map(c => `<option value="${c.类别编号}">${c.类别名称}</option>`).join('');
}

export async function searchBooks() {
    const keyword = document.getElementById('searchInput').value.trim();
    const category = document.getElementById('categoryFilter').value || '0';
    let url = `/api/books/search?keyword=${encodeURIComponent(keyword)}`;
    if (category && category !== '0') url += `&category=${category}`;
    
    const data = await apiCall(url);
    const container = document.getElementById('searchResults');
    if (!container) return;
    
    if (!Array.isArray(data) || data.length === 0) {
        container.innerHTML = '<div class="alert alert-warning">未找到相关图书</div>';
        return;
    }
    
    container.innerHTML = data.map(book => `
        <div class="card mb-3 p-3">
            <div class="row">
                <div class="col-md-6">
                    <strong class="h6">${book.书名}</strong>
                    <span class="badge bg-secondary ms-2">${book.作者}</span>
                </div>
                <div class="col-md-3">
                    库存：<span class="badge ${book.现有库存 > 0 ? 'bg-success' : 'bg-danger'}">${book.现有库存} / ${book.总库存}</span>
                </div>
                <div class="col-md-3 text-end">
                    <small class="text-muted">${book.出版社 || '未知出版社'}</small>
                </div>
            </div>
            <div class="row mt-2">
                <div class="col-12">
                    <small class="text-muted">📖 ${book.简介 || '暂无简介'}</small>
                </div>
            </div>
        </div>
    `).join('');
}