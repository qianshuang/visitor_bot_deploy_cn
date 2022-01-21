# -*- coding: utf-8 -*-

import shutil

from flask import Flask, jsonify
from flask import request
from gevent import pywsgi

from helper import *

app = Flask(__name__)


@app.route('/search', methods=['GET', 'POST'])
def search():
    """
    input json:
    {
        "bot_name": "xxxxxx",  # 要查询的bot name
        "query": "xxxxxx",  # 用户query
        "size": 10         # 最大返回大小，默认10
    }

    return:
    {   'code': 0,m
        'msg': 'success',
        'data': []
    }
    """
    resq_data = json.loads(request.get_data())
    bot_n = resq_data["bot_name"].strip()
    data = resq_data["query"].strip()
    size = int(resq_data["size"]) if "size" in resq_data else default_size

    data = pre_process(data)

    # 1. 前缀搜索
    whoosh_pre_res = whoosh_search(bot_n, data)
    # 2. 断句前缀搜索
    if_split = bool(re.search(r'[,，.。]', data))
    if len(whoosh_pre_res) == 0 and if_split:
        whoosh_pre_res = whoosh_search(bot_n, re.split(r'[,，.。]', data)[-1].strip())
    # 3. 拼音前缀搜索
    if len(whoosh_pre_res) == 0:
        data_pinyin = get_pinyin(data)
        whoosh_pre_res = whoosh_search(bot_n, data_pinyin)
    # 4. 断句拼音前缀搜索
    if len(whoosh_pre_res) == 0 and if_split:
        whoosh_pre_res = whoosh_search(bot_n, re.split(r'[,，.。]', data_pinyin)[-1].strip())

    priorities_res = bot_priorities[bot_n]
    ranked_whoosh_res = rank(bot_n, list(set(whoosh_pre_res) - set(priorities_res)))
    # 5. 全文检索
    if len(priorities_res + ranked_whoosh_res) >= size:
        whoosh_res = []
    else:
        whoosh_res = whoosh_search(bot_n, data)

    ori_res = priorities_res + ranked_whoosh_res + whoosh_res
    final_res = sorted(set(ori_res), key=ori_res.index)
    return {'code': 0, 'msg': 'success', 'data': final_res[:size]}


@app.route('/callback', methods=['GET', 'POST'])
def callback():
    """
    {
        "bot_name": "xxxxxx",  # 要操作的bot name
        "intent": "xxxxxx"  # 匹配到的标准答案
    }
    """
    resq_data = json.loads(request.get_data())
    bot_n = resq_data["bot_name"].strip()
    intent = resq_data["intent"].strip()

    # 回写recent文件
    if intent in bot_recents[bot_n]:
        bot_recents[bot_n].remove(intent)
    bot_recents[bot_n].insert(0, intent)

    # 回写frequency文件
    bot_frequency[bot_n].setdefault(intent, 0)
    bot_frequency[bot_n][intent] = bot_frequency[bot_n][intent] + 1

    result = {'code': 0, 'msg': 'success', 'data': resq_data}
    return jsonify(result)


@app.route('/refresh', methods=['GET', 'POST'])
def refresh():
    """
    更新intents.txt、priority.txt后，需要手动刷新才生效
    {
        "bot_name": "xxxxxx",  # 要操作的bot name
        "operate": "upsert",  # 操作。upsert：更新或新增；delete：删除
    }
    """
    start = datetime.datetime.now()

    resq_data = json.loads(request.get_data())
    bot_n = resq_data["bot_name"].strip()
    operate = resq_data["operate"].strip()

    if operate == "upsert":
        build_bot_intents_dict(bot_n)
        # rebuild whoosh索引文件
        index_dir_ = os.path.join(BOT_SRC_DIR, bot_n, "index")
        if not os.path.exists(index_dir_):
            os.mkdir(index_dir_)
        ix_ = build_bot_whoosh_index(bot_n, index_dir_)
        bot_searcher[bot_n] = ix_.searcher()
        build_bot_qp(bot_n, ix_)

        # 加载priority文件，越top优先级越高
        PRIORITY_FILE_ = os.path.join(BOT_SRC_DIR, bot_n, "priority.txt")
        bot_priorities[bot_n] = read_file(PRIORITY_FILE_)
        return {'code': 0, 'msg': 'success', 'time_cost': time_cost(start)}
    elif operate == "copy":
        # 复制bot。一方面不用从头训练，直接复用原始bot的能力；另一方面避免误删除bot
        src_bot_name = resq_data["src_bot_name"].strip()
        src_bot_path = os.path.join(BOT_SRC_DIR, src_bot_name)
        bot_path = os.path.join(BOT_SRC_DIR, bot_n)
        shutil.copytree(src_bot_path, bot_path)

        bot_intents_dict[bot_n] = bot_intents_dict[src_bot_name]
        bot_priorities[bot_n] = bot_priorities[src_bot_name]
        bot_recents[bot_n] = bot_recents[src_bot_name]
        bot_frequency[bot_n] = bot_frequency[src_bot_name]

        bot_searcher[bot_n] = bot_searcher[src_bot_name]
        bot_qp[bot_n] = bot_qp[src_bot_name]
        return {'code': 0, 'msg': 'success', 'time_cost': time_cost(start)}
    elif operate == "delete":
        # 删除bot
        try:
            shutil.rmtree(os.path.join(BOT_SRC_DIR, bot_n))
            del bot_intents_dict[bot_n]
            del bot_recents[bot_n]
            del bot_frequency[bot_n]
            del bot_priorities[bot_n]

            del bot_searcher[bot_n]
            del bot_qp[bot_n]
        except:
            print(bot_n, "deleted already...")
        return {'code': 0, 'msg': 'success', 'time_cost': time_cost(start)}
    else:
        return {'code': -1, 'msg': 'unsupported operation', 'time_cost': time_cost(start)}


if __name__ == '__main__':
    server = pywsgi.WSGIServer(('0.0.0.0', 8088), app)
    server.serve_forever()
    # app.run(debug=False, threaded=True, host='0.0.0.0', port=8088)
