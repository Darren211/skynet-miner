from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pymysql
import os

app = FastAPI(title="XHS Insight Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态网页 (指向前台页面)
app.mount("/static", StaticFiles(directory="public"), name="static")

# 数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "123456")
DB_NAME = os.getenv("DB_NAME", "media_crawler")

def get_db():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

@app.get("/api/insights")
def get_insights(limit: int = 50, keyword: str = ""):
    """提取分析过的痛点内容，支持关键字查询"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 查询痛点表，支持模糊搜索，排空完全没有实质内容的记录
            sql = """
                SELECT id, source_type, domain, pain_point, sentiment, unmet_need, created_at 
                FROM insight_pain_points 
                WHERE (pain_point LIKE %s OR unmet_need LIKE %s OR domain LIKE %s)
                  AND (
                      (pain_point IS NOT NULL AND pain_point != '' AND pain_point != '无' AND pain_point != '""')
                      OR
                      (unmet_need IS NOT NULL AND unmet_need != '' AND unmet_need != '无' AND unmet_need != '""')
                  )
                ORDER BY created_at DESC 
                LIMIT %s
            """
            search_pattern = f"%{keyword}%"
            cursor.execute(sql, (search_pattern, search_pattern, search_pattern, limit))
            rows = cursor.fetchall()
            
            # 手工聚合一个雷达图数据或分类分布
            cursor.execute("""
                SELECT domain, COUNT(*) as count 
                FROM insight_pain_points 
                WHERE domain != '' AND domain IS NOT NULL
                GROUP BY domain 
                ORDER BY count DESC 
                LIMIT 10
            """)
            domain_stats = cursor.fetchall()
            
        return {"status": "success", "data": rows, "stats": domain_stats}
    except Exception as e:
        return {"status": "error", "msg": str(e)}
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    # 本地启动 uvicorn
    uvicorn.run("backend_api:app", host="127.0.0.1", port=8000, reload=True)
