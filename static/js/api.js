// static/js/api.js

export function showMessage(elementId, msg, type = 'success') {
    const el = document.getElementById(elementId);
    if (!el) return;
    const className = type === 'success' ? 'alert-success' : 'alert-danger';
    el.innerHTML = `<div class="alert ${className}">${msg}</div>`;
}

export async function apiCall(url, method = 'GET', data = null) {
    try {
        const options = { method, headers: { 'Content-Type': 'application/json' } };
        if (data) options.body = JSON.stringify(data);
        const res = await fetch(url, options);
        const json = await res.json();
        
        // 兼容 FastAPI 的 detail 错误返回格式
        if (!res.ok) {
            return { 
                success: false, 
                message: json.detail || json.message || "请求失败，请检查服务器日志" 
            };
        }
        return json;
    } catch (err) {
        console.error("API Call Error:", err);
        return { success: false, message: "网络请求异常或服务器无响应" };
    }
}