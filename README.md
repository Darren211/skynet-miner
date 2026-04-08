# 天网痛点挖掘机 (Skynet Miner) 🌐⚡

像天网一样，无死角捕获一切潜在的商业商机！

`天网痛点挖掘机` 是一个霸道且开箱即用的自动化商机挖掘系统。它基于 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 的底层爬虫架构，搭配无情的大语言模型（LLM）提取引擎，能够全自动降噪监控社交网络上的吐槽、避雷与求推荐帖子，并将杂乱的内容结构化提炼为真正的**商业机会、痛点以及未被满足的赛道需求**。

同时附带了一个极具科技质感的交互式大屏看板，让你像看盘一样实时审阅涌现出的新商机。

---

## 🏗 架构说明

本项目分为三个核心模块，相互解耦：
1. **爬虫引擎 (MediaCrawler)**：利用关键字在小红书自动执行搜索扒取，产生未经清洗的海量源文件。
2. **大模型提炼漏斗 (LLM Extractor)**：全天候扫描数据库，剔除废话和水军，保留包含有效 `痛点` 和 `未满足需求` 的高价值信息。
3. **数据可视化看板 (Web Dashboard)**：在浏览器里供你实时检索最新的商机。

---

## 🛠 快速上手指南

### 1. 环境准备
确保您的机器安装了 Python (>=3.10) 和 MySQL 数据库。

```bash
# 1. 安装核心爬虫所需依赖
pip install -r requirements.txt

# 2. 安装大模型分析与看板所需依赖
pip install openai fastapi uvicorn pydantic pymysql
```

### 2. 配置环境变量

复制 `.env.example` 作为 `.env`，填入你的 MySQL 密码和大模型 API Key：
```env
# 数据库配置
DB_HOST=localhost
DB_USER=root
DB_PASS=您的数据库密码
DB_NAME=media_crawler

# 大模型配置 (支持任何遵循 OpenAI 格式的接口，如阿里百炼、DeepSeek、智谱等)
LLM_API_KEY=sk-xxxxxx
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-max
```
*(注意：`MediaCrawler` 原本的 `base_config.py` 与 `db_config.py` 也请按需调整)*

---

### 3. 一键启动流程

#### 步骤 一：初始化数据库与拉起爬虫
```bash
# 这一步会自动建表
python main.py --init_db mysql

# 启动爬虫抓取（记得扫码登录小红书账号）
python main.py --platform xhs --lt qrcode --type search
```
*(爬虫抓取的规则与受众，可以通过修改 `config/base_config.py` 里面的 `KEYWORDS` 调整，强烈推荐改成您想看的细分行业吐槽。)*

#### 步骤 二：启动 LLM AI 分析引擎
打开一个新的终端选项卡：
```bash
cd analyzer
python llm_extractor.py
```
*(该脚本将以心跳监听的方式后台死循环执行，每找到新帖子便执行解析。)*

#### 步骤 三：启动商机可视化看板
再打开一个新的终端选项卡：
```bash
cd dashboard
python backend_api.py
```
随后，直接使用浏览器访问大屏效果：**http://127.0.0.1:8000/static/index.html**

---

## 📜 声明与协议
1. 爬虫底层技术遵循原开源项目的要求，请勿用于非法或给平台带来极高负载的恶意目的。
2. 请合理控制抓取频率 (`CRAWLER_MAX_NOTES_COUNT` 等参数)，切勿过度。
3. 本项目提供的信息仅作商业灵感参考，大模型的推断不代表事实真相。
