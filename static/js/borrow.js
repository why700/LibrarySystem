// static/js/borrow.js
import { apiCall, showMessage } from './api.js';

export async function loadBorrowForm() {
    const [readers, books] = await Promise.all([
        apiCall('/api/readers/all'),
        apiCall('/api/books/all')
    ]);
    const readerSel = document.getElementById('borrowReader');
    const bookSel = document.getElementById('borrowBook');
    if (readerSel && Array.isArray(readers)) {
        readerSel.innerHTML = readers.length ? readers.map(r => 
            `<option value="${r.读者编号}">${r.姓名} (已借 ${r.已借数量}/${r.最大借阅量})</option>`
        ).join('') : '<option value="">暂无可用读者</option>';
    }
    if (bookSel && Array.isArray(books)) {
        bookSel.innerHTML = books.length ? books.map(b => 
            `<option value="${b.图书编号}">${b.书名} (余 ${b.现有库存})</option>`
        ).join('') : '<option value="">暂无在馆图书</option>';
    }
}

export async function borrowBook() {
    const reader_id = document.getElementById('borrowReader').value;
    const book_id = document.getElementById('borrowBook').value;
    
    if (!reader_id || !book_id) {
        showMessage('borrowResult', '请选择读者与要借阅的图书', 'danger');
        return;
    }
    
    const btn = document.querySelector('#tab-borrow .btn-success');
    if (btn) {
        btn.disabled = true;
        btn.textContent = '提交中...';
    }

    const result = await apiCall('/api/borrow', 'POST', { 
        reader_id: parseInt(reader_id), 
        book_id: book_id 
    });
    
    if (btn) {
        btn.disabled = false;
        btn.textContent = '提交借阅';
    }

    showMessage('borrowResult', result.message, result.success ? 'success' : 'danger');
    if (result.success) loadBorrowForm();
}