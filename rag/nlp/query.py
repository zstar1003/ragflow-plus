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
import json
import re
from rag.utils.doc_store_conn import MatchTextExpr

from rag.nlp import rag_tokenizer, term_weight, synonym


class FulltextQueryer:
    def __init__(self):
        self.tw = term_weight.Dealer()
        self.syn = synonym.Dealer()
        self.query_fields = [
            "title_tks^10",
            "title_sm_tks^5",
            "important_kwd^30",
            "important_tks^20",
            "question_tks^20",
            "content_ltks^2",
            "content_sm_ltks",
        ]

    @staticmethod
    def subSpecialChar(line):
        return re.sub(r"([:\{\}/\[\]\-\*\"\(\)\|\+~\^])", r"\\\1", line).strip()

    @staticmethod
    def isChinese(line):
        arr = re.split(r"[ \t]+", line)
        if len(arr) <= 3:
            return True
        e = 0
        for t in arr:
            if not re.match(r"[a-zA-Z]+$", t):
                e += 1
        return e * 1.0 / len(arr) >= 0.7

    @staticmethod
    def rmWWW(txt):
        """
        移除文本中的WWW(WHAT、WHO、WHERE等疑问词)。

        本函数通过一系列正则表达式模式来识别并替换文本中的疑问词，以简化文本或为后续处理做准备。
        参数:
        - txt: 待处理的文本字符串。

        返回:
        - 处理后的文本字符串，如果所有疑问词都被移除且文本为空，则返回原始文本。
        """
        patts = [
            (
                r"是*(什么样的|哪家|一下|那家|请问|啥样|咋样了|什么时候|何时|何地|何人|是否|是不是|多少|哪里|怎么|哪儿|怎么样|如何|哪些|是啥|啥是|啊|吗|呢|吧|咋|什么|有没有|呀|谁|哪位|哪个)是*",
                "",
            ),
            (r"(^| )(what|who|how|which|where|why)('re|'s)? ", " "),
            (
                r"(^| )('s|'re|is|are|were|was|do|does|did|don't|doesn't|didn't|has|have|be|there|you|me|your|my|mine|just|please|may|i|should|would|wouldn't|will|won't|done|go|for|with|so|the|a|an|by|i'm|it's|he's|she's|they|they're|you're|as|by|on|in|at|up|out|down|of|to|or|and|if) ",
                " ",
            ),
        ]
        otxt = txt
        for r, p in patts:
            txt = re.sub(r, p, txt, flags=re.IGNORECASE)
        if not txt:
            txt = otxt
        return txt

    @staticmethod
    def add_space_between_eng_zh(txt):
        """
        在英文和中文之间添加空格。

        该函数通过正则表达式匹配文本中英文和中文相邻的情况，并在它们之间插入空格。
        这样做可以改善文本的可读性，特别是在混合使用英文和中文时。

        参数:
        txt (str): 需要处理的文本字符串。

        返回:
        str: 处理后的文本字符串，其中英文和中文之间添加了空格。
        """
        # (ENG/ENG+NUM) + ZH
        txt = re.sub(r"([A-Za-z]+[0-9]+)([\u4e00-\u9fa5]+)", r"\1 \2", txt)
        # ENG + ZH
        txt = re.sub(r"([A-Za-z])([\u4e00-\u9fa5]+)", r"\1 \2", txt)
        # ZH + (ENG/ENG+NUM)
        txt = re.sub(r"([\u4e00-\u9fa5]+)([A-Za-z]+[0-9]+)", r"\1 \2", txt)
        txt = re.sub(r"([\u4e00-\u9fa5]+)([A-Za-z])", r"\1 \2", txt)
        return txt

    def question(self, txt, tbl="qa", min_match: float = 0.6):
        """
        根据输入的文本生成查询表达式，用于在数据库中匹配相关问题。

        参数:
        - txt (str): 输入的文本。
        - tbl (str): 数据表名，默认为"qa"。
        - min_match (float): 最小匹配度，默认为0.6。

        返回:
        - MatchTextExpr: 生成的查询表达式对象。
        - keywords (list): 提取的关键词列表。
        """
        txt = FulltextQueryer.add_space_between_eng_zh(txt)  # 在英文和中文之间添加空格
        # 使用正则表达式替换特殊字符为单个空格，并将文本转换为简体中文和小写
        txt = re.sub(
            r"[ :|\r\n\t,，。？?/`!！&^%%()\[\]{}<>]+",
            " ",
            rag_tokenizer.tradi2simp(rag_tokenizer.strQ2B(txt.lower())),
        ).strip()
        otxt = txt
        txt = FulltextQueryer.rmWWW(txt)

        # 如果文本不是中文，则进行英文处理
        if not self.isChinese(txt):
            txt = FulltextQueryer.rmWWW(txt)
            tks = rag_tokenizer.tokenize(txt).split()
            keywords = [t for t in tks if t]
            tks_w = self.tw.weights(tks, preprocess=False)
            tks_w = [(re.sub(r"[ \\\"'^]", "", tk), w) for tk, w in tks_w]
            tks_w = [(re.sub(r"^[a-z0-9]$", "", tk), w) for tk, w in tks_w if tk]
            tks_w = [(re.sub(r"^[\+-]", "", tk), w) for tk, w in tks_w if tk]
            tks_w = [(tk.strip(), w) for tk, w in tks_w if tk.strip()]
            syns = []
            for tk, w in tks_w[:256]:
                syn = self.syn.lookup(tk)
                syn = rag_tokenizer.tokenize(" ".join(syn)).split()
                keywords.extend(syn)
                syn = ['"{}"^{:.4f}'.format(s, w / 4.0) for s in syn if s.strip()]
                syns.append(" ".join(syn))

            q = ["({}^{:.4f}".format(tk, w) + " {})".format(syn) for (tk, w), syn in zip(tks_w, syns) if tk and not re.match(r"[.^+\(\)-]", tk)]
            for i in range(1, len(tks_w)):
                left, right = tks_w[i - 1][0].strip(), tks_w[i][0].strip()
                if not left or not right:
                    continue
                q.append(
                    '"%s %s"^%.4f'
                    % (
                        tks_w[i - 1][0],
                        tks_w[i][0],
                        max(tks_w[i - 1][1], tks_w[i][1]) * 2,
                    )
                )
            if not q:
                q.append(txt)
            query = " ".join(q)
            return MatchTextExpr(self.query_fields, query, 100), keywords

        def need_fine_grained_tokenize(tk):
            """
            判断是否需要对词进行细粒度分词。

            参数:
            - tk (str): 待判断的词。

            返回:
            - bool: 是否需要进行细粒度分词。
            """
            # 长度小于3的词不处理
            if len(tk) < 3:
                return False
            # 匹配特定模式的词不处理（如数字、字母、符号组合）
            if re.match(r"[0-9a-z\.\+#_\*-]+$", tk):
                return False
            return True

        txt = FulltextQueryer.rmWWW(txt)
        qs, keywords = [], []
        # 遍历文本分割后的前256个片段（防止处理过长文本）
        for tt in self.tw.split(txt)[:256]:  # 注：这个split似乎是对英文设计，中文不起作用
            if not tt:
                continue
            # 将当前片段加入关键词列表
            keywords.append(tt)
            # 获取当前片段的权重
            twts = self.tw.weights([tt])
            # 查找同义词
            syns = self.syn.lookup(tt)
            # 如果有同义词且关键词数量未超过32，将同义词加入关键词列表
            if syns and len(keywords) < 32:
                keywords.extend(syns)
            # 调试日志：输出权重信息
            logging.debug(json.dumps(twts, ensure_ascii=False))
            # 初始化查询条件列表
            tms = []
            # 按权重降序排序处理每个token
            for tk, w in sorted(twts, key=lambda x: x[1] * -1):
                # 如果需要细粒度分词，则进行分词处理
                sm = rag_tokenizer.fine_grained_tokenize(tk).split() if need_fine_grained_tokenize(tk) else []
                # 对每个分词结果进行清洗：
                # 1. 去除标点符号和特殊字符
                # 2. 使用subSpecialChar进一步处理
                # 3. 过滤掉长度<=1的词
                sm = [
                    re.sub(
                        r"[ ,\./;'\[\]\\`~!@#$%\^&\*\(\)=\+_<>\?:\"\{\}\|，。；‘’【】、！￥……（）——《》？：“”-]+",
                        "",
                        m,
                    )
                    for m in sm
                ]
                sm = [FulltextQueryer.subSpecialChar(m) for m in sm if len(m) > 1]
                sm = [m for m in sm if len(m) > 1]

                # 如果关键词数量未达上限，添加处理后的token和分词结果
                if len(keywords) < 32:
                    keywords.append(re.sub(r"[ \\\"']+", "", tk))  # 去除转义字符
                    keywords.extend(sm)  # 添加分词结果
                # 获取当前token的同义词并进行处理
                tk_syns = self.syn.lookup(tk)
                tk_syns = [FulltextQueryer.subSpecialChar(s) for s in tk_syns]
                # 添加有效同义词到关键词列表
                if len(keywords) < 32:
                    keywords.extend([s for s in tk_syns if s])
                # 对同义词进行分词处理，并为包含空格的同义词添加引号
                tk_syns = [rag_tokenizer.fine_grained_tokenize(s) for s in tk_syns if s]
                tk_syns = [f'"{s}"' if s.find(" ") > 0 else s for s in tk_syns]

                # 关键词数量达到上限则停止处理
                if len(keywords) >= 32:
                    break

                # 处理当前token用于构建查询条件：
                # 1. 特殊字符处理
                # 2. 为包含空格的token添加引号
                # 3. 如果有同义词，构建OR条件并降低权重
                # 4. 如果有分词结果，添加OR条件
                tk = FulltextQueryer.subSpecialChar(tk)
                if tk.find(" ") > 0:
                    tk = '"%s"' % tk
                if tk_syns:
                    tk = f"({tk} OR (%s)^0.2)" % " ".join(tk_syns)
                if sm:
                    tk = f'{tk} OR "%s" OR ("%s"~2)^0.5' % (" ".join(sm), " ".join(sm))
                if tk.strip():
                    tms.append((tk, w))

            # 将处理后的查询条件按权重组合成字符串
            tms = " ".join([f"({t})^{w}" for t, w in tms])

            # 如果有多个权重项，添加短语搜索条件（提高相邻词匹配的权重）
            if len(twts) > 1:
                tms += ' ("%s"~2)^1.5' % rag_tokenizer.tokenize(tt)

            # 处理同义词的查询条件
            syns = " OR ".join(['"%s"' % rag_tokenizer.tokenize(FulltextQueryer.subSpecialChar(s)) for s in syns])
            # 组合主查询条件和同义词条件
            if syns and tms:
                tms = f"({tms})^5 OR ({syns})^0.7"
            # 将最终查询条件加入列表
            qs.append(tms)

        # 处理所有查询条件
        if qs:
            # 组合所有查询条件为OR关系
            query = " OR ".join([f"({t})" for t in qs if t])
            # 如果查询条件为空，使用原始文本
            if not query:
                query = otxt
            # 返回匹配文本表达式和关键词
            return MatchTextExpr(self.query_fields, query, 100, {"minimum_should_match": min_match}), keywords
        # 如果没有生成查询条件，只返回关键词
        return None, keywords

    def hybrid_similarity(self, avec, bvecs, atks, btkss, tkweight=0.3, vtweight=0.7):
        from sklearn.metrics.pairwise import cosine_similarity as CosineSimilarity
        import numpy as np

        sims = CosineSimilarity([avec], bvecs)
        tksim = self.token_similarity(atks, btkss)
        if np.sum(sims[0]) == 0:
            return np.array(tksim), tksim, sims[0]
        return np.array(sims[0]) * vtweight + np.array(tksim) * tkweight, tksim, sims[0]

    def token_similarity(self, atks, btkss):
        def toDict(tks):
            d = {}
            if isinstance(tks, str):
                tks = tks.split()
            for t, c in self.tw.weights(tks, preprocess=False):
                if t not in d:
                    d[t] = 0
                d[t] += c
            return d

        atks = toDict(atks)
        btkss = [toDict(tks) for tks in btkss]
        return [self.similarity(atks, btks) for btks in btkss]

    def similarity(self, qtwt, dtwt):
        if isinstance(dtwt, type("")):
            dtwt = {t: w for t, w in self.tw.weights(self.tw.split(dtwt), preprocess=False)}
        if isinstance(qtwt, type("")):
            qtwt = {t: w for t, w in self.tw.weights(self.tw.split(qtwt), preprocess=False)}
        s = 1e-9
        for k, v in qtwt.items():
            if k in dtwt:
                s += v  # * dtwt[k]
        q = 1e-9
        for k, v in qtwt.items():
            q += v
        return s / q

    def paragraph(self, content_tks: str, keywords: list = [], keywords_topn=30):
        if isinstance(content_tks, str):
            content_tks = [c.strip() for c in content_tks.strip() if c.strip()]
        tks_w = self.tw.weights(content_tks, preprocess=False)

        keywords = [f'"{k.strip()}"' for k in keywords]
        for tk, w in sorted(tks_w, key=lambda x: x[1] * -1)[:keywords_topn]:
            tk_syns = self.syn.lookup(tk)
            tk_syns = [FulltextQueryer.subSpecialChar(s) for s in tk_syns]
            tk_syns = [rag_tokenizer.fine_grained_tokenize(s) for s in tk_syns if s]
            tk_syns = [f'"{s}"' if s.find(" ") > 0 else s for s in tk_syns]
            tk = FulltextQueryer.subSpecialChar(tk)
            if tk.find(" ") > 0:
                tk = '"%s"' % tk
            if tk_syns:
                tk = f"({tk} OR (%s)^0.2)" % " ".join(tk_syns)
            if tk:
                keywords.append(f"{tk}^{w}")

        return MatchTextExpr(self.query_fields, " ".join(keywords), 100, {"minimum_should_match": min(3, len(keywords) / 10)})
