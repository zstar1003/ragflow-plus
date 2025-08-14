import copy
import logging
import math
import os
import re
import string

import datrie
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
        """전각을 반각으로, 소문자로 변환"""
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
        """번체를 간체로 변환"""
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
        """언어별로 분리"""
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
        입력 텍스트를 토크나이즈(분절)하며, 중영문 혼합 처리를 지원합니다.

        토크나이즈 과정:
        1. 전처리:
            - 모든 단어 문자가 아닌 문자(알파벳, 숫자, 밑줄 제외)를 공백으로 대체
            - 전각 문자를 반각으로 변환
            - 소문자로 변환
            - 번체 중국어를 간체로 변환
        2. 언어별 분리:
            - 전처리된 텍스트를 언어(중국어/비중국어)별로 여러 조각으로 분할
        3. 조각별 처리:
            - 비중국어(주로 영어) 조각:
                - NLTK의 `word_tokenize`로 분절
                - 결과에 대해 어간 추출(PorterStemmer) 및 표제어 추출(WordNetLemmatizer)
            - 중국어 조각:
                - 조각이 너무 짧거나(길이<2), 순수 영문/숫자 패턴(예: "abc-def", "123.45")이면 그대로 보존
                - 그렇지 않으면 사전 기반 혼합 분절 전략 적용:
                a. 정방향 최대 매칭(FMM)과 역방향 최대 매칭(BMM)으로 두 개의 분절 결과(`tks`, `tks1`) 생성
                b. FMM과 BMM 결과 비교:
                    i.  두 결과의 시작부터 가장 긴 동일 분절 시퀀스를 찾아 결과에 추가
                    ii. FMM과 BMM 결과가 다른 부분(첫 차이점부터의 부분 문자열):
                            - 이 부분의 원본 텍스트 추출
                            - `self.dfs_`(깊이 우선 탐색)으로 가능한 모든 분절 조합 탐색
                            - `self.dfs_`는 Trie 사전을 활용, `self.sortTks_`로 모든 조합을 평가 및 정렬
                            - 가장 점수가 높은 분절을 해당 부분 결과로 선택
                    iii. FMM/BMM 결과의 모호 부분 이후를 반복적으로 처리
                c. 모든 부분 비교 후 FMM/BMM에 남은 부분이 있으면(이론상 구현이 정확하다면 동일해야 함),
                    이 부분도 `self.dfs_`로 최적 분절 수행
        4. 후처리:
            - 모든 처리된 조각(영문 토큰, 중문 토큰)을 공백으로 연결
            - `self.merge_`로 추가 병합 처리(사전 기반으로 잘못 분리된 조각 합침)
        5. 최종 분절 결과 문자열(토큰 간 공백 구분) 반환

        Args:
            line (str): 분절할 원본 입력 문자열

        Returns:
            str: 분절된 문자열(토큰 간 공백)
        """
        # 1. 전처리
        line = re.sub(r"\W+", " ", line)  # 모든 단어 문자가 아닌 문자(알파벳, 숫자, 밑줄 제외)를 공백으로 대체
        line = self._strQ2B(line).lower()  # 전각을 반각으로, 소문자로 변환
        line = self._tradi2simp(line)  # 번체를 간체로 변환

        # 2. 언어별 분리
        arr = self._split_by_lang(line)  # (텍스트 조각, 중국어 여부) 리스트로 분리
        res = []  # 최종 토큰 결과 리스트

        # 3. 조각별 처리
        for L, lang in arr:  # L: 텍스트 조각, lang: 중국어 여부
            if not lang:  # 중국어가 아니면
                # NLTK로 분절, 어간 추출, 표제어 추출
                res.extend([self.stemmer.stem(self.lemmatizer.lemmatize(t)) for t in word_tokenize(L)])
                continue  # 处理下一个片段

            # 중국어이지만 길이<2이거나 영문/숫자 패턴이면 그대로 추가
            if len(L) < 2 or re.match(r"[a-z\.-]+$", L) or re.match(r"[0-9\.-]+$", L):
                res.append(L)
                continue  # 处理下一个片段

            # 긴 중국어 조각은 FMM/BMM 적용
            tks, s = self.maxForward_(L)  # FMM 결과
            tks1, s1 = self.maxBackward_(L)  # BMM 결과

            # FMM/BMM 결과 비교
            i, j = 0, 0
            _i, _j = 0, 0

            # 3.b.i. FMM/BMM의 동일한 앞부분 찾기
            same = 0
            while i + same < len(tks1) and j + same < len(tks) and tks1[i + same] == tks[j + same]:
                same += 1
            if same > 0:
                res.append(" ".join(tks[j : j + same]))

            _i = i + same
            _j = j + same
            j = _j + 1
            i = _i + 1

            # 3.b.ii. FMM/BMM의 모호 부분 반복 처리
            while i < len(tks1) and j < len(tks):
                tk1, tk = "".join(tks1[_i:i]), "".join(tks[_j:j])

                if tk1 != tk:
                    if len(tk1) > len(tk):
                        j += 1
                    else:
                        i += 1
                    continue

                if tks1[i] != tks[j]:
                    i += 1
                    j += 1
                    continue

                tkslist = []
                self.dfs_("".join(tks[_j:j]), 0, [], tkslist)
                if tkslist:
                    res.append(" ".join(self.sortTks_(tkslist)[0][0]))

                same = 1
                while i + same < len(tks1) and j + same < len(tks) and tks1[i + same] == tks[j + same]:
                    same += 1
                res.append(" ".join(tks[j : j + same]))

                _i = i + same
                _j = j + same
                j = _j + 1
                i = _i + 1

            # 3.c. FMM/BMM의 남은 부분 처리
            if _i < len(tks1):
                assert _j < len(tks)
                assert "".join(tks1[_i:]) == "".join(tks[_j:])
                tkslist = []
                self.dfs_("".join(tks[_j:]), 0, [], tkslist)
                if tkslist:
                    res.append(" ".join(self.sortTks_(tkslist)[0][0]))

        # 4. 후처리
        res_str = " ".join(res)
        return self.merge_(res_str)


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
