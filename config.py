# -*- coding: utf-8 -*-

import time
import schedule
import os
import json
import threading

from whoosh import index
from whoosh.index import create_in
from whoosh.fields import *
from whoosh.qparser import QueryParser
from whoosh import qparser
from jieba.analyse import ChineseAnalyzer

from common import *

BOT_SRC_DIR = "bot_resources"
# 默认返回大小
default_size = 10

bot_intents_dict = {}
bot_priorities = {}
bot_recents = {}
bot_frequency = {}

bot_searcher = {}
bot_qp = {}


def build_bot_intents_dict(bot_name):
    # 刷新intents文件
    INTENT_FILE_ = os.path.join(BOT_SRC_DIR, bot_name, "intents.txt")
    intents_dict_ = {}
    for intent_ in read_file(INTENT_FILE_):
        intent_pro_ = pre_process(intent_)
        intents_dict_[intent_pro_] = intent_

        intent_pinyin_ = get_pinyin(intent_pro_)
        intents_dict_[intent_pinyin_] = intent_
    bot_intents_dict[bot_name] = intents_dict_


def build_bot_whoosh_index(bot_name, index_dir_):
    schema_ = Schema(content=TEXT(stored=True, analyzer=ChineseAnalyzer()))
    ix_ = create_in(index_dir_, schema_)
    writer_ = ix_.writer()
    for line_ in bot_intents_dict[bot_name].keys():
        writer_.add_document(content=line_)
    writer_.commit()
    return ix_


def build_bot_qp(bot_name, ix_):
    qp_and_ = QueryParser("content", ix_.schema)
    qp_and_.add_plugin(qparser.FuzzyTermPlugin())
    bot_qp[bot_name] = qp_and_


for bot_na in os.listdir(BOT_SRC_DIR):
    build_bot_intents_dict(bot_na)
    print(bot_na, "intents dict finished building...")

    # 加载whoosh索引文件
    index_dir = os.path.join(BOT_SRC_DIR, bot_na, "index")
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
        ix = build_bot_whoosh_index(bot_na, index_dir)
    else:
        ix = index.open_dir(index_dir)
    bot_searcher[bot_na] = ix.searcher()

    build_bot_qp(bot_na, ix)
    print(bot_na, "whoosh index finished building...")

    # 加载priority文件，越top优先级越高
    PRIORITY_FILE = os.path.join(BOT_SRC_DIR, bot_na, "priority.txt")
    bot_priorities[bot_na] = read_file(PRIORITY_FILE)
    print(bot_na, "priority file finished loading...")

    # 读取recent文件，越top优先级越高
    RECENT_FILE = os.path.join(BOT_SRC_DIR, bot_na, "recent.txt")
    if not os.path.exists(RECENT_FILE):
        recents = []
    else:
        recents = read_file(RECENT_FILE)
    bot_recents[bot_na] = recents
    print(bot_na, "recent file finished loading...")

    # 读取frequency文件
    FREQUENCY_FILE = os.path.join(BOT_SRC_DIR, bot_na, "frequency.json")
    if not os.path.exists(FREQUENCY_FILE):
        frequency = {}
    else:
        with open(FREQUENCY_FILE, encoding="utf-8") as f:
            frequency = json.load(f)
    bot_frequency[bot_na] = frequency
    print(bot_na, "frequency file finished loading...")


# 每天写入资源文件
def run_resources():
    for _bot_name_ in os.listdir(BOT_SRC_DIR):
        print(_bot_name_, 'starting writing resource files...')
        write_lines(os.path.join(BOT_SRC_DIR, _bot_name_, "recent.txt"), bot_recents[_bot_name_])
        open_file(os.path.join(BOT_SRC_DIR, _bot_name_, "frequency.json"), mode='w').write(
            json.dumps(bot_frequency[_bot_name_], ensure_ascii=False))


# 每30天reset排序因子
def run_resort():
    for bot_n in os.listdir(BOT_SRC_DIR):
        bot_recents[bot_n] = []
        bot_frequency[bot_n] = {}

        recent_file_path = os.path.join(BOT_SRC_DIR, bot_n, "recent.txt")
        freq_file_path = os.path.join(BOT_SRC_DIR, bot_n, "frequency.json")
        if os.path.exists(recent_file_path):
            os.remove(recent_file_path)
        if os.path.exists(freq_file_path):
            os.remove(freq_file_path)


schedule.every().day.do(run_resources)
schedule.every(30).days.do(run_resort)


# 多线程调度
def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)


threading.Thread(target=run_schedule).start()
