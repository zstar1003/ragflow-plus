"""Execute production retrieval with deterministic search/model boundaries.

No Elasticsearch or embedding service is required. Total remains the number
passing the threshold in the current candidate window, not a global count.
"""
import ast
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
node = next(n for n in ast.parse((ROOT / 'rag/nlp/search.py').read_text()).body
            if isinstance(n, ast.ClassDef) and n.name == 'Dealer')
method = next(n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == 'retrieval')
ns = {'np': np, 'math': math, 'PAGERANK_FLD': 'pagerank',
      'index_name': lambda tid: f'ragflow_{tid}', 'rmSpace': lambda s: s}
exec(compile(ast.Module(body=[method], type_ignores=[]), 'search.py', 'exec'), ns)


class PaginationTests(unittest.TestCase):
    def retrieve(self, page, size, count=145, scores=None, **kwargs):
        self.dealer = Mock()
        def search(req, indices, kb_ids, *args, **kw):
            offset = (req['page'] - 1) * req['size']
            ids = list(range(offset, min(offset + req['size'], count)))
            return SimpleNamespace(total=count, ids=ids, query_vector=[1.0],
                highlight={i: f'highlight-{i}' for i in ids},
                field={i: {'content_ltks': str(i), 'content_with_weight': str(i),
                           'kb_id': 'kb', 'doc_id': 'doc', 'docnm_kwd': 'document'} for i in ids})
        def rerank(sres, *args, **kw):
            sim = np.array([scores(i) if scores else 1 - i / 10000 for i in sres.ids])
            return sim, sim * 0.5, sim * 0.75
        self.dealer.search.side_effect = search
        self.dealer.rerank.side_effect = rerank
        self.dealer.rerank_by_model.side_effect = lambda mdl, sres, *a, **kw: rerank(sres)
        return ns['retrieval'](self.dealer, 'question', object(), 'tenant-a,tenant-b',
                               ['kb'], page, size, **kwargs)

    def test_all_pages_across_windows_and_partial_tail(self):
        for size in (1, 10, 12, 30, 64, 65, 128, 129):
            collected = []
            for page in range(1, math.ceil(145 / size) + 2):
                result = self.retrieve(page, size)
                actual = [c['chunk_id'] for c in result['chunks']]
                self.assertEqual(actual, list(range((page - 1) * size, min(page * size, 145))), (page, size))
                collected += actual
            self.assertEqual(collected, list(range(145)))

    def test_page_seven_uses_second_window_and_forwards_filters(self):
        result = self.retrieve(7, 10, highlight=True)
        self.assertEqual([c['chunk_id'] for c in result['chunks']], list(range(60, 70)))
        req, indices, kb_ids = self.dealer.search.call_args.args[:3]
        self.assertEqual((req['page'], req['size']), (2, 60))
        self.assertEqual((req['available_int'], req['kb_ids']), (1, ['kb']))
        self.assertEqual(indices, ['ragflow_tenant-a', 'ragflow_tenant-b'])
        self.assertEqual(result['chunks'][0]['highlight'], 'highlight-60')
        self.assertEqual(result['doc_aggs'], [{'doc_name': 'document', 'doc_id': 'doc', 'count': 10}])

    def test_model_reranks_within_window_and_preserves_scores(self):
        result = self.retrieve(7, 10, scores=lambda i: i / 1000, similarity_threshold=0,
                               rerank_mdl=object())
        self.assertEqual([c['chunk_id'] for c in result['chunks']], list(range(119, 109, -1)))
        self.dealer.rerank.assert_not_called()
        self.dealer.rerank_by_model.assert_called_once()
        self.assertAlmostEqual(result['chunks'][0]['similarity'], 0.119)
        self.assertAlmostEqual(result['chunks'][0]['term_similarity'], 0.0595)

    def test_threshold_and_total_are_window_local(self):
        for page, expected in ((7, list(range(60, 65))), (8, [])):
            result = self.retrieve(page, 10, scores=lambda i: 0.8 if i < 65 else 0.1)
            self.assertEqual([c['chunk_id'] for c in result['chunks']], expected)
            self.assertEqual(result['total'], 5)

    def test_document_filter_keeps_existing_threshold_and_cap(self):
        result = self.retrieve(7, 10, scores=lambda i: 0.1, doc_ids=['doc'])
        self.assertEqual(len(result['chunks']), 10)
        self.assertEqual(result['total'], 60)
        self.assertEqual(self.dealer.search.call_args.args[0]['doc_ids'], ['doc'])
        result = self.retrieve(2, 65, doc_ids=['doc'])
        self.assertEqual([c['chunk_id'] for c in result['chunks']], list(range(65, 95)))

    def test_empty_window_and_empty_question(self):
        self.assertEqual(self.retrieve(7, 10, count=60)['chunks'], [])
        self.assertEqual(self.retrieve(1, 10, count=0)['total'], 0)
        dealer = Mock()
        self.assertEqual(ns['retrieval'](dealer, '', None, [], [], 1, 10)['total'], 0)
        dealer.search.assert_not_called()


if __name__ == '__main__':
    unittest.main()
