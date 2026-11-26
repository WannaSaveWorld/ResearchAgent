"""Document-level Recall@k and MRR on a supplied labelled question set."""
import argparse
import json
from pathlib import Path
from researchagent.config import Settings
from researchagent.embeddings import make_embedding
from researchagent.retrieval import HybridRetriever
from researchagent.store import Store


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--questions', type=Path)
    p.add_argument('--modes', nargs='+', choices=['bm25', 'vector', 'hybrid'], default=['bm25'])
    p.add_argument('--k', type=int, default=3)
    p.add_argument('--output', type=Path, default=Path('data/evaluation.json'))
    args = p.parse_args()
    if args.k < 1:
        p.error('k must be positive')
    settings = Settings()
    store = Store(settings)
    questions_path = args.questions or store.root/'demo_questions.json'
    questions = json.loads(questions_path.read_text('utf-8'))
    if not questions or any(not q.get('relevant_files') for q in questions):
        raise ValueError('Provide nonempty questions and relevant_files labels')
    provider = make_embedding(settings) if set(args.modes) != {'bm25'} else None
    r = HybridRetriever(store.chunks(), provider, store.root/'index')
    available = {d.filename for d in store.documents()}
    if any(not set(q['relevant_files']) <= available for q in questions):
        raise ValueError('A labelled relevant file is missing from the corpus')
    report = {'questions': len(questions), 'documents': len(store.documents()),
              'chunks': len(store.chunks()), 'k': args.k,
              'embedding_model': provider.model_id if provider else None,
              'scope': 'document-level retrieval; synthetic demo is not a real-world quality benchmark',
              'results': {}}
    for mode in args.modes:
        recalls, reciprocal_ranks = [], []
        for item in questions:
            # Retrieve all chunks, then deduplicate documents before top-k.
            ranked = []
            for hit in r.search(item['question'], k=min(100, max(1, len(store.chunks()))), mode=mode):
                if hit.chunk.filename not in ranked:
                    ranked.append(hit.chunk.filename)
            selected = ranked[:args.k]
            relevant = set(item['relevant_files'])
            recalls.append(len(relevant & set(selected))/len(relevant))
            reciprocal_ranks.append(next((1/i for i, name in enumerate(selected, 1)
                                          if name in relevant), 0))
        report['results'][mode] = {f'recall@{args.k}': sum(recalls)/len(recalls),
                                   f'mrr@{args.k}': sum(reciprocal_ranks)/len(reciprocal_ranks)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
