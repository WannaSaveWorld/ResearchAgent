import asyncio
from researchagent.models import Answer, Chunk, Hit
from researchagent.workflow import ResearchWorkflow


class Retriever:
    def __init__(self, hits):
        self.hits = hits
    def search(self, question, k=6, mode='hybrid'):
        return self.hits


class Engine:
    async def answer(self, question, hits):
        return Answer(answer='Grounded answer.', citations=[hits[0].chunk], evidence_count=len(hits))


class Tool:
    calls = 0
    async def search(self, question):
        self.calls += 1
        return [{'title': 'Paper', 'url': 'https://example.org/paper', 'text': 'External evidence'}]


def hit():
    return Hit(chunk=Chunk(id='c', document_id='d', filename='p.pdf', page=1,
                          section='Methods', text='saliency fusion'), score=1)


async def test_local_and_no_evidence_refusal():
    tool = Tool()
    w = ResearchWorkflow(Retriever([hit()]), Engine(), tool=tool)
    assert (await w.ask('what', external=False)).evidence_count == 1
    assert tool.calls == 0
    empty = await ResearchWorkflow(Retriever([]), Engine()).ask('what')
    assert empty.refused and not empty.citations


async def test_external_opt_in_and_tool_failure():
    tool = Tool()
    out = await ResearchWorkflow(Retriever([]), Engine(), tool=tool).ask('what', external=True)
    assert tool.calls == 1
    assert out.citations[0].url == 'https://example.org/paper'
    assert out.citations[0].page is None
    class SlowTool:
        async def search(self, q):
            await asyncio.sleep(1)
    out = await ResearchWorkflow(Retriever([]), Engine(), tool=SlowTool(),
                                 timeout=0.01).ask('what', external=True)
    assert out.refused and out.warnings


async def test_unknown_citations_rejected():
    class BadEngine:
        async def answer(self, q, hits):
            c = hit().chunk.model_copy(update={'id': 'invented'})
            return Answer(answer='wrong', citations=[c])
    out = await ResearchWorkflow(Retriever([hit()]), BadEngine()).ask('what')
    assert out.refused and not out.citations
