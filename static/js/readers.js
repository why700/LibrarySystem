// static/js/readers.js
import { apiCall, showMessage } from './api.js';

export async function loadReaderList() {
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

export function searchReaders() {
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

export function showEditPhone(readerId, name, currentPhone) {
    const newPhone = prompt(`修改 ${name} 的手机号\n当前号码：${currentPhone}\n请输入新的11位手机号：`);
    if (newPhone === null) return;
    const phone = newPhone.trim();
    if (!/^1\d{10}$/.test(phone)) {
        alert('❌ 请输入有效的11位手机号！');
        return;
    }
    updateReaderPhone(readerId, phone);
}

export async function updateReaderPhone(readerId, newPhone) {
    const result = await apiCall(`/api/readers/${readerId}/phone`, 'PUT', { phone: newPhone });
    if (result.success) {
        alert('✅ ' + result.message);
        loadReaderList();
    } else {
        alert('❌ ' + result.message);
    }
}

export async function deleteReader(readerId, name) {
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

export async function addReader() {
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
