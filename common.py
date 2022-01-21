# -*- coding: utf-8 -*-

import string
import re
import datetime
import pypinyin
from whoosh.lang import stopwords
from zhon.hanzi import punctuation
import jieba


def open_file(filename, mode='r'):
    return open(filename, mode, encoding='utf-8', errors='ignore')


def read_file(filename):
    return [line.strip() for line in open(filename).readlines() if line.strip() != ""]


def write_file(filename, content):
    open_file(filename, mode="w").write(content)


def write_lines(filename, list_res):
    test_w = open_file(filename, mode="w")
    for j in list_res:
        test_w.write(j + "\n")


def rm_stws(query):
    en_stws = stopwords.stoplists["en"]
    remain_ws = [w for w in re.split(r'\s+', query) if w not in en_stws]
    return " ".join(remain_ws)


def pre_process(query):
    # 1. 去标点
    query = re.sub(r"[%s]+" % punctuation, "", query)
    for c in string.punctuation:
        query = query.replace(c, "")

    # 2. 分词
    query = " ".join(jieba.cut(query))

    # 3. 去停用词
    # query = rm_stws(query)

    # 4. 合并空格
    query = re.sub(r'\s+', ' ', query)
    return query


def get_pinyin(hanz):
    pinyin = pypinyin.lazy_pinyin(hanz, style=pypinyin.NORMAL)
    return rm_stws(" ".join(pinyin))


def time_cost(start, type_="sec"):
    interval = datetime.datetime.now() - start
    if type_ == "sec":
        return interval.total_seconds()
    elif type_ == "day":
        return interval.days
