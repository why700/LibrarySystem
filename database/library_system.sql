-- ============================================================
-- 图书借阅管理系统 - 数据库初始化脚本
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS 罚款记录;
DROP TABLE IF EXISTS 借阅记录;
DROP TABLE IF EXISTS 图书信息;
DROP TABLE IF EXISTS 读者信息;
DROP TABLE IF EXISTS 图书类别;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. 图书类别表
CREATE TABLE 图书类别 (
    类别编号 INT AUTO_INCREMENT PRIMARY KEY,
    类别名称 VARCHAR(50) NOT NULL UNIQUE,
    类别描述 VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 图书信息表
CREATE TABLE 图书信息 (
    图书编号 VARCHAR(20) PRIMARY KEY COMMENT '即ISBN号',
    书名 VARCHAR(100) NOT NULL,
    作者 VARCHAR(50) NOT NULL,
    出版社 VARCHAR(50),
    类别编号 INT NOT NULL,
    总库存 INT NOT NULL CHECK (总库存 >= 0),
    现有库存 INT NOT NULL CHECK (现有库存 >= 0),
    简介 TEXT COMMENT '图书简介',
    FOREIGN KEY (类别编号) REFERENCES 图书类别(类别编号) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 读者信息表
CREATE TABLE 读者信息 (
    读者编号 INT AUTO_INCREMENT PRIMARY KEY,
    姓名 VARCHAR(50) NOT NULL,
    联系电话 VARCHAR(20) UNIQUE NOT NULL,
    最大借阅量 INT DEFAULT 5,
    已借数量 INT DEFAULT 0,
    账号状态 VARCHAR(10) DEFAULT '正常'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 借阅记录表
CREATE TABLE 借阅记录 (
    记录编号 INT AUTO_INCREMENT PRIMARY KEY,
    读者编号 INT NOT NULL,
    图书编号 VARCHAR(20) NOT NULL,
    借出日期 DATE NOT NULL,
    应还日期 DATE NOT NULL,
    归还日期 DATE DEFAULT NULL,
    记录状态 VARCHAR(10) DEFAULT '借阅中',
    FOREIGN KEY (读者编号) REFERENCES 读者信息(读者编号) ON UPDATE CASCADE,
    FOREIGN KEY (图书编号) REFERENCES 图书信息(图书编号) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. 罚款记录表
CREATE TABLE 罚款记录 (
    罚款编号 INT AUTO_INCREMENT PRIMARY KEY,
    记录编号 INT NOT NULL UNIQUE,
    罚款金额 DECIMAL(10, 2) NOT NULL CHECK (罚款金额 > 0),
    罚款原因 VARCHAR(100) DEFAULT '逾期未还',
    是否结清 BOOLEAN DEFAULT FALSE,
    生成时间 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    备注 VARCHAR(100) DEFAULT '未缴费',
    FOREIGN KEY (记录编号) REFERENCES 借阅记录(记录编号) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 测试数据
-- ============================================================

-- 图书类别
INSERT INTO 图书类别 (类别名称, 类别描述) VALUES
('计算机科学', '包含编程、算法、数据库、人工智能等方向的书籍'),
('经济与管理', '包含宏观经济、微观经济、金融、企业管理等'),
('文学小说', '中外古典与现代文学作品'),
('自然科学', '物理、化学、生物、天文等基础科学'),
('历史哲学', '历史、哲学、心理学等人文社科');

-- 图书信息
INSERT INTO 图书信息 (图书编号, 书名, 作者, 出版社, 类别编号, 总库存, 现有库存, 简介) VALUES
('9787111544937', '数据库系统概念', 'Abraham Silberschatz', '机械工业出版社', 1, 100, 99, '数据库系统经典教材，全面介绍关系数据库理论、SQL语言和事务管理。'),
('9787115545688', 'Python编程：从入门到实践', 'Eric Matthes', '人民邮电出版社', 1, 100, 100, 'Python入门必读，从零开始学习Python编程，包含大量实战项目。'),
('9787302423287', '微观经济学', '保罗·萨缪尔森', '清华大学出版社', 2, 100, 99, '经济学经典著作，系统介绍微观经济学的基本原理和分析方法。'),
('9787532786831', '百年孤独', '加西亚·马尔克斯', '上海译文出版社', 3, 100, 100, '魔幻现实主义代表作，讲述布恩迪亚家族七代人的传奇故事。'),
('9787111641247', '深入理解计算机系统', 'Randal E.Bryant', '机械工业出版社', 1, 100, 100, '计算机系统底层原理经典，涵盖硬件、操作系统、编译原理等核心知识。'),
('9787123456789', '算法导论', 'Thomas H. Cormen', '机械工业出版社', 1, 50, 48, '算法领域权威著作，涵盖排序、搜索、图算法等核心内容。'),
('9787544253994', '三体', '刘慈欣', '重庆出版社', 3, 80, 80, '中国科幻巅峰之作，讲述人类与三体文明的星际战争。'),
('9787508657590', '人类简史', '尤瓦尔·赫拉利', '中信出版社', 5, 60, 58, '从认知革命到现代社会，梳理人类历史的宏大叙事。');

-- 读者信息
INSERT INTO 读者信息 (姓名, 联系电话, 最大借阅量, 已借数量, 账号状态) VALUES
('张三', '13800000001', 5, 0, '正常'),
('李四', '13800000002', 5, 3, '正常'),
('王五', '13800000003', 5, 0, '冻结'),
('赵六', '13800000004', 5, 2, '正常'),
('孙七', '13800000005', 5, 1, '正常');

-- 借阅记录（已归还 + 借阅中 + 逾期）
INSERT INTO 借阅记录 (读者编号, 图书编号, 借出日期, 应还日期, 归还日期, 记录状态) VALUES
(1, '9787111544937', '2026-01-01', '2026-01-31', '2026-01-20', '已归还'),
(2, '9787115545688', '2026-02-01', '2026-03-03', '2026-02-25', '已归还'),
(2, '9787111544937', '2026-08-10', DATE_ADD('2026-08-10', INTERVAL 30 DAY), NULL, '借阅中'),
(4, '9787115545688', '2026-08-20', DATE_ADD('2026-08-20', INTERVAL 30 DAY), NULL, '借阅中'),
(2, '9787302423287', DATE_SUB(CURDATE(), INTERVAL 45 DAY), DATE_SUB(CURDATE(), INTERVAL 15 DAY), NULL, '借阅中'),
(4, '9787111641247', DATE_SUB(CURDATE(), INTERVAL 55 DAY), DATE_SUB(CURDATE(), INTERVAL 25 DAY), NULL, '借阅中');

-- 罚款记录（为逾期记录自动生成）
INSERT INTO 罚款记录 (记录编号, 罚款金额, 罚款原因, 备注)
SELECT 记录编号, DATEDIFF(CURDATE(), 应还日期) * 1.5, '逾期还书', '未缴费'
FROM 借阅记录
WHERE 归还日期 IS NULL AND 应还日期 < CURDATE();