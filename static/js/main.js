// static/js/main.js
import { loadCategories, searchBooks } from './search.js';
import { loadBorrowForm, borrowBook } from './borrow.js';
import { loadReturnForm, filterReturnReaders, onReturnReaderSelected, executeReturnBook } from './return.js';
import { loadFines, selectFine, payFine, filterFines } from './fine.js';
import { scanAndFreeze, loadViolators } from './admin.js';
import { loadRecommendForm, getRecommend } from './recommend.js';
import { loadReaderList, searchReaders, showEditPhone, deleteReader, addReader } from './readers.js';

// ============ Tab 切换总控 ============
export function switchTab(tab) {
    console.log("切换 Tab 到:", tab);
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

export function logout() {
    if (confirm('确认退出登录吗？')) {
        window.location.href = '/logout';
    }
}

// ============ 挂载到全局 window ============
Object.assign(window, {
    switchTab,
    logout,
    searchBooks,
    borrowBook,
    filterReturnReaders,
    onReturnReaderSelected,
    executeReturnBook,
    selectFine,
    payFine,
    filterFines,
    scanAndFreeze,
    getRecommend,
    searchReaders,
    showEditPhone,
    deleteReader,
    addReader
});

// ============ 初始化 ============
document.addEventListener('DOMContentLoaded', () => {
    console.log("✅ 页面 JS 模块已成功加载与挂载");
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