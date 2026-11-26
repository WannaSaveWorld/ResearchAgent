# 验证记录

日期：2026-11-26。环境：Windows / Python 3.12.14。

## 已实际执行

- `python -m pytest -q`：19项通过。
- `python -m ruff check src tests scripts examples`：通过。
- `python -m pip check`：无依赖冲突。
- Chrome 无头浏览器实测桌面1366px与手机390px页面，文献列表正常、无JS异常、手机无横向溢出，缺少模型密钥时显示明确错误。
- `python scripts/demo.py`：生成并入库5份自制PDF、10页、10片段。
- `python scripts/evaluate.py --modes bm25 --k 3`：10个合成问题，文档级Recall@3=1.0，MRR@3=1.0。题集非常简单，仅验证评测流程，不作为真实效果或收益证明。

## 测试覆盖

1. PDF多页与页序、文件名安全、同名不同文档、哈希去重、重启存储、扫描件拒绝、上传大小及并发重复上传。
2. 真实FAISS写入与重载、模型变更拒绝、RRF去重、BM25查询及空语料。
3. 真实PaperQA证据摘要与回答流程，注入LLM替身验证候选流转及引用映射，虚构引用拒答。
4. 真实LiteLLM通过本地模拟聊天HTTP端点调用，真实embedding HTTP协议，异常响应处理；不是供应商线上测试。
5. LangGraph本地命中、无证据拒答、外部开关、工具超时及引用校验。
6. 真实MCP SDK连接本地HTTP测试服务，验证query入参与results结构；不调用arXiv。
7. FastAPI上传、来源页序检查、会话隔离与持久化、非法问题和配置缺失错误。

## 尚未执行的真实环境验证

- 使用用户真实密钥的聊天与embedding供应商鉴权、配额、限流、实际模型质量。
- 真实语义embedding下BM25、向量和混合检索的效果比较。
- arXiv线上MCP检索与服务可用性。
- 可选sentence-transformers本地模型下载和推理。
- Docker构建及Linux CI运行结果，不能用Windows本地通过代替。
- 实验室真实语料、用户使用情况、长时间运行和性能指标。

首版为小规模、本机单用户服务。`asyncio.timeout`无法强制终止线程内正在执行的同步计算：embedding批量设总预算并为请求使用剩余超时，但在途HTTP/CPU工作可能在客户端收到超时后短暂继续；不是硬实时取消系统。
