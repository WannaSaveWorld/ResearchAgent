# ResearchAgent · 科研文献助手

以 [PaperQA](https://github.com/Future-House/paper-qa) 为文献证据问答基础的独立项目，增加 PDF 页码溯源、BM25 + FAISS + RRF 混合检索、LangGraph 工作流、FastAPI 服务和显式授权的 MCP 外部论文搜索。

适用于组会准备、课题调研和论文结论核查。回答附带证据原文及来源，仍需人工确认引用是否真正支持结论。

## 功能

- **文献入库**：内容哈希去重、逐页提取文本、识别常见章节标题、分块、保留 PDF 文件页序与页标签。
- **混合检索**：BM25 词法检索与真实 embedding 的 FAISS 余弦相似度召回，通过 RRF 融合排名。
- **PaperQA 问答**：混合检索决定候选，PaperQA 进行证据摘要及引用回答，关闭上游重复召回。
- **来源校验**：引用只能映射到实际候选，页码由解析器确定；未知引用或无有效引用时拒答。
- **Agent 工作流**：LangGraph 管理本地检索、可选外部搜索、回答和引用检查，有步数及超时限制。
- **可运行服务**：中文上传/问答页面、Swagger API、SQLite 文献与会话持久化。
- **评测与测试**：合成演示文献、标注检索题集、Recall@k/MRR@k 评测及无需真实密钥的协议测试。

## 快速开始

推荐 Python 3.12；支持 Python 3.11-3.13。以下在仓库根目录运行。

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Linux/macOS：使用 `source .venv/bin/activate` 和 `cp .env.example .env`。

Windows 若遇到依赖的长路径错误，优先把仓库放到较短路径（例如 `D:\ResearchAgent`），再安装。项目无需修改注册表。不要提交 `.venv`。

编辑 `.env` 中的聊天与 embedding 服务配置，然后启动：

```powershell
python -m uvicorn researchagent.api:app_factory --factory --host 127.0.0.1 --port 8000
```

- 页面：<http://127.0.0.1:8000>
- API：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/health>

默认仅供本机单用户使用，不含公开服务所需的认证、租户隔离及生产运维设施。

## 配置模型

默认使用兼容聊天及 embeddings API 的服务；API key 由使用者自行提供。`RA_CHAT_MODEL` 采用 LiteLLM 模型名，例如 `openai/gpt-4o-mini`。可替换成兼容供应商支持的模型和端点，不要将密钥放入 README、代码或 Git。

```dotenv
RA_CHAT_MODEL=openai/gpt-4o-mini
RA_CHAT_BASE_URL=https://api.openai.com/v1
RA_CHAT_API_KEY=your-key
RA_EMBEDDING_BACKEND=api
RA_EMBEDDING_MODEL=text-embedding-3-small
RA_EMBEDDING_BASE_URL=https://api.openai.com/v1
RA_EMBEDDING_API_KEY=your-key
```

这些是配置示例，不代表附送额度，也不保证任意供应商的兼容行为。将 PDF 片段发送至远程 embedding/聊天服务前，应确认这些文献允许发送。

也可安装 `python -m pip install -e ".[local]"`，选择 `RA_EMBEDDING_BACKEND=local` 并将 `RA_EMBEDDING_MODEL` 设置为实际本地 sentence-transformers 模型名或路径。首次下载模型需要网络和磁盘空间；聊天仍由单独的配置决定。项目不会用随机向量或哈希向量代替生产语义检索。

**没有密钥也可以**：上传文献、查看来源、调用 `/search?mode=bm25&q=...`、运行离线测试和 BM25 演示评测。聊天和语义检索缺少配置时返回明确错误，不生成假回答。

## 外部论文搜索（可选）

示例提供一个真正调用 arXiv 元数据 API 的 MCP 服务：

```powershell
python examples/mcp_paper_search.py
```

在 `.env` 配置：

```dotenv
RA_MCP_URL=http://127.0.0.1:8001/mcp
RA_MCP_TOOL=search_papers
```

重启 ResearchAgent，在页面勾选“允许外部论文检索”。**仅本地未召回候选且用户显式开启时调用**，每次请求最多一次；关闭时不联系该服务。首版不根据模型判断任意执行工具。

工具契约：接收 `{"query":"..."}`，返回 `{"results":[{"title":"...","url":"https://...","text":"摘要或证据"}]}`。外部证据标记 URL，不伪造 PDF 页码。示例检索摘要而非下载全文，受 arXiv 可用性和使用限制影响。

## 演示与评测

```powershell
python scripts/demo.py
python scripts/evaluate.py --modes bm25 --k 3
# 配置真实 embedding 后比较同一题集上的三种方法：
python scripts/evaluate.py --modes bm25 vector hybrid --k 3
```

演示为**自制5份、10页合成文本和10个问题**，不是公开论文，也不是实验室真实效果评测。输出在 `data/evaluation.json`。报告是文档级 Recall@k 和 MRR@k；候选先按文档去重，不是片段级指标。可通过 `--questions` 指定真实标注 JSON：

```json
[{"question":"研究问题","relevant_files":["paper.pdf"]}]
```

评测文件名应唯一；实际评测应增加问题数量、同义表达、困难负样本和无答案问题。不要把合成数据高分写成真实检索提升。

## API 一览

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | `/health` | 运行和配置状态，不返回密钥 |
| POST / GET | `/documents` | 上传 / 列出 PDF |
| GET | `/documents/{id}/source?page=1` | 返回原 PDF，查看器可追加 `#page=1` |
| GET | `/search?q=...&mode=hybrid&k=6` | 返回候选及检索分数 |
| POST | `/sessions` | 创建会话 |
| GET | `/sessions/{id}` | 已保存消息 |
| POST | `/ask` | 问题、可选 session_id 与 external |

会话保留历史消息，并使用最近三个用户问题作为有限主题上下文；不是完整对话重写系统。历史回答不作为本次问题的文献证据。一次成功请求后保存用户问题及结构化回答。

## 测试

```powershell
python -m pytest -q
python -m ruff check src tests scripts examples
python -m pip check
```

测试包含真实 FAISS、真实 PaperQA 证据/回答流程、LangGraph、API 和本机 HTTP 协议。测试中的 LLM 与部分 embedding 是**明确标注的替身**，没有宣称真实供应商质量或模型准确率。真实密钥、线上模型和 arXiv 服务的验证必须另行执行。

参考开发环境锁定见 `requirements-lock.txt`（Python 3.12 / Windows）。跨平台优先按 `pyproject.toml` 安装；完整锁文件中平台依赖带有标记。

## 数据与索引

默认 `data/` 下包含 SQLite、原始 PDF、FAISS 索引及清单，均被 Git 忽略。不要直接加载来历不明的索引文件。文件名仅用于显示，原文件按 SHA-256 ID 存储。

索引清单记录模型标识、语料摘要、向量维度和索引摘要。新增文献会触发重建；更换 embedding 模型需使用新数据目录或在停止服务后备份并重建索引目录。首版针对小规模文献库，未实现增量向量更新和分布式索引。

## 复用与新增边界

**PaperQA 提供**：文献/片段模型、证据摘要、带引用回答及其格式化能力。

**本项目增加**：逐页解析与来源元数据、SQLite 管理、BM25/FAISS/RRF、候选注入适配、引用校验、LangGraph、有界 MCP 工具调用、FastAPI 页面与接口、评测和测试。

采用独立依赖集成，未将 PaperQA 上游整体复制并改名。保留来源说明和 Apache-2.0 许可证；第三方组件继续遵循各自许可证。架构与局限见 [docs/architecture.md](docs/architecture.md)，验证记录见 [docs/validation.md](docs/validation.md)。
