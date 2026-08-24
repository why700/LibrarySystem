// static/script.js

// ============ 工具函数 ============
function showMessage(elementId, msg, type = 'success') {
    const el = document.getElementById(elementId);
    if (!el) return;
    const className = type === 'success' ? 'alert-success' : 'alert-danger';
    el.innerHTML = `<div class="alert ${className}">${msg}</div>`;
}

async function apiCall(url, method = 'GET', data = null) {
    try {
        const options = { method, headers: { 'Content-Type': 'application/json' } };
        if (data) options.body = JSON.stringify(data);
        const res = await fetch(url, options);
        return await res.json();
    } catch (err) {
        console.error("API Call Error:", err);
        return { success: false, message: "网络请求异常或服务器无响应" };
    }
}

// ============ Tab 切换 ============
function switchTab(tab) {
    document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
    const targetTab = document.getElementById(`tab-${tab}`);
    if (targetTab) targetTab.style.display = 'block';
    
    const titles = {
        'search': '🔍 馆藏图书查询',
        'borrow': '📝 办理借书',
        'return': '🔄 办理还书',
        'fine': '💰 缴纳罚金',
        'admin': '⚙️ 系统维护',
        'recommend': '🤖 智能推荐',
        'reader_manage': '👥 读者信息管理'
    };
    const titleEl = document.getElementById('pageTitle');
    if (titleEl) titleEl.textContent = titles[tab] || '图书馆系统';
    
    if (tab === 'borrow') loadBorrowForm();
    if (tab === 'return') loadReturnForm();
    if (tab === 'fine') loadFines();
    if (tab === 'admin') loadViolators();
    if (tab === 'recommend') loadRecommendForm();
    if (tab === 'reader_manage') {
        const searchInput = document.getElementById('readerSearchInput');
        if (searchInput) searchInput.value = '';
        loadReaderList();
    }
}

// ============ 加载分类下拉框 ============
async function loadCategories() {
    const data = await apiCall('/api/categories');
    const sel = document.getElementById('categoryFilter');
    if (!sel || !Array.isArray(data)) return;
    
    sel.innerHTML = '<option value="0">📚 全部分类</option>' + 
        data.map(c => `<option value="${c.类别编号}">${c.类别名称}</option>`).join('');
}

// ============ 1. 搜索图书 ============
async function searchBooks() {
    const keyword = document.getElementById('searchInput').value.trim();
    const category = document.getElementById('categoryFilter').value || '0';
    
    let url = `/api/books/search?keyword=${encodeURIComponent(keyword)}`;
    if (category && category !== '0') {
        url += `&category=${category}`;
    }
    
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

// ============ 2. 借书 ============
async function loadBorrowForm() {
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

async function borrowBook() {
    const reader_id = document.getElementById('borrowReader').value;
    const book_id = document.getElementById('borrowBook').value;
    
    if (!reader_id || !book_id) {
        showMessage('borrowResult', '请选择读者与要借阅的图书', 'danger');
        return;
    }
    
    const result = await apiCall('/api/borrow', 'POST', { reader_id: parseInt(reader_id), book_id });
    showMessage('borrowResult', result.message, result.success ? 'success' : 'danger');
    if (result.success) loadBorrowForm();
}

// ============ 3. 还书 ============
async function loadReturnForm() {
    const data = await apiCall('/api/borrowings/active');
    const readerSel = document.getElementById('returnReader');
    if (!readerSel) return;

    if (!Array.isArray(data) || data.length === 0) {
        readerSel.innerHTML = '<option value="">暂无需还书读者</option>';
        document.getElementById('returnBook').innerHTML = '<option value="">无待还记录</option>';
        return;
    }
    
    const readersMap = new Map();
    data.forEach(r => readersMap.set(String(r.读者编号), r.姓名));
    
    readerSel.innerHTML = Array.from(readersMap.entries()).map(([id, name]) => 
        `<option value="${id}">${name}</option>`
    ).join('');
    
    updateReturnBooks();
}

async function updateReturnBooks() {
    const readerId = document.getElementById('returnReader').value;
    const bookSel = document.getElementById('returnBook');
    if (!readerId || !bookSel) return;
    
    const data = await apiCall('/api/borrowings/active');
    const books = Array.isArray(data) ? data.filter(r => String(r.读者编号) === String(readerId)) : [];
    
    if (books.length === 0) {
        bookSel.innerHTML = '<option value="">该读者暂无未还图书</option>';
        return;
    }
    bookSel.innerHTML = books.map(b => 
        `<option value="${b.图书编号}">${b.书名}</option>`
    ).join('');
}

async function returnBook() {
    const reader_id = document.getElementById('returnReader').value;
    const book_id = document.getElementById('returnBook').value;
    
    if (!reader_id || !book_id) {
        showMessage('returnResult', '请选择有效读者和待归还的图书', 'danger');
        return;
    }
    
    const result = await apiCall('/api/return', 'POST', { reader_id: parseInt(reader_id), book_id });
    showMessage('returnResult', result.message, result.success ? 'success' : 'danger');
    if (result.success) loadReturnForm();
}

// ============ 4. 罚金 ============
let selectedFineId = null;

async function loadFines() {
    const data = await apiCall('/api/fines/unpaid');
    const container = document.getElementById('fineList');
    if (!container) return;
    
    if (!Array.isArray(data) || data.length === 0) {
        container.innerHTML = '<div class="alert alert-success">🎉 暂无未缴罚单</div>';
        selectedFineId = null;
        return;
    }
    
    container.innerHTML = data.map(f => `
        <div class="card mb-2 p-3 fine-item ${selectedFineId === f.罚款编号 ? 'border-danger bg-light' : ''}" 
             style="cursor: pointer;"
             onclick="selectFine(${f.罚款编号})">
            <div class="row align-items-center">
                <div class="col-md-3"><strong>${f.姓名}</strong></div>
                <div class="col-md-3 text-danger font-weight-bold">金额：￥${f.罚款金额}</div>
                <div class="col-md-4">原因：${f.罚款原因}</div>
                <div class="col-md-2 text-end"><span class="badge bg-danger">未缴</span></div>
            </div>
        </div>
    `).join('');
}

function selectFine(id) {
    selectedFineId = id;
    loadFines();
}

async function payFine() {
    if (!selectedFineId) {
        showMessage('fineResult', '请先点击选择一笔待缴纳的罚单', 'danger');
        return;
    }
    const result = await apiCall('/api/pay_fine', 'POST', { fine_id: selectedFineId });
    showMessage('fineResult', result.message, result.success ? 'success' : 'danger');
    if (result.success) {
        selectedFineId = null;
        loadFines();
    }
}

// ============ 5. 系统维护 ============
async function scanOverdue() {
    const result = await apiCall('/api/scan_overdue', 'POST');
    showMessage('adminResult', result.message, result.success ? 'success' : 'danger');
    loadViolators();
}

async function freezeViolators() {
    const result = await apiCall('/api/freeze_violators', 'POST');
    showMessage('adminResult', result.message, result.success ? 'success' : 'danger');
    loadViolators();
}

async function loadViolators() {
    const data = await apiCall('/api/violators');
    const container = document.getElementById('violatorList');
    if (!container) return;

    if (!Array.isArray(data) || data.length === 0) {
        container.innerHTML = '<div class="alert alert-success">暂无违规账号</div>';
        return;
    }
    container.innerHTML = data.map(v => `
        <div class="card mb-2 p-2">
            <div class="d-flex justify-content-between align-items-center">
                <span><strong>${v.姓名}</strong> (联系电话: ${v.联系电话 || '无'})</span>
                <span class="badge bg-danger">${v.账号状态}</span>
            </div>
        </div>
    `).join('');
}

// ============ 6. AI 推荐 ============
async function loadRecommendForm() {
    const data = await apiCall('/api/readers/all');
    const sel = document.getElementById('recommendReader');
    if (!sel) return;

    if (!Array.isArray(data) || data.length === 0) {
        sel.innerHTML = '<option value="">无有效读者</option>';
        return;
    }
    sel.innerHTML = data.map(r => `<option value="${r.读者编号}">${r.姓名}</option>`).join('');
}

async function getRecommend() {
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

// ============ 7. 退出登录 ============
async function logout() {
    if (confirm('确认退出登录吗？')) {
        window.location.href = '/logout';
    }
}

// ============ 8. 读者信息管理 ============

// 加载读者列表
async function loadReaderList() {
    const data = await apiCall('/api/readers/all');
    const container = document.getElementById('readerList');
    if (!container) return;

    // 清除搜索提示
    const existingMsg = container.querySelector('.search-result-msg');
    if (existingMsg) existingMsg.remove();

    if (!Array.isArray(data) || data.length === 0) {
        container.innerHTML = '<div class="alert alert-info">📭 暂无读者信息</div>';
        return;
    }

    container.innerHTML = data.map(r => `
        <div class="card mb-2 p-3" id="reader-${r.读者编号}">
            <div class="row align-items-center">
                <div class="col-md-2">
                    <strong>${r.姓名}</strong>
                    <span class="badge ${r.账号状态 === '正常' ? 'bg-success' : 'bg-danger'} ms-2">${r.账号状态}</span>
                </div>
                <div class="col-md-3">
                    <span class="text-muted">📞 ${r.联系电话}</span>
                </div>
                <div class="col-md-2">
                    <small>已借：${r.已借数量}/${r.最大借阅量}</small>
                </div>
                <div class="col-md-2">
                    <small class="text-muted">编号：${r.读者编号}</small>
                </div>
                <div class="col-md-3 text-end">
                    <button class="btn btn-sm btn-outline-primary me-2" onclick="showEditPhone(${r.读者编号}, '${r.姓名}', '${r.联系电话}')">✏️ 改号</button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteReader(${r.读者编号}, '${r.姓名}')">🗑️ 注销</button>
                </div>
            </div>
        </div>
    `).join('');
}

// 搜索读者（前端过滤）
function searchReaders() {
    const keyword = document.getElementById('readerSearchInput').value.trim().toLowerCase();
    const cards = document.querySelectorAll('#readerList .card');
    const container = document.getElementById('readerList');
    
    let foundCount = 0;
    cards.forEach(card => {
        const text = card.textContent.toLowerCase();
        if (text.includes(keyword)) {
            card.style.display = '';
            foundCount++;
        } else {
            card.style.display = 'none';
        }
    });
    
    // 显示搜索结果提示
    const existingMsg = container.querySelector('.search-result-msg');
    if (existingMsg) existingMsg.remove();
    
    if (foundCount === 0 && keyword) {
        const msg = document.createElement('div');
        msg.className = 'alert alert-warning search-result-msg';
        msg.textContent = `🔍 未找到包含 "${keyword}" 的读者`;
        container.prepend(msg);
    }
}

// 显示修改手机号弹窗
function showEditPhone(readerId, name, currentPhone) {
    const newPhone = prompt(`修改 ${name} 的手机号\n当前号码：${currentPhone}\n请输入新的11位手机号：`);
    if (newPhone === null) return;

    const phone = newPhone.trim();
    if (!/^1\d{10}$/.test(phone)) {
        alert('❌ 请输入有效的11位手机号！');
        return;
    }

    updateReaderPhone(readerId, phone);
}

// 修改读者手机号
async function updateReaderPhone(readerId, newPhone) {
    const result = await apiCall(`/api/readers/${readerId}/phone`, 'PUT', { phone: newPhone });

    if (result.success) {
        alert('✅ ' + result.message);
        loadReaderList();
    } else {
        alert('❌ ' + result.message);
    }
}

// 注销读者
async function deleteReader(readerId, name) {
    if (!confirm(`确定要注销读者 "${name}" 吗？\n如果该读者有未归还的图书，将无法注销。`)) {
        return;
    }

    const result = await apiCall(`/api/readers/${readerId}`, 'DELETE');

    if (result.success) {
        alert('✅ ' + result.message);
        loadReaderList();
    } else {
        alert('❌ ' + result.message);
    }
}

// 添加读者
async function addReader() {
    const name = document.getElementById('readerName').value.trim();
    const phone = document.getElementById('readerPhone').value.trim();

    if (!name) {
        showMessage('addReaderResult', '请输入读者姓名！', 'danger');
        return;
    }
    if (!phone) {
        showMessage('addReaderResult', '请输入联系电话！', 'danger');
        return;
    }
    if (!/^1\d{10}$/.test(phone)) {
        showMessage('addReaderResult', '请输入有效的11位手机号！', 'danger');
        return;
    }

    const result = await apiCall('/api/readers', 'POST', { name, phone });

    if (result.success) {
        document.getElementById('readerName').value = '';
        document.getElementById('readerPhone').value = '';
        showMessage('addReaderResult', result.message, 'success');
        loadReaderList();
    } else {
        showMessage('addReaderResult', result.message, 'danger');
    }
}

// ============ 初始化 ============
document.addEventListener('DOMContentLoaded', () => {
    switchTab('search');
    loadCategories();
    
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keyup', (e) => {
            if (e.key === 'Enter') searchBooks();
        });
    }
    
    const readerSearchInput = document.getElementById('readerSearchInput');
    if (readerSearchInput) {
        readerSearchInput.addEventListener('keyup', (e) => {
            if (e.key === 'Enter') searchReaders();
        });
    }
});