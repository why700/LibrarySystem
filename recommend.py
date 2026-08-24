# recommend.py - AI推荐服务（修复 SQL 构建防注入 & 缺失值防报错处理）
import mysql.connector
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os

db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", "123456"),
    "database": os.getenv("DB_NAME", "librarysystem")
}

def get_connection():
    return mysql.connector.connect(**db_config)

def get_recommendations(reader_id, top_n=5):
    """
    基于读者已借图书的类别、作者及出版社，推荐相似图书
    """
    try:
        conn = get_connection()
        
        # 1. 获取该读者已借的所有图书编号
        query_borrowed = """
            SELECT DISTINCT 图书编号 
            FROM 借阅记录 
            WHERE 读者编号 = %s
        """
        borrowed_df = pd.read_sql(query_borrowed, conn, params=(reader_id,))
        
        # 若无历史借阅，推荐热门图书
        if borrowed_df.empty:
            hot_query = """
                SELECT 图书编号, 书名, 作者, 类别编号, 现有库存
                FROM 图书信息 
                ORDER BY (总库存 - 现有库存) DESC 
                LIMIT %s
            """
            hot_df = pd.read_sql(hot_query, conn, params=(top_n,))
            conn.close()
            return hot_df.to_dict('records')
        
        borrowed_isbns = borrowed_df['图书编号'].tolist()
        
        # 2. 读取所有未借图书与已借图书信息
        placeholders = ','.join(['%s'] * len(borrowed_isbns))
        
        query_all = f"""
            SELECT 图书编号, 书名, 作者, 出版社, 类别编号
            FROM 图书信息
            WHERE 图书编号 NOT IN ({placeholders})
        """
        all_books_df = pd.read_sql(query_all, conn, params=borrowed_isbns)
        
        if all_books_df.empty:
            conn.close()
            return []
        
        query_borrowed_features = f"""
            SELECT 图书编号, 书名, 作者, 出版社, 类别编号
            FROM 图书信息
            WHERE 图书编号 IN ({placeholders})
        """
        borrowed_features_df = pd.read_sql(query_borrowed_features, conn, params=borrowed_isbns)
        conn.close()
        
        # 3. 数据清洗防空值报错，拼接特征文本
        for df in [all_books_df, borrowed_features_df]:
            df['类别编号'] = df['类别编号'].fillna('').astype(str)
            df['作者'] = df['作者'].fillna('')
            df['出版社'] = df['出版社'].fillna('')
            df['特征'] = df['类别编号'] + ' ' + df['作者'] + ' ' + df['出版社']

        # 4. TF-IDF 文本特征抽取
        all_features = list(borrowed_features_df['特征']) + list(all_books_df['特征'])
        
        vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
        tfidf_matrix = vectorizer.fit_transform(all_features)
        
        # 5. 余弦相似度计算
        n_borrowed = len(borrowed_features_df)
        similarity_matrix = cosine_similarity(tfidf_matrix[:n_borrowed], tfidf_matrix[n_borrowed:])
        
        avg_similarities = similarity_matrix.mean(axis=0)
        
        # 6. 取 Top N 结果
        all_books_df['相似度'] = avg_similarities
        top_books = all_books_df.sort_values('相似度', ascending=False).head(top_n)
        
        result = top_books[['图书编号', '书名', '作者', '相似度']].to_dict('records')
        for r in result:
            r['相似度'] = float(r['相似度'])
            
        return result

    except Exception as e:
        print(f"❌ 智能推荐模块运行异常: {e}")
        return []