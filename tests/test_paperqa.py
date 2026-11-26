import json
from lmi import LLMModel, LLMResult
from paperqa.utils import get_citation_ids
from researchagent.config import Settings
from researchagent.models import Chunk, Hit
from researchagent.paperqa_engine import PaperQAEngine


class ScriptedLLM(LLMModel):
    """Real PaperQA pipeline with an explicit offline LLM test double."""
    calls: list[str] = []
    hallucinate: bool = False

    async def call_single(self, messages, **kwargs):
        text = '\n'.join(str(m.content) for m in messages)
        self.calls.append(text)
        if kwargs.get('name') == 'answer':
            ids = sorted(get_citation_ids(text) - {'pqac-0f650d59'})
            citation = 'pqac-00000000' if self.hallucinate else ids[0]
            output = f'Thermal evidence supports fusion ({citation}).'
        else:
            output = json.dumps({'summary': 'Thermal modality provides complementary evidence for saliency '
                                 'detection in low light, and the experiment evaluates the fusion method.',
                                 'relevance_score': 9})
        return LLMResult(text=output, model='test', prompt_count=0, completion_count=0)


async def test_real_paperqa_uses_selected_evidence_and_maps_citation(tmp_path):
    llm = ScriptedLLM(name='test')
    engine = PaperQAEngine(Settings(data_dir=tmp_path), llm=llm)
    c = Chunk(id='abc', document_id='doc', filename='study.pdf', page=3,
              section='Methods', text='Thermal modality provides complementary information in low light.')
    out = await engine.answer('What does thermal contribute?', [Hit(chunk=c, score=1)])
    assert not out.refused
    assert out.citations[0].id == 'abc' and out.citations[0].page == 3
    assert any(c.text in prompt for prompt in llm.calls)
    assert len(llm.calls) >= 2  # PaperQA summary and answer both executed.


async def test_hallucinated_citation_refused(tmp_path):
    engine = PaperQAEngine(Settings(data_dir=tmp_path), llm=ScriptedLLM(name='test', hallucinate=True))
    c = Chunk(id='abc', document_id='doc', filename='s.pdf', page=1, text='Relevant evidence.')
    out = await engine.answer('Question', [Hit(chunk=c, score=1)])
    assert out.refused and not out.citations
