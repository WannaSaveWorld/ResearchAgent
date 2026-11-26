# ResearchAgent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 实现并上传可运行的科研文献检索与引用问答独立项目。
**Architecture:** SQLite 保存文献片段和会话；BM25/FAISS/RRF 提供候选；PaperQA 负责证据和回答；LangGraph 控制流程；FastAPI 暴露本地接口和中文页面。
**Tech Stack:** Python 3.12、PaperQA、pypdf、rank-bm25、FAISS、LangGraph、FastAPI、MCP。
**Spec:** ../specs/2026-11-26-researchagent-design.md

## Global Constraints
- 不提交密钥、个人文档或运行数据。
- 引用页码必须来自文献解析；证据不足可拒答。
- 无线上密钥时离线测试与真实调用明确区分。
- 外部检索默认关闭，仅访问显式配置的 MCP 服务。

## Review Focus
- 扫描/空PDF：明确拒绝并提示OCR。
- 同名与重复PDF：哈希去重而非文件名覆盖。
- 模型切换：拒绝使用不匹配向量索引。
- 引用不存在：不输出无法溯源的引用。
- 超时/并发会话：不无限调用、不串会话。

### Task 1: 文献与存储
Files: src/researchagent/{config,models,store,ingest}.py; tests/test_ingest.py
Interfaces: Chunk、Document；Store.add_pdf(data,name)、Store.chunks(document_ids)、Store.get_document(id)。
- [x] 测试多页PDF页码、中文、重复上传、扫描件及安全文件名，确认先失败。
- [x] 实现逐页章节分块与SQLite事务持久化，运行测试。

### Task 2: 检索与模型适配
Files: embeddings.py、retrieval.py、paperqa_engine.py；tests/test_retrieval.py、test_paperqa.py。
Interfaces: HybridRetriever.search(question,k,mode)->list[Hit]；PaperQAEngine.answer(question,hits)->Answer。
- [x] 测试 RRF 去重、真实FAISS持久化与模型不匹配，以及PaperQA注入候选和引用映射，确认先失败。
- [x] 实现标准API embedding与可选本地模型、BM25/FAISS/RRF及PaperQA适配，运行测试。

### Task 3: 图编排、MCP与API
Files: workflow.py、tools.py、api.py、static/index.html；tests/test_workflow.py、test_api.py。
Interfaces: ResearchWorkflow.ask(question,session_id,external)->Answer；create_app(settings,services)->FastAPI。
- [x] 测试上传到引用流程、工具限制与超时、无证据拒答、会话持久化、错误状态码，确认先失败。
- [x] 实现LangGraph有界执行、MCP客户端及本地API与页面，运行测试。

### Task 4: 验收与上传
Files: README.md、.env.example、Dockerfile、scripts/demo.py、scripts/evaluate.py、docs/architecture.md、LICENSE、NOTICE。
- [x] 提供自制演示文献与有标注检索题集，运行 BM25/向量/混合 Recall@k 和MRR评测。
- [x] 运行完整测试、lint及依赖检查，审查配置与数据排除，记录真实验证结果。
- [ ] 独立复核后修复重要问题；提交并上传用户授权的私有仓库，核实远端文件和提交。
