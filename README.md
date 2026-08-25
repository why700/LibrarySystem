# 📚 图书借阅管理系统 (Library Management System)

本项目基于 **FastAPI + SQLAlchemy 2.0 (Async) + MySQL + Jinja2/原生 JS** 构建，采用模块化分层架构设计。

---

## 📁 项目目录与文件功能清单

### 1. 核心与配置入口
* **`app.py`**：系统主入口。负责初始化 FastAPI 实例、挂载静态资源与 Session 中间件、管理数据库连接生命周期（`lifespan`），并集中注册 `routers/` 中的所有业务路由。
* **`config.py`**：全局基础配置文件。存放管理员账密（`ADMIN_USERNAME` / `ADMIN_PASSWORD`）及系统常量。
* **`database.py`**：数据库与 ORM 映射层。基于 SQLAlchemy 2.0 异步驱动（`asyncmy`）创建异步引擎（`engine`）和会话生成器（`AsyncSessionLocal`），并定义了 `Book`、`Reader`、`BorrowRecord`、`FineRecord`、`BookCategory` 等数据表模型类。
* **`recommend.py`**：AI 智能推荐算法模块。基于 TF-IDF 和余弦相似度（Cosine Similarity），根据读者的历史借阅画像为其推荐相似图书。

---

### 2. 路由控制层 (`routers/`)
* **`routers/__init__.py`**：包标识文件，使 `routers` 目录可作为 Python 模块被导入。
* **`routers/auth.py`**：管理员登录与会话模块。包含管理员登录校验接口（`/api/login`）和退出登录（`/logout`）。
* **`routers/books.py`**：图书与分类模块。提供图书模糊搜索、在馆图书查询、图书类别列表获取以及调用 AI 推荐的接口。
* **`routers/borrow.py`**：核心借还业务模块。包含读者借书事务（库存扣减与上限校验）、未还记录查询、还书处理及逾期自动开罚单逻辑。
* **`routers/fines.py`**：罚金管理模块。提供未缴罚单列表查询、在线缴纳罚金及结清后自动解冻账号的业务逻辑。
* **`routers/readers.py`**：读者信息管理模块。提供读者信息增删改查、手机号修改、读者注销前校验未还记录等接口。
* **`routers/admin.py`**：系统运维模块。提供一键扫描逾期借阅、批量冻结违规账号及违规“老赖”名单查询接口。

---

### 3. 前端与界面呈现
* **`templates/`**（页面模板）
  * **`index.html`**：系统核心管理主界面。包含图书查询、借还书、罚金、运维、AI推荐、读者管理等单页 Tab。
  * **`login.html`**：管理员登录页面。
* **`static/`**（静态资源）
  * **`script.js`**：前端交互脚本。封装 `apiCall` 工具函数，负责各模块的数据异步请求、DOM 动态渲染、防重点击和表单校验。
  * **`style.css`**：全局样式表。定义侧边栏固定布局、卡片动效、滚动条美化等。