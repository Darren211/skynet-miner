import os
import json
import pymysql
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Optional

load_dotenv() # 自动加载项目根目录的 .env 文件

# ================= 配置区 =================
# 您的数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "123456")
DB_NAME = os.getenv("DB_NAME", "media_crawler")

# 大模型配置 
LLM_API_KEY = os.getenv("LLM_API_KEY", "your-api-key-here")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-max")

# ================= 数据结构 =================
class PainPointDetail(BaseModel):
    is_insightful: bool       # 是否包含真实的痛点或需求（如果是无关内容填 False）
    domain: Optional[str]     # 所属领域/赛道（如：小家电、SaaS、自媒体工具、美妆等）
    pain_point: Optional[str] # 具体的痛点描述（简明扼要，如：剪辑软件导出太慢、找不到好看的模板）
    sentiment: Optional[str]  # 情绪强度（如：极度抱怨、一般吐槽、求助）
    unmet_need: Optional[str] # 潜在的未满足需求（用户想要的理想解决方案是什么）

class ExtractedInsight(BaseModel):
    items: List[PainPointDetail]

# ================= 数据库工具 =================
def get_db_connection():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

def init_insight_table():
    """初始化用于存放最终痛点分析结果的数据表"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS insight_pain_points (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    source_id VARCHAR(255) COMMENT '原始帖子或评论ID',
                    source_type VARCHAR(50) COMMENT 'note 或 comment',
                    domain VARCHAR(100) COMMENT '赛道/领域',
                    pain_point TEXT COMMENT '痛点描述',
                    sentiment VARCHAR(50) COMMENT '情绪',
                    unmet_need TEXT COMMENT '未满足需求',
                    original_text TEXT COMMENT '原始文本(便于回溯)',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            """)
            # 创建分析状态表，记录哪些已经分析过
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS insight_process_log (
                    source_id VARCHAR(255) PRIMARY KEY,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
    finally:
        conn.close()

# ================= 核心分析逻辑 =================
def analyze_content(client: OpenAI, text: str) -> Optional[PainPointDetail]:
    prompt = f"""
    你是一个擅长商业分析和用户需求挖掘的专家。请阅读以下小红书的用户内容（可能是帖子标题+正文，或者是评论），从中提取出用户痛点和未被满足的需求。
    如果这不是一个表达诉求、吐槽或痛点的内容，请将 is_insightful 置为 false。
    
    分析内容如下：
    {text}
    
    请严格按照以下 JSON 数据格式输出，不要包含任何 markdown 代码块标记，只输出纯 JSON 字符串：
    {{
        "items": [
            {{
                "is_insightful": true,
                "domain": "必须填写该需求所属的具体商业垂直领域，只能是词汇（如：办公软件、自媒体工具、小家电、健身器材、心理健康、宠物用品、美妆护肤等，绝不能输出'未知'或留空）",
                "pain_point": "具体的痛点描述",
                "sentiment": "情绪强度，如：吐槽、求助、抱怨",
                "unmet_need": "潜在的未满足需求，即用户想要但没被满足的东西"
            }}
        ]
    }}
    """
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是一个严谨的商业分析AI，只输出合法的 JSON 字符串。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        content = response.choices[0].message.content.strip()
        if content.startswith('```json'): # 移除可能存在的markdown标记
            content = content.replace('```json', '', 1)
            if content.endswith('```'):
                content = content[:-3]
        
        data = json.loads(content)
        items = data.get("items", [])
        if items and len(items) > 0:
            item = items[0]
            return PainPointDetail(
                is_insightful=item.get("is_insightful", False),
                domain=item.get("domain", ""),
                pain_point=item.get("pain_point", ""),
                sentiment=item.get("sentiment", ""),
                unmet_need=item.get("unmet_need", "")
            )
        return None
    except Exception as e:
        print(f"调用 LLM 失败: {e}")
        return None

def process_unprocessed_notes():
    """读取还未处理的日记进行大模型分析"""
    conn = get_db_connection()
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    
    try:
        with conn.cursor() as cursor:
            # 查出最新的10条还没有被分析过的小红书笔记或评论
            # 先处理帖子
            cursor.execute("""
                SELECT n.note_id as id, n.title, n.desc as content, 'note' as type 
                FROM xhs_note n 
                LEFT JOIN insight_process_log l ON n.note_id = l.source_id 
                WHERE l.source_id IS NULL AND n.desc IS NOT NULL
                LIMIT 5
            """)
            items = cursor.fetchall()

            # 再查5条评论
            cursor.execute("""
                SELECT c.comment_id as id, '' as title, c.content as content, 'comment' as type 
                FROM xhs_note_comment c 
                LEFT JOIN insight_process_log l ON c.comment_id = l.source_id 
                WHERE l.source_id IS NULL AND c.content IS NOT NULL
                LIMIT 5
            """)
            items.extend(cursor.fetchall())
            
            if not items:
                print("没有找到新的需要分析的笔记或评论。")
                return

            for item in items:
                item_id = item['id']
                item_type = item['type']
                text_to_analyze = f"【标题】{item['title']}\n【正文/评论】{item['content']}"
                print(f"正在分析 ({item_type}) ID: {item_id} ...")
                
                # 1. 调大模型分析
                result: PainPointDetail = analyze_content(client, text_to_analyze)
                
                # 2. 如果包含有效痛点或有效未满足需求，则入库
                valid_pain = result and result.pain_point and result.pain_point.strip() not in ('', '无', 'None', '""')
                valid_need = result and result.unmet_need and result.unmet_need.strip() not in ('', '无', 'None', '""')
                if result and result.is_insightful and (valid_pain or valid_need):
                    cursor.execute("""
                        INSERT INTO insight_pain_points 
                        (source_id, source_type, domain, pain_point, sentiment, unmet_need, original_text)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        item_id, item_type, 
                        result.domain or '未知', 
                        result.pain_point or '', 
                        result.sentiment or '', 
                        result.unmet_need or '', 
                        text_to_analyze
                    ))
                    print(f"  -> 发现机会！领域：{result.domain}")
                else:
                    print(f"  -> 无痛点内容，跳过。")
                
                # 3. 标记为已处理 (使用 IGNORE 避免抓取重复数据导致的报错)
                cursor.execute("INSERT IGNORE INTO insight_process_log (source_id) VALUES (%s)", (item_id,))
                conn.commit()

    finally:
        conn.close()

if __name__ == "__main__":
    print("开始初始化数据库...")
    init_insight_table()
    print("数据库初始化完成。开始持续后台扫描未处理的笔记...")
    
    # 持续执行循环
    import time
    while True:
        try:
            process_unprocessed_notes()
        except Exception as e:
            print(f"本轮处理发生错误: {e}")
        
        # 避免过于频繁请求，休息 10 秒钟再扫下一次
        print("====== 休息 10 秒后继续下一轮提取 ======")
        time.sleep(10)
