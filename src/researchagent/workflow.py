import asyncio
import hashlib
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from researchagent.models import Answer, Chunk, Hit


class State(TypedDict, total=False):
    question: str
    external: bool
    hits: list[Hit]
    tool_calls: int
    warnings: list[str]
    answer: Answer


class ResearchWorkflow:
    def __init__(self, retriever, engine, tool=None, timeout=90, top_k=6,
                 max_tool_calls=1, recursion_limit=12):
        self.retriever, self.engine, self.tool = retriever, engine, tool
        self.timeout, self.top_k = timeout, top_k
        self.max_tool_calls, self.recursion_limit = max_tool_calls, recursion_limit
        graph = StateGraph(State)
        graph.add_node('retrieve', self._retrieve)
        graph.add_node('external_search', self._external)
        graph.add_node('answer', self._answer)
        graph.add_edge(START, 'retrieve')
        graph.add_conditional_edges('retrieve', lambda s: 'external_search'
            if s['external'] and not s['hits'] and self.max_tool_calls > 0 else 'answer')
        graph.add_edge('external_search', 'answer')
        graph.add_edge('answer', END)
        self.graph = graph.compile()

    async def _retrieve(self, state):
        hits = await asyncio.to_thread(self.retriever.search, state['question'], self.top_k)
        return {'hits': hits}

    async def _external(self, state):
        try:
            if self.tool is None:
                raise RuntimeError('External tool is not configured')
            async with asyncio.timeout(self.timeout):
                rows = await self.tool.search(state['question'])
            hits = []
            for row in rows[:self.top_k]:
                key = hashlib.sha256((row['url']+row['text']).encode()).hexdigest()[:24]
                c = Chunk(id=key, document_id='external:'+key, filename=row['title'],
                          page=None, text=row['text'], url=row['url'])
                hits.append(Hit(chunk=c, score=1))
            return {'hits': hits, 'tool_calls': 1}
        except Exception:
            return {'warnings': ['外部检索失败或超时，请检查 MCP 配置。'], 'tool_calls': 1}

    async def _answer(self, state):
        hits = state['hits']
        if not hits:
            return {'answer': Answer(answer='未找到足够的文献证据，请上传相关论文或调整问题。',
                                     refused=True, warnings=state['warnings'])}
        async with asyncio.timeout(self.timeout):
            answer = await self.engine.answer(state['question'], hits)
        allowed = {h.chunk.id: h.chunk for h in hits}
        # Replace all returned metadata with the original parser-owned metadata.
        if any(c.id not in allowed for c in answer.citations) or (not answer.citations and not answer.refused):
            answer = Answer(answer='回答引用未通过校验，请调整问题或检查文献证据。', refused=True)
        else:
            answer.citations = [allowed[c.id] for c in answer.citations]
        answer.warnings.extend(state['warnings'])
        return {'answer': answer}

    async def ask(self, question, external=False):
        result = await self.graph.ainvoke(
            State(question=question, external=external, hits=[], warnings=[], tool_calls=0),
            config={'recursion_limit': self.recursion_limit})
        return result['answer']
