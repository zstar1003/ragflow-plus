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
import os
import time
import re
from nltk.corpus import wordnet
from api.utils.file_utils import get_project_base_directory


class Dealer:
    def __init__(self, redis=None):
        self.lookup_num = 100000000
        self.load_tm = time.time() - 1000000
        self.dictionary = None
        path = os.path.join(get_project_base_directory(), "rag/res", "synonym.json")
        try:
            self.dictionary = json.load(open(path, "r", encoding="utf-8"))
        except Exception:
            logging.warning("Missing synonym.json")
            self.dictionary = {}

        if not redis:
            logging.warning("Realtime synonym is disabled, since no redis connection.")
        if not len(self.dictionary.keys()):
            logging.warning("Fail to load synonym")

        self.redis = redis
        self.load()

    def load(self):
        if not self.redis:
            return

        if self.lookup_num < 100:
            return
        tm = time.time()
        if tm - self.load_tm < 3600:
            return

        self.load_tm = time.time()
        self.lookup_num = 0
        d = self.redis.get("kevin_synonyms")
        if not d:
            return
        try:
            d = json.loads(d)
            self.dictionary = d
        except Exception as e:
            logging.error("Fail to load synonym!" + str(e))

    def lookup(self, tk, topn=8):
        """
        查找输入词条(tk)的同义词，支持英文和中文混合处理

        参数:
            tk (str): 待查询的词条（如"happy"或"苹果"）
            topn (int): 最多返回的同义词数量，默认为8

        返回:
            list: 同义词列表，可能为空（无同义词时）

        处理逻辑:
            1. 英文单词：使用WordNet语义网络查询
            2. 中文/其他：从预加载的自定义词典查询
        """
        # 英文单词处理分支
        if re.match(r"[a-z]+$", tk):
            res = list(set([re.sub("_", " ", syn.name().split(".")[0]) for syn in wordnet.synsets(tk)]) - set([tk]))
            return [t for t in res if t]

        # 中文/其他词条处理
        self.lookup_num += 1
        self.load()  # 自定义词典
        # 从字典获取同义词，默认返回空列表
        res = self.dictionary.get(re.sub(r"[ \t]+", " ", tk.lower()), [])
        # 兼容处理：如果字典值是字符串，转为单元素列表
        if isinstance(res, str):
            res = [res]
        return res[:topn]


if __name__ == "__main__":
    dl = Dealer()
    print(dl.dictionary)
