// static/js/return.js
import { apiCall, showMessage } from './api.js';

let allActiveBorrowings = [];
let currentFilteredReaders = [];

export async function loadReturnForm() {
    const data = await apiCall('/api/borrowings/active');
    allActiveBorrowings = Array.isArray(data) ? data : [];
    
    const readersMap = new Map();
    allActiveBorrowings.forEach(r => {
        if (!readersMap.has(String(r.读者编号))) {
            readersMap.set(String(r.读者编号), {
                id: r.读者编号,
                name: r.姓名,
                phone: r.联系电话 || ''
            });
        }
    });
    
    currentFilteredReaders = Array.from(readersMap.values());
    renderReturnReaderOptions(currentFilteredReaders);
    
    const container = document.getElementById('returnBooksContainer');
    const badge = document.getElementById('borrowCountBadge');
    if (badge) {
        badge.className = 'badge bg-secondary';
        badge.textContent = '未选择读者';
    }
    if (container) {
        container.innerHTML = '<div class="alert alert-light border text-center text-muted">请选择上方读者查看名下借阅图书</div>';
    }
}

function renderReturnReaderOptions(readers) {
    const readerSel = document.getElementById('returnReader');
    if (!readerSel) return;
    
    if (readers.length === 0) {
        readerSel.innerHTML = '<option value="">暂无待还书读者</option>';
        return;
    }
    
    readerSel.innerHTML = '<option value="">-- 请选择读者 --</option>' + 
        readers.map(r => `<option value="${r.id}">${r.name} (${r.phone || '无电话'})</option>`).join('');
}

export function filterReturnReaders() {
    const keyword = document.getElementById('returnReaderSearchInput').value.trim().toLowerCase();
    
    const readersMap = new Map();
    allActiveBorrowings.forEach(r => {
        if (!readersMap.has(String(r.读者编号))) {
            readersMap.set(String(r.读者编号), {
                id: r.读者编号,
                name: r.姓名,
                phone: r.联系电话 || ''
            });
        }
    });
    
    const allReaders = Array.from(readersMap.values());
    const filtered = allReaders.filter(r => 
        r.name.toLowerCase().includes(keyword) || r.phone.includes(keyword)
    );
    
    renderReturnReaderOptions(filtered);
    
    if (filtered.length === 1) {
        document.getElementById('returnReader').value = filtered[0].id;
        onReturnReaderSelected();
    }
}

export function onReturnReaderSelected() {
    const readerId = document.getElementById('returnReader').value;
    const container = document.getElementById('returnBooksContainer');
    const badge = document.getElementById('borrowCountBadge');
    if (!container) return;

    if (!readerId) {
        container.innerHTML = '<div class="alert alert-light border text-center text-muted">请选择上方读者查看名下借阅图书</div>';
        if (badge) {
            badge.className = 'badge bg-secondary';
            badge.textContent = '未选择读者';
        }
        return;
    }

    const userBooks = allActiveBorrowings.filter(r => String(r.读者编号) === String(readerId));
    
    if (badge) {
        badge.className = 'badge bg-primary';
        badge.textContent = `待还 ${userBooks.length} 本`;
    }

    if (userBooks.length === 0) {
        container.innerHTML = '<div class="alert alert-success">🎉 该读者名下所有借阅均已还清！</div>';
        return;
    }

    container.innerHTML = userBooks.map(item => `
        <div class="card mb-2 p-3 ${item.是否逾期 ? 'border-danger' : ''}">
            <div class="row align-items-center">
                <div class="col-md-4">
                    <strong class="h6 mb-0">${item.书名}</strong>
                    <span class="badge bg-secondary ms-1">${item.作者 || '佚名'}</span>
                </div>
                <div class="col-md-3 text-muted">
                    <small>借出: ${item.借出日期}</small><br>
                    <small>应还: ${item.应还日期}</small>
                </div>
                <div class="col-md-2">
                    ${item.是否逾期 
                        ? '<span class="badge bg-danger">⚠️ 已逾期</span>' 
                        : '<span class="badge bg-success">正常借阅</span>'}
                </div>
                <div class="col-md-3 text-end">
                    <button class="btn btn-sm btn-outline-warning" 
                            onclick="executeReturnBook(${item.读者编号}, '${item.图书编号}', '${item.书名}')">
                        🔄 归还此书
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

export async function executeReturnBook(readerId, bookId, bookName) {
    if (!confirm(`确认办理归还《${bookName}》吗？`)) return;

    const result = await apiCall('/api/return', 'POST', { 
        reader_id: parseInt(readerId), 
        book_id: String(bookId) 
    });

    showMessage('returnResult', result.message, result.success ? 'success' : 'danger');

    if (result.success) {
        const data = await apiCall('/api/borrowings/active');
        allActiveBorrowings = Array.isArray(data) ? data : [];
        onReturnReaderSelected();
    }
}