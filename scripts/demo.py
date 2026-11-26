"""Create original, synthetic PDFs for a reproducible local smoke test."""
import json
from io import BytesIO
from reportlab.pdfgen.canvas import Canvas
from researchagent.config import Settings
from researchagent.store import Store

PAPERS = {
 'thermal_fusion.pdf': [
  ('1 Introduction', 'Thermal infrared provides complementary information in low light. RGB describes appearance.'),
  ('2 Methods', 'Cross-modal fusion combines RGB thermal infrared and depth features for saliency prediction.')],
 'cache_systems.pdf': [
  ('1 Introduction', 'Redis stores short link mappings. A Bloom filter rejects definitely absent link identifiers.'),
  ('2 Methods', 'A mutex and a second cache lookup prevent concurrent rebuilds. Stream consumers process statistics.')],
 'path_planning.pdf': [
  ('1 Introduction', 'A star search plans routes on a grid. RRT explores a continuous configuration space.'),
  ('2 Methods', 'Collision checks reject obstacle intersections. Gazebo simulates navigation with height constraints.')],
 'document_retrieval.pdf': [
  ('1 Introduction', 'BM25 retrieves keyword matches. Dense embeddings retrieve semantically related passages.'),
  ('2 Methods', 'Reciprocal rank fusion combines rankings. Citation metadata links evidence to original PDF pages.')],
 'image_quality.pdf': [
  ('1 Introduction', 'Gaussian filtering smooths image noise. Median filtering can remove salt and pepper noise.'),
  ('2 Methods', 'Canny extracts thin edges. Laplacian variance is a focus indicator but noise also changes it.')],
}
QUESTIONS = [
 ('What does thermal infrared contribute in low light?', 'thermal_fusion.pdf'),
 ('Which modalities are combined for saliency prediction?', 'thermal_fusion.pdf'),
 ('How does a Bloom filter support short links?', 'cache_systems.pdf'),
 ('How are concurrent cache rebuilds controlled?', 'cache_systems.pdf'),
 ('How are obstacle collisions checked in navigation?', 'path_planning.pdf'),
 ('What does Gazebo simulate?', 'path_planning.pdf'),
 ('How do BM25 and embeddings retrieve passages?', 'document_retrieval.pdf'),
 ('How are citations connected to original PDF pages?', 'document_retrieval.pdf'),
 ('Which filter removes salt and pepper noise?', 'image_quality.pdf'),
 ('Why is Laplacian variance affected by noise?', 'image_quality.pdf'),
]


def main():
    store = Store(Settings())
    for name, pages in PAPERS.items():
        stream = BytesIO()
        canvas = Canvas(stream, invariant=True)
        for heading, text in pages:
            canvas.drawString(45, 760, heading)
            # Small original fixtures; not actual published research papers.
            for i in range(0, len(text), 82):
                canvas.drawString(45, 725-(i//82)*18, text[i:i+82])
            canvas.showPage()
        canvas.save()
        doc = store.add_pdf(stream.getvalue(), name)
        print(f'{name}: {doc.pages} pages, {doc.chunks} chunks')
    target = store.root/'demo_questions.json'
    target.write_text(json.dumps([{'question': q, 'relevant_files': [f]} for q, f in QUESTIONS],
                                 ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Question set: {target}')


if __name__ == '__main__':
    main()
