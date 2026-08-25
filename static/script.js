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
    
    // 🔥 防止重复点击
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

// ============ 3. 还书板块重构 ============
let allActiveBorrowings = []; // 缓存当前所有未还记录
let currentFilteredReaders = []; // 缓存去重后的读者列表

// 加载还书表单与读者数据
async function loadReturnForm() {
    const data = await apiCall('/api/borrowings/active');
    allActiveBorrowings = Array.isArray(data) ? data : [];
    
    // 读者去重处理
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
    
    // 重置图书展示区
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

// 渲染读者下拉选项
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

// 模糊搜索读者（支持姓名或电话）
function filterReturnReaders() {
    const keyword = document.getElementById('returnReaderSearchInput').value.trim().toLowerCase();
    
    // 重新从完整借阅记录中提取读者
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
    
    // 如果过滤后刚好只剩一位读者，自动选中并触发展示
    if (filtered.length === 1) {
        document.getElementById('returnReader').value = filtered[0].id;
        onReturnReaderSelected();
    }
}

// 当选中读者时，渲染该读者的借阅列表卡片
function onReturnReaderSelected() {
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

// 执行还书操作
async function executeReturnBook(readerId, bookId, bookName) {
    if (!confirm(`确认办理归还《${bookName}》吗？`)) return;

    const result = await apiCall('/api/return', 'POST', { 
        reader_id: parseInt(readerId), 
        book_id: String(bookId) 
    });

    showMessage('returnResult', result.message, result.success ? 'success' : 'danger');

    if (result.success) {
        // 重新拉取借阅数据，并保持当前选中读者以便即时刷新图书卡片
        const data = await apiCall('/api/borrowings/active');
        allActiveBorrowings = Array.isArray(data) ? data : [];
        onReturnReaderSelected();
    }
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
             style="cursor: pointer;" onclick="selectFine(${f.罚款编号})">
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
async function scanAndFreeze() {
    const result = await apiCall('/api/admin/scan_and_freeze', 'POST');
    showMessage('adminResult', result.message, result.success ? 'success' : 'danger');
    loadViolators();
}

async function loadViolators() {
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
async function loadReaderList() {
    const data = await apiCall('/api/readers/all');
    const container = document.getElementById('readerList');
    if (!container) return;
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
    const existingMsg = container.querySelector('.search-result-msg');
    if (existingMsg) existingMsg.remove();
    if (foundCount === 0 && keyword) {
        const msg = document.createElement('div');
        msg.className = 'alert alert-warning search-result-msg';
        msg.textContent = `🔍 未找到包含 "${keyword}" 的读者`;
        container.prepend(msg);
    }
}

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

async function updateReaderPhone(readerId, newPhone) {
    const result = await apiCall(`/api/readers/${readerId}/phone`, 'PUT', { phone: newPhone });
    if (result.success) {
        alert('✅ ' + result.message);
        loadReaderList();
    } else {
        alert('❌ ' + result.message);
    }
}

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