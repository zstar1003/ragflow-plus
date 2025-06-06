#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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
import json
import re
import csv
from copy import deepcopy
from rag.app.qa import Excel
from rag.nlp import rag_tokenizer
from rag.nlp import find_codec


def get_text(fnm: str, binary=None) -> str:
    txt = ""
    if binary:
        encoding = find_codec(binary)
        txt = binary.decode(encoding, errors="ignore")
    else:
        with open(fnm, "r") as f:
            while True:
                line = f.readline()
                if not line:
                    break
                txt += line
    return txt


def beAdoc(d, q, a, eng, row_num=-1):
    d["content_with_weight"] = q
    d["content_ltks"] = rag_tokenizer.tokenize(q)
    d["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(d["content_ltks"])
    d["tag_kwd"] = [t.strip() for t in a.split(",") if t.strip()]
    if row_num >= 0:
        d["top_int"] = [row_num]
    return d


def chunk(filename, binary=None, lang="Chinese", callback=None, **kwargs):
    """
    Excel and csv(txt) format files are supported.
    If the file is in excel format, there should be 2 column content and tags without header.
    And content column is ahead of tags column.
    And it's O.K if it has multiple sheets as long as the columns are rightly composed.

    If it's in csv format, it should be UTF-8 encoded. Use TAB as delimiter to separate content and tags.

    All the deformed lines will be ignored.
    Every pair will be treated as a chunk.
    """
    eng = lang.lower() == "english"
    res = []
    doc = {"docnm_kwd": filename, "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename))}
    if re.search(r"\.xlsx?$", filename, re.IGNORECASE):
        callback(0.1, "Start to parse.")
        excel_parser = Excel()
        for ii, (q, a) in enumerate(excel_parser(filename, binary, callback)):
            res.append(beAdoc(deepcopy(doc), q, a, eng, ii))
        return res

    elif re.search(r"\.(txt)$", filename, re.IGNORECASE):
        callback(0.1, "Start to parse.")
        txt = get_text(filename, binary)
        lines = txt.split("\n")
        comma, tab = 0, 0
        for line in lines:
            if len(line.split(",")) == 2:
                comma += 1
            if len(line.split("\t")) == 2:
                tab += 1
        delimiter = "\t" if tab >= comma else ","

        fails = []
        content = ""
        i = 0
        while i < len(lines):
            arr = lines[i].split(delimiter)
            if len(arr) != 2:
                content += "\n" + lines[i]
            elif len(arr) == 2:
                content += "\n" + arr[0]
                res.append(beAdoc(deepcopy(doc), content, arr[1], eng, i))
                content = ""
            i += 1
            if len(res) % 999 == 0:
                callback(len(res) * 0.6 / len(lines), ("Extract TAG: {}".format(len(res)) + (f"{len(fails)} failure, line: %s..." % (",".join(fails[:3])) if fails else "")))

        callback(0.6, ("Extract TAG: {}".format(len(res)) + (f"{len(fails)} failure, line: %s..." % (",".join(fails[:3])) if fails else "")))

        return res

    elif re.search(r"\.(csv)$", filename, re.IGNORECASE):
        callback(0.1, "Start to parse.")
        txt = get_text(filename, binary)
        lines = txt.split("\n")

        fails = []
        content = ""
        res = []
        reader = csv.reader(lines)

        for i, row in enumerate(reader):
            row = [r.strip() for r in row if r.strip()]
            if len(row) != 2:
                content += "\n" + lines[i]
            elif len(row) == 2:
                content += "\n" + row[0]
                res.append(beAdoc(deepcopy(doc), content, row[1], eng, i))
                content = ""
            if len(res) % 999 == 0:
                callback(len(res) * 0.6 / len(lines), ("Extract Tags: {}".format(len(res)) + (f"{len(fails)} failure, line: %s..." % (",".join(fails[:3])) if fails else "")))

        callback(0.6, ("Extract TAG : {}".format(len(res)) + (f"{len(fails)} failure, line: %s..." % (",".join(fails[:3])) if fails else "")))
        return res

    raise NotImplementedError("Excel, csv(txt) format files are supported.")


def label_question(question, kbs):
    """
    标记问题的标签。

    该函数通过给定的问题和知识库列表，对问题进行标签标记。它首先确定哪些知识库配置了标签，
    然后从缓存中获取这些标签，必要时从设置中检索标签。最后，使用这些标签对问题进行标记。

    参数:
    question (str): 需要标记的问题。
    kbs (list): 知识库对象列表，用于标签标记。

    返回:
    list: 与问题相关的标签列表。
    """
    from api.db.services.knowledgebase_service import KnowledgebaseService
    from graphrag.utils import get_tags_from_cache, set_tags_to_cache
    from api import settings

    # 初始化标签和标签知识库ID列表
    tags = None
    tag_kb_ids = []

    # 遍历知识库，收集所有标签知识库ID
    for kb in kbs:
        if kb.parser_config.get("tag_kb_ids"):
            tag_kb_ids.extend(kb.parser_config["tag_kb_ids"])

    # 如果存在标签知识库ID，则进一步处理
    if tag_kb_ids:
        # 尝试从缓存中获取所有标签
        all_tags = get_tags_from_cache(tag_kb_ids)

        # 如果缓存中没有标签，从设置中检索标签，并设置缓存
        if not all_tags:
            all_tags = settings.retrievaler.all_tags_in_portion(kb.tenant_id, tag_kb_ids)
            set_tags_to_cache(all_tags, tag_kb_ids)
        else:
            # 如果缓存中获取到标签，将其解析为JSON格式
            all_tags = json.loads(all_tags)

        # 根据标签知识库ID获取对应的标签知识库
        tag_kbs = KnowledgebaseService.get_by_ids(tag_kb_ids)

        # 使用设置中的检索器对问题进行标签标记
        tags = settings.retrievaler.tag_query(question, list(set([kb.tenant_id for kb in tag_kbs])), tag_kb_ids, all_tags, kb.parser_config.get("topn_tags", 3))

    # 返回标记的标签
    return tags


if __name__ == "__main__":
    import sys

    def dummy(prog=None, msg=""):
        pass

    chunk(sys.argv[1], from_page=0, to_page=10, callback=dummy)
