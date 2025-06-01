import logging
import copy
import datrie
import math
import os
import re
import string
from hanziconv import HanziConv
from nltk import word_tokenize
from nltk.stem import PorterStemmer, WordNetLemmatizer


class RagTokenizer:
    def key_(self, line):
        return str(line.lower().encode("utf-8"))[2:-1]

    def rkey_(self, line):
        return str(("DD" + (line[::-1].lower())).encode("utf-8"))[2:-1]

    def loadDict_(self, fnm):
        print(f"[HUQIE]:Build trie from {fnm}")
        try:
            of = open(fnm, "r", encoding="utf-8")
            while True:
                line = of.readline()
                if not line:
                    break
                line = re.sub(r"[\r\n]+", "", line)
                line = re.split(r"[ \t]", line)
                k = self.key_(line[0])
                F = int(math.log(float(line[1]) / self.DENOMINATOR) + 0.5)
                if k not in self.trie_ or self.trie_[k][0] < F:
                    self.trie_[self.key_(line[0])] = (F, line[2])
                self.trie_[self.rkey_(line[0])] = 1

            dict_file_cache = fnm + ".trie"
            print(f"[HUQIE]:Build trie cache to {dict_file_cache}")
            self.trie_.save(dict_file_cache)
            of.close()
        except Exception:
            logging.exception(f"[HUQIE]:Build trie {fnm} failed")

    def __init__(self):
        self.DENOMINATOR = 1000000
        self.DIR_ = os.path.join(os.path.dirname(os.path.realpath(__file__)), "res", "huqie")

        self.stemmer = PorterStemmer()
        self.lemmatizer = WordNetLemmatizer()

        self.SPLIT_CHAR = r"([ ,\.<>/?;:'\[\]\\`!@#$%^&*\(\)\{\}\|_+=《》，。？、；‘’：“”【】~！￥%……（）——-]+|[a-zA-Z0-9,\.-]+)"

        trie_file_name = self.DIR_ + ".txt.trie"
        # check if trie file existence
        if os.path.exists(trie_file_name):
            try:
                # load trie from file
                self.trie_ = datrie.Trie.load(trie_file_name)
                return
            except Exception:
                # fail to load trie from file, build default trie
                logging.exception(f"[HUQIE]:Fail to load trie file {trie_file_name}, build the default trie file")
                self.trie_ = datrie.Trie(string.printable)
        else:
            # file not exist, build default trie
            print(f"[HUQIE]:Trie file {trie_file_name} not found, build the default trie file")
            self.trie_ = datrie.Trie(string.printable)

        # load data from dict file and save to trie file
        self.loadDict_(self.DIR_ + ".txt")

    def _strQ2B(self, ustring):
        """全角转半角，转小写"""
        rstring = ""
        for uchar in ustring:
            inside_code = ord(uchar)
            if inside_code == 0x3000:
                inside_code = 0x0020
            else:
                inside_code -= 0xFEE0
            if inside_code < 0x0020 or inside_code > 0x7E:  # After the conversion, if it's not a half-width character, return the original character.
                rstring += uchar
            else:
                rstring += chr(inside_code)
        return rstring

    def _tradi2simp(self, line):
        """繁体转简体"""
        return HanziConv.toSimplified(line)

    def dfs_(self, chars, s, preTks, tkslist):
        res = s
        # if s > MAX_L or s>= len(chars):
        if s >= len(chars):
            tkslist.append(preTks)
            return res

        # pruning
        S = s + 1
        if s + 2 <= len(chars):
            t1, t2 = "".join(chars[s : s + 1]), "".join(chars[s : s + 2])
            if self.trie_.has_keys_with_prefix(self.key_(t1)) and not self.trie_.has_keys_with_prefix(self.key_(t2)):
                S = s + 2
        if len(preTks) > 2 and len(preTks[-1][0]) == 1 and len(preTks[-2][0]) == 1 and len(preTks[-3][0]) == 1:
            t1 = preTks[-1][0] + "".join(chars[s : s + 1])
            if self.trie_.has_keys_with_prefix(self.key_(t1)):
                S = s + 2

        for e in range(S, len(chars) + 1):
            t = "".join(chars[s:e])
            k = self.key_(t)

            if e > s + 1 and not self.trie_.has_keys_with_prefix(k):
                break

            if k in self.trie_:
                pretks = copy.deepcopy(preTks)
                if k in self.trie_:
                    pretks.append((t, self.trie_[k]))
                else:
                    pretks.append((t, (-12, "")))
                res = max(res, self.dfs_(chars, e, pretks, tkslist))

        if res > s:
            return res

        t = "".join(chars[s : s + 1])
        k = self.key_(t)
        if k in self.trie_:
            preTks.append((t, self.trie_[k]))
        else:
            preTks.append((t, (-12, "")))

        return self.dfs_(chars, s + 1, preTks, tkslist)

    def freq(self, tk):
        k = self.key_(tk)
        if k not in self.trie_:
            return 0
        return int(math.exp(self.trie_[k][0]) * self.DENOMINATOR + 0.5)

    def score_(self, tfts):
        B = 30
        F, L, tks = 0, 0, []
        for tk, (freq, tag) in tfts:
            F += freq
            L += 0 if len(tk) < 2 else 1
            tks.append(tk)
        # F /= len(tks)
        L /= len(tks)
        logging.debug("[SC] {} {} {} {} {}".format(tks, len(tks), L, F, B / len(tks) + L + F))
        return tks, B / len(tks) + L + F

    def sortTks_(self, tkslist):
        res = []
        for tfts in tkslist:
            tks, s = self.score_(tfts)
            res.append((tks, s))
        return sorted(res, key=lambda x: x[1], reverse=True)

    def merge_(self, tks):
        # if split chars is part of token
        res = []
        tks = re.sub(r"[ ]+", " ", tks).split()
        s = 0
        while True:
            if s >= len(tks):
                break
            E = s + 1
            for e in range(s + 2, min(len(tks) + 2, s + 6)):
                tk = "".join(tks[s:e])
                if re.search(self.SPLIT_CHAR, tk) and self.freq(tk):
                    E = e
            res.append("".join(tks[s:E]))
            s = E

        return " ".join(res)

    def maxForward_(self, line):
        res = []
        s = 0
        while s < len(line):
            e = s + 1
            t = line[s:e]
            while e < len(line) and self.trie_.has_keys_with_prefix(self.key_(t)):
                e += 1
                t = line[s:e]

            while e - 1 > s and self.key_(t) not in self.trie_:
                e -= 1
                t = line[s:e]

            if self.key_(t) in self.trie_:
                res.append((t, self.trie_[self.key_(t)]))
            else:
                res.append((t, (0, "")))

            s = e

        return self.score_(res)

    def maxBackward_(self, line):
        res = []
        s = len(line) - 1
        while s >= 0:
            e = s + 1
            t = line[s:e]
            while s > 0 and self.trie_.has_keys_with_prefix(self.rkey_(t)):
                s -= 1
                t = line[s:e]

            while s + 1 < e and self.key_(t) not in self.trie_:
                s += 1
                t = line[s:e]

            if self.key_(t) in self.trie_:
                res.append((t, self.trie_[self.key_(t)]))
            else:
                res.append((t, (0, "")))

            s -= 1

        return self.score_(res[::-1])

    def _split_by_lang(self, line):
        """根据语言进行切分"""
        txt_lang_pairs = []
        arr = re.split(self.SPLIT_CHAR, line)
        for a in arr:
            if not a:
                continue
            s = 0
            e = s + 1
            zh = is_chinese(a[s])
            while e < len(a):
                _zh = is_chinese(a[e])
                if _zh == zh:
                    e += 1
                    continue
                txt_lang_pairs.append((a[s:e], zh))
                s = e
                e = s + 1
                zh = _zh
            if s >= len(a):
                continue
            txt_lang_pairs.append((a[s:e], zh))
        return txt_lang_pairs

    def tokenize(self, line: str) -> str:
        """
        对输入文本进行分词，支持中英文混合处理。

        分词流程：
        1. 预处理：
           - 将所有非单词字符（字母、数字、下划线以外的）替换为空格。
           - 全角字符转半角。
           - 转换为小写。
           - 繁体中文转简体中文。
        2. 按语言切分：
           - 将预处理后的文本按语言（中文/非中文）分割成多个片段。
        3. 分段处理：
           - 对于非中文（通常是英文）片段：
             - 使用 NLTK 的 `word_tokenize` 进行分词。
             - 对分词结果进行词干提取 (PorterStemmer) 和词形还原 (WordNetLemmatizer)。
           - 对于中文片段：
             - 如果片段过短（长度<2）或为纯粹的英文/数字模式（如 "abc-def", "123.45"），则直接保留该片段。
             - 否则，采用基于词典的混合分词策略：
               a. 执行正向最大匹配 (FMM) 和逆向最大匹配 (BMM) 得到两组分词结果 (`tks` 和 `tks1`)。
               b. 比较 FMM 和 BMM 的结果：
                  i.  找到两者从开头开始最长的相同分词序列，这部分通常是无歧义的，直接加入结果。
                  ii. 对于 FMM 和 BMM 结果不一致的歧义部分（即从第一个不同点开始的子串）：
                      - 提取出这段有歧义的原始文本。
                      - 调用 `self.dfs_` (深度优先搜索) 在这段文本上探索所有可能的分词组合。
                      - `self.dfs_` 会利用Trie词典，并由 `self.sortTks_` 对所有组合进行评分和排序。
                      - 选择得分最高的分词方案作为该歧义段落的结果。
                  iii.继续处理 FMM 和 BMM 结果中歧义段落之后的部分，重复步骤 i 和 ii，直到两个序列都处理完毕。
               c. 如果在比较完所有对应部分后，FMM 或 BMM 仍有剩余（理论上如果实现正确且输入相同，剩余部分也应相同），
                  则对这部分剩余的原始文本同样使用 `self.dfs_` 进行最优分词。
        4. 后处理：
           - 将所有处理过的片段（英文词元、中文词元）用空格连接起来。
           - 调用 `self.merge_` 对连接后的结果进行进一步的合并操作，
             尝试合并一些可能被错误分割但实际是一个完整词的片段（基于词典检查）。
        5. 返回最终分词结果字符串（词元间用空格分隔）。

        Args:
            line (str): 待分词的原始输入字符串。

        Returns:
            str: 分词后的字符串，词元之间用空格分隔。
        """
        # 1. 预处理
        line = re.sub(r"\W+", " ", line)  # 将非字母数字下划线替换为空格
        line = self._strQ2B(line).lower()  # 全角转半角，转小写
        line = self._tradi2simp(line)  # 繁体转简体

        # 2. 按语言切分
        arr = self._split_by_lang(line)  # 将文本分割成 (文本片段, 是否为中文) 的列表
        res = []  # 存储最终分词结果的列表

        # 3. 分段处理
        for L, lang in arr:  # L 是文本片段，lang 是布尔值表示是否为中文
            if not lang:  # 如果不是中文
                # 使用NLTK进行分词、词干提取和词形还原
                res.extend([self.stemmer.stem(self.lemmatizer.lemmatize(t)) for t in word_tokenize(L)])
                continue  # 处理下一个片段

            # 如果是中文，但长度小于2或匹配纯英文/数字模式，则直接添加，不进一步切分
            if len(L) < 2 or re.match(r"[a-z\.-]+$", L) or re.match(r"[0-9\.-]+$", L):
                res.append(L)
                continue  # 处理下一个片段

            # 对较长的中文片段执行FMM和BMM
            tks, s = self.maxForward_(L)  # tks: FMM结果列表, s: FMM评分 FMM (Forward Maximum Matching - 正向最大匹配)
            tks1, s1 = self.maxBackward_(L)  # tks1: BMM结果列表, s1: BMM评分 BMM (Backward Maximum Matching - 逆向最大匹配)

            # 初始化用于比较FMM和BMM结果的指针
            i, j = 0, 0  # i 指向 tks1 (BMM), j 指向 tks (FMM)
            _i, _j = 0, 0  # _i, _j 记录上一段歧义处理的结束位置

            # 3.b.i. 查找 FMM 和 BMM 从头开始的最长相同前缀
            same = 0  # 相同词元的数量
            while i + same < len(tks1) and j + same < len(tks) and tks1[i + same] == tks[j + same]:
                same += 1
            if same > 0:  # 如果存在相同前缀
                res.append(" ".join(tks[j : j + same]))  # 将FMM中的相同部分加入结果

            # 更新指针到不同部分的开始
            _i = i + same
            _j = j + same
            # 准备开始处理可能存在的歧义部分
            j = _j + 1  # FMM指针向后移动一位（或多位，取决于下面tk的构造）
            i = _i + 1  # BMM指针向后移动一位（或多位）

            # 3.b.ii. 迭代处理 FMM 和 BMM 结果中的歧义部分
            while i < len(tks1) and j < len(tks):
                # tk1 是 BMM 从上一个同步点 _i 到当前指针 i 形成的字符串
                # tk 是 FMM 从上一个同步点 _j 到当前指针 j 形成的字符串
                tk1, tk = "".join(tks1[_i:i]), "".join(tks[_j:j])

                if tk1 != tk:  # 如果这两个子串不相同，说明FMM和BMM的切分路径出现分叉
                    # 尝试通过移动较短子串的指针来寻找下一个可能的同步点
                    if len(tk1) > len(tk):
                        j += 1
                    else:
                        i += 1
                    continue  # 继续外层while循环

                # 如果子串相同，但当前位置的单个词元不同，则这也是一个需要DFS解决的歧义点
                if tks1[i] != tks[j]:  # 注意：这里比较的是tks1[i]和tks[j]，而不是tk1和tk的最后一个词
                    i += 1
                    j += 1
                    continue

                # 从_j到j (不包括j处的词) 这段 FMM 产生的文本是歧义的，需要用DFS解决。
                tkslist = []
                self.dfs_("".join(tks[_j:j]), 0, [], tkslist)  # 对这段FMM子串进行DFS
                if tkslist:  # 确保DFS有结果
                    res.append(" ".join(self.sortTks_(tkslist)[0][0]))  # 取最优DFS结果

                # 处理当前这个相同的词元 (tks[j] 或 tks1[i]) 以及之后连续相同的词元
                same = 1
                while i + same < len(tks1) and j + same < len(tks) and tks1[i + same] == tks[j + same]:
                    same += 1
                res.append(" ".join(tks[j : j + same]))  # 将FMM中从j开始的连续相同部分加入结果

                # 更新指针到下一个不同部分的开始
                _i = i + same
                _j = j + same
                j = _j + 1
                i = _i + 1

            # 3.c. 处理 FMM 或 BMM 可能的尾部剩余部分
            # 如果 _i (BMM的已处理指针) 还没有到达 tks1 的末尾
            # (并且假设 _j (FMM的已处理指针) 也未到 tks 的末尾，且剩余部分代表相同的原始文本)
            if _i < len(tks1):
                # 断言确保FMM的已处理指针也未到末尾
                assert _j < len(tks)
                # 断言FMM和BMM的剩余部分代表相同的原始字符串
                assert "".join(tks1[_i:]) == "".join(tks[_j:])
                # 对FMM的剩余部分（代表了原始文本的尾部）进行DFS分词
                tkslist = []
                self.dfs_("".join(tks[_j:]), 0, [], tkslist)
                if tkslist:  # 确保DFS有结果
                    res.append(" ".join(self.sortTks_(tkslist)[0][0]))

        # 4. 后处理
        res_str = " ".join(res)  # 将所有分词结果用空格连接
        return self.merge_(res_str)  # 返回经过合并处理的最终分词结果


def is_chinese(s):
    if s >= "\u4e00" and s <= "\u9fa5":
        return True
    else:
        return False


if __name__ == "__main__":
    tknzr = RagTokenizer()
    tks = tknzr.tokenize("基于动态视觉相机的光流估计研究_孙文义.pdf")
    print(tks)
    tks = tknzr.tokenize("图3-1 事件流输入表征。（a）事件帧；（b）时间面；（c）体素网格\n(a)\n(b)\n(c)")
    print(tks)
