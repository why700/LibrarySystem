// static/js/fine.js
import { apiCall, showMessage } from './api.js';

let allFinesData = [];    // 缓存从后端拉取到的所有未缴罚单
let selectedFineId = null; // 当前选中的罚款编号

// 1. 加载并拉取未缴罚单
export async function loadFines() {
    const data = await apiCall('/api/fines/unpaid');
    allFinesData = Array.isArray(data) ? data : [];
    
    // 清空搜索框输入
    const searchInput = document.getElementById('fineSearchInput');
    if (searchInput) searchInput.value = '';

    // 默认渲染全部未缴罚单
    renderFineList(allFinesData);
}

// 2. 核心渲染函数
function renderFineList(finesToRender) {
    const container = document.getElementById('fineList');
    const badge = document.getElementById('fineCountBadge');
    if (!container) return;

    if (badge) {
        badge.textContent = `共 ${allFinesData.length} 笔未缴罚单${finesToRender.length !== allFinesData.length ? `（已筛选显示 ${finesToRender.length} 笔）` : ''}`;
    }

    if (finesToRender.length === 0) {
        container.innerHTML = '<div class="alert alert-success">🎉 暂无相关未缴罚单</div>';
        selectedFineId = null;
        return;
    }

    container.innerHTML = finesToRender.map(f => `
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

// 3. 实时搜索过滤（已补齐导出）
export function filterFines() {
    const keyword = document.getElementById('fineSearchInput')?.value.trim().toLowerCase() || '';
    
    if (!keyword) {
        renderFineList(allFinesData);
        return;
    }

    const filtered = allFinesData.filter(f => 
        f.姓名 && f.姓名.toLowerCase().includes(keyword)
    );

    renderFineList(filtered);
}

// 4. 选中罚单（高亮样式）
export function selectFine(id) {
    selectedFineId = id;
    const keyword = document.getElementById('fineSearchInput')?.value.trim().toLowerCase();
    if (keyword) {
        const filtered = allFinesData.filter(f => f.姓名 && f.姓名.toLowerCase().includes(keyword));
        renderFineList(filtered);
    } else {
        renderFineList(allFinesData);
    }
}

// 5. 缴纳罚金
export async function payFine() {
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