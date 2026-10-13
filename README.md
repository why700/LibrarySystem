# 📚 图书借阅管理系统 (Library Management System)

本项目采用前后端分离模块化设计，后端基于 **FastAPI + SQLAlchemy 2.0 (Async) + MySQL**，前端采用 **原生 ES6 JavaScript 模块化 + Bootstrap 5** 构建，支持图书检索、借阅管理、逾期检测、自动罚款、读者管理及个性化推荐等功能。

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy 2.0 (Async) + Pydantic |
| 数据库 | MySQL 8.0 + asyncmy 异步驱动 |
| 前端 | 原生 JavaScript (ES Module) + Bootstrap 5 |
| 推荐算法 | Scikit-learn (TF-IDF + 余弦相似度) |
| 版本管理 | Git |

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- MySQL 8.0+

### 1. 克隆项目

```
git clone https://github.com/why700/LibrarySystem.git
cd LibrarySystem
```

### 2. 创建虚拟环境并安装依赖
```
pip install fastapi uvicorn sqlalchemy asyncmy pymysql aiomysql pydantic jinja2 itsdangerous mysql-connector-python pandas scikit-learn
```

### 3. 初始化数据库
```
mysql -u root -p -e "CREATE DATABASE librarysystem DEFAULT CHARSET utf8mb4;"
mysql -u root -p librarysystem < database/library_system.sql
```

### 4. 修改数据库密码

打开 database.py，把 DB_PASS 改成你自己的 MySQL 密码：
```
DB_PASS = os.getenv("DB_PASS", "你的密码")
```
### 5. 启动服务
```
uvicorn app:app --reload --port 8001
```
浏览器访问：http://localhost:8001

---

## 🔐 默认账号

| 用户名 | 密码 |
|--------|------|
| admin | 123456 |

---

## 📁 目录与文件功能速查表

| 目录/文件 | 核心职责与功能描述 |
| :--- | :--- |
| **`app.py`** | **主程序入口**：初始化 FastAPI 实例、挂载静态资源与 Session 中间件、管理异步引擎生命周期并集中注册所有路由。 |
| **`config.py`** | **系统配置**：配置管理员默认账号密码及全局常量。 |
| **`database.py`** | **数据库与 ORM**：配置 MySQL 异步连接池（`asyncmy`），定义图书、读者、借阅、罚款及分类的数据模型映射。 |
| **`recommend.py`** | **智能推荐算法**：基于 TF-IDF 文本特征抽取与余弦相似度计算，结合冷启动热门榜单实现个性化图书推荐。 |
| **`.gitignore`** | **Git 忽略清单**：排除 `__pycache__`、虚拟环境及敏感本地文件。 |
| **`README.md`** | **项目说明文档**：记录系统架构、运行方式与模块设计说明。 |
| **`database/library_system.sql`** | **数据库初始化脚本**：包含建表语句与完整测试数据。 |

---

## 🔀 后端路由层 (`routers/`)

* **`__init__.py`**：包初始化标识文件，使 `routers` 成为可导入的 Python 模块。
* **`admin.py`**：**系统维护接口**。提供逾期记录批量扫描与违规账号冻结（`/api/admin/scan_and_freeze`）以及被冻结“老赖”名单查询。
* **`auth.py`**：**权限认证接口**。处理管理员登录校验（`/api/login`）与注销会话（`/logout`）。
* **`books.py`**：**图书查询接口**。提供图书关键字模糊搜索、在馆图书列表展示及全部分类数据获取。
* **`borrow.py`**：**核心借还事务**。处理读者借书校验与库存扣减（`/api/borrow`）、当前未还图书查询以及还书结算与逾期自动开单（`/api/return`）。
* **`fines.py`**：**罚款管理接口**。查询未缴罚单列表（`/api/fines/unpaid`），并在缴纳罚金后自动检测剩余违规情况以执行账号解冻判定（`/api/pay_fine`）。
* **`readers.py`**：**读者信息接口**。提供读者列表展示、新增读者、修改联系电话及注销读者（含未还书校验）。

---

## 🎨 前端逻辑层 (`static/js/`)

* **`api.js`**：**底层网络与弹窗工具**。封装统一的异步 `fetch` 请求函数 `apiCall`（兼容错误解析）与消息展示函数 `showMessage`。
* **`main.js`**：**前端主控制入口**。负责 Tab 页面切换分发、回车事件绑定以及将各子模块函数挂载到 `window` 供 HTML 调用。
* **`search.js`**：**图书检索交互**。负责分类下拉框渲染与图书卡片列表的异步检索呈现。
* **`borrow.js`**：**借书表单交互**。动态加载借阅下拉候选框并向后端提交借阅请求。
* **`return.js`**：**还书联动交互**。实现待还读者实时模糊筛选、名下未还图书卡片呈现及一键归还操作。
* **`fine.js`**：**罚金缴纳交互**。实现未缴罚单卡片渲染、实时模糊筛选读者、单笔卡片高亮选中及缴费提交。
* **`admin.js`**：**系统运维交互**。触发逾期全库扫描与渲染违规冻结读者列表。
* **`readers.js`**：**读者管理交互**。实现读者列表实时筛选、新增读者校验、弹窗修改手机号及注销确认。
* **`recommend.js`**：**AI 推荐交互**。选择目标读者并异步获取个性化图书推荐卡片与匹配度得分。

---

## 🖼️ 视图与静态样式 (`templates/` & `static/`)

* **`templates/index.html`**：**主控制台视图**。包含侧边栏导航及各业务 Tab 的响应式布局容器。
* **`templates/login.html`**：**管理员登录视图**。提供用户登录表单及异步身份认证。
* **`static/style.css`**：**全局样式文件**。定制侧边栏排版、卡片阴影动画、高亮选框以及滚动条样式。

---

## ✨ 核心功能

| 模块 | 功能 |
|------|------|
| 图书检索 | 支持按书名、作者模糊搜索，按分类筛选 |
| 借阅管理 | 借书校验库存与借阅上限，库存与记录在同一事务提交 |
| 还书管理 | 自动检测逾期，按 1.5 元/天生成罚单，防重复开单 |
| 罚金管理 | 查询未缴罚单，缴费后自动检测是否解冻账号 |
| 读者管理 | 新增读者、修改手机号、注销读者 |
| 系统维护 | 批量扫描逾期、冻结违规账号 |
| 智能推荐 | 基于 TF-IDF + 余弦相似度，按借阅历史推荐图书；冷启动推荐热门书目 |

---

## 🧠 推荐算法说明

1. 特征构造：将图书的类别、作者、出版社拼接为特征文本。
2. 向量化：使用 TF-IDF 计算各特征词的权重。
3. 相似度计算：计算候选图书与读者已借图书的平均余弦相似度。
4. 排序推荐：按相似度降序取前 5 本。
5. 冷启动：无借阅历史时，按借出次数推荐热门书目。

---

## 📊 数据模型

| 表名 | 说明 |
|------|------|
| 图书类别 | 图书分类信息 |
| 图书信息 | 图书基本信息（含简介、库存） |
| 读者信息 | 读者基本信息（含账号状态） |
| 借阅记录 | 借阅历史（含借出、应还、归还日期） |
| 罚款记录 | 逾期罚款记录 |

---

## 🧪 测试数据

database/library_system.sql 已包含完整的测试数据：

- 5 个图书分类
- 8 本图书（含简介）
- 5 位读者
- 多条借阅记录（已归还 / 借阅中 / 逾期）
- 若干罚款记录（未缴 / 已缴）

---

## 📄 License

本项目仅用于学习与交流。