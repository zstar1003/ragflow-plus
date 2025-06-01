#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import logging
import re
import math
from dataclasses import dataclass

from rag.settings import TAG_FLD, PAGERANK_FLD
from rag.utils import rmSpace
from rag.nlp import rag_tokenizer, query
import numpy as np
from rag.utils.doc_store_conn import DocStoreConnection, MatchDenseExpr, FusionExpr, OrderByExpr


def index_name(uid):
    return f"ragflow_{uid}"


class Dealer:
    def __init__(self, dataStore: DocStoreConnection):
        self.qryr = query.FulltextQueryer()
        self.dataStore = dataStore

    @dataclass
    class SearchResult:
        total: int
        ids: list[str]
        query_vector: list[float] | None = None
        field: dict | None = None
        highlight: dict | None = None
        aggregation: list | dict | None = None
        keywords: list[str] | None = None
        group_docs: list[list] | None = None

    def get_vector(self, txt, emb_mdl, topk=10, similarity=0.1):
        qv, _ = emb_mdl.encode_queries(txt)
        shape = np.array(qv).shape
        if len(shape) > 1:
            raise Exception(f"Dealer.get_vector returned array's shape {shape} doesn't match expectation(exact one dimension).")
        embedding_data = [float(v) for v in qv]
        vector_column_name = f"q_{len(embedding_data)}_vec"
        return MatchDenseExpr(vector_column_name, embedding_data, "float", "cosine", topk, {"similarity": similarity})

    def get_filters(self, req):
        condition = dict()
        for key, field in {"kb_ids": "kb_id", "doc_ids": "doc_id"}.items():
            if key in req and req[key] is not None:
                condition[field] = req[key]
        # TODO(yzc): `available_int` is nullable however infinity doesn't support nullable columns.
        for key in ["knowledge_graph_kwd", "available_int", "entity_kwd", "from_entity_kwd", "to_entity_kwd", "removed_kwd"]:
            if key in req and req[key] is not None:
                condition[key] = req[key]
        return condition

    def search(self, req, idx_names: str | list[str], kb_ids: list[str], emb_mdl=None, highlight=False, rank_feature: dict | None = None):
        """
        执行混合检索（全文检索+向量检索）

        参数:
            req: 请求参数字典，包含：
                - page: 页码
                - topk: 返回结果最大数量
                - size: 每页大小
                - fields: 指定返回字段
                - question: 查询问题文本
                - similarity: 向量相似度阈值
            idx_names: 索引名称或列表
            kb_ids: 知识库ID列表
            emb_mdl: 嵌入模型，用于向量检索
            highlight: 是否返回高亮内容
            rank_feature: 排序特征配置

        返回:
            SearchResult对象，包含：
                - total: 匹配总数
                - ids: 匹配的chunk ID列表
                - query_vector: 查询向量
                - field: 各chunk的字段值
                - highlight: 高亮内容
                - aggregation: 聚合结果
                - keywords: 提取的关键词
        """
        # 1. 初始化过滤条件和排序规则
        filters = self.get_filters(req)
        orderBy = OrderByExpr()

        # 2. 处理分页参数
        pg = int(req.get("page", 1)) - 1
        topk = int(req.get("topk", 1024))
        ps = int(req.get("size", topk))
        offset, limit = pg * ps, ps

        # 3. 设置返回字段（默认包含文档名、内容等核心字段）
        src = req.get(
            "fields",
            [
                "docnm_kwd",
                "content_ltks",
                "kb_id",
                "img_id",
                "title_tks",
                "important_kwd",
                "position_int",
                "doc_id",
                "page_num_int",
                "top_int",
                "create_timestamp_flt",
                "knowledge_graph_kwd",
                "question_kwd",
                "question_tks",
                "available_int",
                "content_with_weight",
                PAGERANK_FLD,
                TAG_FLD,
            ],
        )
        kwds = set([])  # 初始化关键词集合

        # 4. 处理查询问题
        qst = req.get("question", "")  # 获取查询问题文本
        print(f"收到前端问题：{qst}")
        q_vec = []  # 初始化查询向量（如需向量检索）
        if not qst:
            # 4.1 若查询文本为空，执行默认排序检索（通常用于无搜索条件浏览）(注：前端测试检索时会禁止空文本的提交)
            if req.get("sort"):
                orderBy.asc("page_num_int")
                orderBy.asc("top_int")
                orderBy.desc("create_timestamp_flt")
            res = self.dataStore.search(src, [], filters, [], orderBy, offset, limit, idx_names, kb_ids)
            total = self.dataStore.getTotal(res)
            logging.debug("Dealer.search TOTAL: {}".format(total))
        else:
            # 4.2 若存在查询文本，进入全文/混合检索流程
            highlightFields = ["content_ltks", "title_tks"] if highlight else []  # highlight当前会一直为False，不起作用
            # 4.2.1 生成全文检索表达式和关键词
            matchText, keywords = self.qryr.question(qst, min_match=0.3)
            print(f"matchText.matching_text: {matchText.matching_text}")
            print(f"keywords: {keywords}\n")
            if emb_mdl is None:
                # 4.2.2 纯全文检索模式 （未提供向量模型，正常情况不会进入）
                matchExprs = [matchText]
                res = self.dataStore.search(src, highlightFields, filters, matchExprs, orderBy, offset, limit, idx_names, kb_ids, rank_feature=rank_feature)
                total = self.dataStore.getTotal(res)
                logging.debug("Dealer.search TOTAL: {}".format(total))
            else:
                # 4.2.3 混合检索模式（全文+向量）
                # 生成查询向量
                matchDense = self.get_vector(qst, emb_mdl, topk, req.get("similarity", 0.1))
                q_vec = matchDense.embedding_data
                # 在返回字段中加入查询向量字段
                src.append(f"q_{len(q_vec)}_vec")
                # 创建融合表达式：设置向量匹配为95%，全文为5%
                fusionExpr = FusionExpr("weighted_sum", topk, {"weights": "0.05, 0.95"})
                # 构建混合查询表达式
                matchExprs = [matchText, matchDense, fusionExpr]

                # 执行混合检索
                res = self.dataStore.search(src, highlightFields, filters, matchExprs, orderBy, offset, limit, idx_names, kb_ids, rank_feature=rank_feature)
                total = self.dataStore.getTotal(res)
                logging.debug("Dealer.search TOTAL: {}".format(total))

                print(f"共查询到: {total} 条信息")
                # print(f"查询信息结果: {res}\n")

                # 若未找到结果，则尝试降低匹配门槛后重试
                if total == 0:
                    if filters.get("doc_id"):
                        # 有特定文档ID时执行无条件查询
                        res = self.dataStore.search(src, [], filters, [], orderBy, offset, limit, idx_names, kb_ids)
                        total = self.dataStore.getTotal(res)
                        print(f"针对选中文档，共查询到: {total} 条信息")
                        # print(f"查询信息结果: {res}\n")
                    else:
                        # 否则调整全文和向量匹配参数再次搜索
                        matchText, _ = self.qryr.question(qst, min_match=0.1)
                        filters.pop("doc_id", None)
                        matchDense.extra_options["similarity"] = 0.17
                        res = self.dataStore.search(src, highlightFields, filters, [matchText, matchDense, fusionExpr], orderBy, offset, limit, idx_names, kb_ids, rank_feature=rank_feature)
                        total = self.dataStore.getTotal(res)
                        logging.debug("Dealer.search 2 TOTAL: {}".format(total))
                        print(f"再次查询，共查询到: {total} 条信息")
                        # print(f"查询信息结果: {res}\n")

            # 4.3 处理关键词（对关键词进行更细粒度的切词）
            for k in keywords:
                kwds.add(k)
                for kk in rag_tokenizer.fine_grained_tokenize(k).split():
                    if len(kk) < 2:
                        continue
                    if kk in kwds:
                        continue
                    kwds.add(kk)

        # 5. 提取检索结果中的ID、字段、聚合和高亮信息
        logging.debug(f"TOTAL: {total}")
        ids = self.dataStore.getChunkIds(res)  # 提取匹配chunk的ID
        keywords = list(kwds)  # 转为列表格式返回
        highlight = self.dataStore.getHighlight(res, keywords, "content_with_weight")  # 获取高亮内容
        aggs = self.dataStore.getAggregation(res, "docnm_kwd")  # 执行基于文档名的聚合分析
        return self.SearchResult(total=total, ids=ids, query_vector=q_vec, aggregation=aggs, highlight=highlight, field=self.dataStore.getFields(res, src), keywords=keywords)

    @staticmethod
    def trans2floats(txt):
        return [float(t) for t in txt.split("\t")]

    def insert_citations(self, answer, chunks, chunk_v, embd_mdl, tkweight=0.1, vtweight=0.9):
        assert len(chunks) == len(chunk_v)
        if not chunks:
            return answer, set([])
        pieces = re.split(r"(```)", answer)
        if len(pieces) >= 3:
            i = 0
            pieces_ = []
            while i < len(pieces):
                if pieces[i] == "```":
                    st = i
                    i += 1
                    while i < len(pieces) and pieces[i] != "```":
                        i += 1
                    if i < len(pieces):
                        i += 1
                    pieces_.append("".join(pieces[st:i]) + "\n")
                else:
                    pieces_.extend(re.split(r"([^\|][；。？!！\n]|[a-z][.?;!][ \n])", pieces[i]))
                    i += 1
            pieces = pieces_
        else:
            pieces = re.split(r"([^\|][；。？!！\n]|[a-z][.?;!][ \n])", answer)
        for i in range(1, len(pieces)):
            if re.match(r"([^\|][；。？!！\n]|[a-z][.?;!][ \n])", pieces[i]):
                pieces[i - 1] += pieces[i][0]
                pieces[i] = pieces[i][1:]
        idx = []
        pieces_ = []
        for i, t in enumerate(pieces):
            if len(t) < 5:
                continue
            idx.append(i)
            pieces_.append(t)
        logging.debug("{} => {}".format(answer, pieces_))
        if not pieces_:
            return answer, set([])

        ans_v, _ = embd_mdl.encode(pieces_)
        for i in range(len(chunk_v)):
            if len(ans_v[0]) != len(chunk_v[i]):
                chunk_v[i] = [0.0] * len(ans_v[0])
                logging.warning("The dimension of query and chunk do not match: {} vs. {}".format(len(ans_v[0]), len(chunk_v[i])))

        assert len(ans_v[0]) == len(chunk_v[0]), "The dimension of query and chunk do not match: {} vs. {}".format(len(ans_v[0]), len(chunk_v[0]))

        chunks_tks = [rag_tokenizer.tokenize(self.qryr.rmWWW(ck)).split() for ck in chunks]
        cites = {}
        thr = 0.63
        while thr > 0.3 and len(cites.keys()) == 0 and pieces_ and chunks_tks:
            for i, a in enumerate(pieces_):
                sim, tksim, vtsim = self.qryr.hybrid_similarity(ans_v[i], chunk_v, rag_tokenizer.tokenize(self.qryr.rmWWW(pieces_[i])).split(), chunks_tks, tkweight, vtweight)
                mx = np.max(sim) * 0.99
                logging.debug("{} SIM: {}".format(pieces_[i], mx))
                if mx < thr:
                    continue
                cites[idx[i]] = list(set([str(ii) for ii in range(len(chunk_v)) if sim[ii] > mx]))[:4]
            thr *= 0.8

        res = ""
        seted = set([])
        for i, p in enumerate(pieces):
            res += p
            if i not in idx:
                continue
            if i not in cites:
                continue
            for c in cites[i]:
                assert int(c) < len(chunk_v)
            for c in cites[i]:
                if c in seted:
                    continue
                res += f" ##{c}$$"
                seted.add(c)

        return res, seted

    def _rank_feature_scores(self, query_rfea, search_res):
        ## For rank feature(tag_fea) scores.
        rank_fea = []
        pageranks = []
        for chunk_id in search_res.ids:
            pageranks.append(search_res.field[chunk_id].get(PAGERANK_FLD, 0))
        pageranks = np.array(pageranks, dtype=float)

        if not query_rfea:
            return np.array([0 for _ in range(len(search_res.ids))]) + pageranks

        q_denor = np.sqrt(np.sum([s * s for t, s in query_rfea.items() if t != PAGERANK_FLD]))
        for i in search_res.ids:
            nor, denor = 0, 0
            for t, sc in eval(search_res.field[i].get(TAG_FLD, "{}")).items():
                if t in query_rfea:
                    nor += query_rfea[t] * sc
                denor += sc * sc
            if denor == 0:
                rank_fea.append(0)
            else:
                rank_fea.append(nor / np.sqrt(denor) / q_denor)
        return np.array(rank_fea) * 10.0 + pageranks

    def rerank(self, sres, query, tkweight=0.3, vtweight=0.7, cfield="content_ltks", rank_feature: dict | None = None):
        """
        对初步检索到的结果 (sres) 进行重排序。

        该方法结合了多种相似度/特征来计算每个结果的新排序分数：
        1. 文本相似度 (Token Similarity): 基于查询关键词与文档内容的词元匹配。
        2. 向量相似度 (Vector Similarity): 基于查询向量与文档向量的余弦相似度。
        3. 排序特征分数 (Rank Feature Scores): 如文档的 PageRank 值或与查询相关的标签特征得分。

        最终的排序分数是这几种分数的加权组合（或直接相加）。

        Args:
            sres (SearchResult): 初步检索的结果对象，包含查询向量、文档ID、字段内容等。
            query (str): 原始用户查询字符串。
            tkweight (float): 文本相似度在混合相似度计算中的权重。
            vtweight (float): 向量相似度在混合相似度计算中的权重。
            cfield (str): 用于提取主要文本内容以进行词元匹配的字段名，默认为 "content_ltks"。
            rank_feature (dict | None): 用于计算排序特征分数的查询侧特征，
                                        例如 {PAGERANK_FLD: 10} 表示 PageRank 权重，
                                        或包含其他标签及其权重的字典。

        Returns:
            tuple[np.ndarray, np.ndarray, np.ndarray]:
                - sim (np.ndarray): 每个文档的最终重排序分数 (混合相似度 + 排序特征分数)。
                - tksim (np.ndarray): 每个文档的纯文本相似度分数。
                - vtsim (np.ndarray): 每个文档的纯向量相似度分数。
                如果初步检索结果为空 (sres.ids is empty)，则返回三个空列表。
        """
        _, keywords = self.qryr.question(query)
        vector_size = len(sres.query_vector)
        vector_column = f"q_{vector_size}_vec"
        zero_vector = [0.0] * vector_size
        ins_embd = []
        for chunk_id in sres.ids:
            vector = sres.field[chunk_id].get(vector_column, zero_vector)
            if isinstance(vector, str):
                vector = [float(v) for v in vector.split("\t")]
            ins_embd.append(vector)
        if not ins_embd:
            return [], [], []

        for i in sres.ids:
            if isinstance(sres.field[i].get("important_kwd", []), str):
                sres.field[i]["important_kwd"] = [sres.field[i]["important_kwd"]]
        ins_tw = []
        for i in sres.ids:
            content_ltks = sres.field[i][cfield].split()
            title_tks = [t for t in sres.field[i].get("title_tks", "").split() if t]
            question_tks = [t for t in sres.field[i].get("question_tks", "").split() if t]
            important_kwd = sres.field[i].get("important_kwd", [])
            tks = content_ltks + title_tks * 2 + important_kwd * 5 + question_tks * 6
            ins_tw.append(tks)

        ## For rank feature(tag_fea) scores.
        rank_fea = self._rank_feature_scores(rank_feature, sres)

        sim, tksim, vtsim = self.qryr.hybrid_similarity(sres.query_vector, ins_embd, keywords, ins_tw, tkweight, vtweight)

        return sim + rank_fea, tksim, vtsim

    def rerank_by_model(self, rerank_mdl, sres, query, tkweight=0.3, vtweight=0.7, cfield="content_ltks", rank_feature: dict | None = None):
        _, keywords = self.qryr.question(query)

        for i in sres.ids:
            if isinstance(sres.field[i].get("important_kwd", []), str):
                sres.field[i]["important_kwd"] = [sres.field[i]["important_kwd"]]
        ins_tw = []
        for i in sres.ids:
            content_ltks = sres.field[i][cfield].split()
            title_tks = [t for t in sres.field[i].get("title_tks", "").split() if t]
            important_kwd = sres.field[i].get("important_kwd", [])
            tks = content_ltks + title_tks + important_kwd
            ins_tw.append(tks)

        tksim = self.qryr.token_similarity(keywords, ins_tw)
        vtsim, _ = rerank_mdl.similarity(query, [rmSpace(" ".join(tks)) for tks in ins_tw])
        ## For rank feature(tag_fea) scores.
        rank_fea = self._rank_feature_scores(rank_feature, sres)

        return tkweight * (np.array(tksim) + rank_fea) + vtweight * vtsim, tksim, vtsim

    def hybrid_similarity(self, ans_embd, ins_embd, ans, inst):
        return self.qryr.hybrid_similarity(ans_embd, ins_embd, rag_tokenizer.tokenize(ans).split(), rag_tokenizer.tokenize(inst).split())

    def retrieval(
        self,
        question,
        embd_mdl,
        tenant_ids,
        kb_ids,
        page,
        page_size,
        similarity_threshold=0.2,
        vector_similarity_weight=0.3,
        top=1024,
        doc_ids=None,
        aggs=True,
        rerank_mdl=None,
        highlight=False,
        rank_feature: dict | None = {PAGERANK_FLD: 10},
    ):
        """
        执行检索操作，根据问题查询相关文档片段

        参数说明:
        - question: 用户输入的查询问题
        - embd_mdl: 嵌入模型，用于将文本转换为向量
        - tenant_ids: 租户ID，可以是字符串或列表
        - kb_ids: 知识库ID列表
        - page: 当前页码
        - page_size: 每页结果数量
        - similarity_threshold: 相似度阈值，低于此值的结果将被过滤
        - vector_similarity_weight: 向量相似度权重
        - top: 检索的最大结果数
        - doc_ids: 文档ID列表，用于限制检索范围
        - aggs: 是否聚合文档信息
        - rerank_mdl: 重排序模型
        - highlight: 是否高亮匹配内容
        - rank_feature: 排序特征，如PageRank值

        返回:
        包含检索结果的字典，包括总数、文档片段和文档聚合信息
        """
        # 初始化结果字典
        ranks = {"total": 0, "chunks": [], "doc_aggs": {}}
        if not question:
            return ranks
        # 设置重排序页面限制
        RERANK_LIMIT = 64
        RERANK_LIMIT = int(RERANK_LIMIT // page_size + ((RERANK_LIMIT % page_size) / (page_size * 1.0) + 0.5)) * page_size if page_size > 1 else 1
        if RERANK_LIMIT < 1:
            RERANK_LIMIT = 1
        # 构建检索请求参数
        req = {
            "kb_ids": kb_ids,
            "doc_ids": doc_ids,
            "page": math.ceil(page_size * page / RERANK_LIMIT),
            "size": RERANK_LIMIT,
            "question": question,
            "vector": True,
            "topk": top,
            "similarity": similarity_threshold,
            "available_int": 1,
        }

        # 处理租户ID格式
        if isinstance(tenant_ids, str):
            tenant_ids = tenant_ids.split(",")

        # 执行搜索操作
        sres = self.search(req, [index_name(tid) for tid in tenant_ids], kb_ids, embd_mdl, highlight, rank_feature=rank_feature)

        # 执行重排序操作
        if rerank_mdl and sres.total > 0:
            sim, tsim, vsim = self.rerank_by_model(rerank_mdl, sres, question, 1 - vector_similarity_weight, vector_similarity_weight, rank_feature=rank_feature)
        else:
            sim, tsim, vsim = self.rerank(sres, question, 1 - vector_similarity_weight, vector_similarity_weight, rank_feature=rank_feature)
        # Already paginated in search function
        idx = np.argsort(sim * -1)[(page - 1) * page_size : page * page_size]

        dim = len(sres.query_vector)
        vector_column = f"q_{dim}_vec"
        zero_vector = [0.0] * dim
        if doc_ids:
            similarity_threshold = 0
            page_size = 30
        sim_np = np.array(sim)
        filtered_count = (sim_np >= similarity_threshold).sum()
        ranks["total"] = int(filtered_count)  # Convert from np.int64 to Python int otherwise JSON serializable error
        for i in idx:
            if sim[i] < similarity_threshold:
                break
            if len(ranks["chunks"]) >= page_size:
                if aggs:
                    continue
                break
            id = sres.ids[i]
            chunk = sres.field[id]
            dnm = chunk.get("docnm_kwd", "")
            did = chunk.get("doc_id", "")
            position_int = chunk.get("position_int", [])
            d = {
                "chunk_id": id,
                "content_ltks": chunk["content_ltks"],
                "content_with_weight": chunk["content_with_weight"],
                "doc_id": did,
                "docnm_kwd": dnm,
                "kb_id": chunk["kb_id"],
                "important_kwd": chunk.get("important_kwd", []),
                "image_id": chunk.get("img_id", ""),
                "similarity": sim[i],
                "vector_similarity": vsim[i],
                "term_similarity": tsim[i],
                "vector": chunk.get(vector_column, zero_vector),
                "positions": position_int,
                "doc_type_kwd": chunk.get("doc_type_kwd", ""),
            }
            if highlight and sres.highlight:
                if id in sres.highlight:
                    d["highlight"] = rmSpace(sres.highlight[id])
                else:
                    d["highlight"] = d["content_with_weight"]
            ranks["chunks"].append(d)
            if dnm not in ranks["doc_aggs"]:
                ranks["doc_aggs"][dnm] = {"doc_id": did, "count": 0}
            ranks["doc_aggs"][dnm]["count"] += 1
        ranks["doc_aggs"] = [{"doc_name": k, "doc_id": v["doc_id"], "count": v["count"]} for k, v in sorted(ranks["doc_aggs"].items(), key=lambda x: x[1]["count"] * -1)]
        ranks["chunks"] = ranks["chunks"][:page_size]

        return ranks

    def sql_retrieval(self, sql, fetch_size=128, format="json"):
        tbl = self.dataStore.sql(sql, fetch_size, format)
        return tbl

    def chunk_list(self, doc_id: str, tenant_id: str, kb_ids: list[str], max_count=1024, offset=0, fields=["docnm_kwd", "content_with_weight", "img_id"]):
        condition = {"doc_id": doc_id}
        res = []
        bs = 128
        for p in range(offset, max_count, bs):
            es_res = self.dataStore.search(fields, [], condition, [], OrderByExpr(), p, bs, index_name(tenant_id), kb_ids)
            dict_chunks = self.dataStore.getFields(es_res, fields)
            for id, doc in dict_chunks.items():
                doc["id"] = id
            if dict_chunks:
                res.extend(dict_chunks.values())
            if len(dict_chunks.values()) < bs:
                break
        return res

    def all_tags(self, tenant_id: str, kb_ids: list[str], S=1000):
        if not self.dataStore.indexExist(index_name(tenant_id), kb_ids[0]):
            return []
        res = self.dataStore.search([], [], {}, [], OrderByExpr(), 0, 0, index_name(tenant_id), kb_ids, ["tag_kwd"])
        return self.dataStore.getAggregation(res, "tag_kwd")

    def all_tags_in_portion(self, tenant_id: str, kb_ids: list[str], S=1000):
        res = self.dataStore.search([], [], {}, [], OrderByExpr(), 0, 0, index_name(tenant_id), kb_ids, ["tag_kwd"])
        res = self.dataStore.getAggregation(res, "tag_kwd")
        total = np.sum([c for _, c in res])
        return {t: (c + 1) / (total + S) for t, c in res}

    def tag_content(self, tenant_id: str, kb_ids: list[str], doc, all_tags, topn_tags=3, keywords_topn=30, S=1000):
        idx_nm = index_name(tenant_id)
        match_txt = self.qryr.paragraph(doc["title_tks"] + " " + doc["content_ltks"], doc.get("important_kwd", []), keywords_topn)
        res = self.dataStore.search([], [], {}, [match_txt], OrderByExpr(), 0, 0, idx_nm, kb_ids, ["tag_kwd"])
        aggs = self.dataStore.getAggregation(res, "tag_kwd")
        if not aggs:
            return False
        cnt = np.sum([c for _, c in aggs])
        tag_fea = sorted([(a, round(0.1 * (c + 1) / (cnt + S) / max(1e-6, all_tags.get(a, 0.0001)))) for a, c in aggs], key=lambda x: x[1] * -1)[:topn_tags]
        doc[TAG_FLD] = {a: c for a, c in tag_fea if c > 0}
        return True

    def tag_query(self, question: str, tenant_ids: str | list[str], kb_ids: list[str], all_tags, topn_tags=3, S=1000):
        if isinstance(tenant_ids, str):
            idx_nms = index_name(tenant_ids)
        else:
            idx_nms = [index_name(tid) for tid in tenant_ids]
        match_txt, _ = self.qryr.question(question, min_match=0.0)
        res = self.dataStore.search([], [], {}, [match_txt], OrderByExpr(), 0, 0, idx_nms, kb_ids, ["tag_kwd"])
        aggs = self.dataStore.getAggregation(res, "tag_kwd")
        if not aggs:
            return {}
        cnt = np.sum([c for _, c in aggs])
        tag_fea = sorted([(a, round(0.1 * (c + 1) / (cnt + S) / max(1e-6, all_tags.get(a, 0.0001)))) for a, c in aggs], key=lambda x: x[1] * -1)[:topn_tags]
        return {a.replace(".", "_"): max(1, c) for a, c in tag_fea}
