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
    {   'code': 0,
        'msg': 'success',
        'data': []
    }
    """
    resq_data = json.loads(request.get_data())
    bot_n = resq_data["bot_name"].strip()
    data = resq_data["query"].strip()
    size = int(resq_data["size"]) if "size" in resq_data else default_size

    # 1. 原句trie
    trie_res = smart_hint(bot_n, data)
    # 2. 标点最后1句trie
    if len(trie_res) == 0:
        trie_res = smart_hint(bot_n, re.split(r'[,|.]', data)[-1].strip())
    # 3. 编辑距离（若有性能问题，使用whoosh的FuzzyTermPlugin：tommy~2/3）
    if len(trie_res) == 0:
        trie_res = leven(bot_n, data)

    priorities_res = bot_priorities[bot_n]
    ranked_trie_res = rank(bot_n, list(set(trie_res) - set(priorities_res)))
    # 4. 全文检索
    if len(priorities_res + ranked_trie_res) >= size:
        whoosh_res = []
    else:
        whoosh_res = whoosh_search(bot_n, data)

    result = {'code': 0, 'msg': 'success', 'data': (priorities_res + ranked_trie_res + whoosh_res)[:size]}
    return result


@app.route('/callback', methods=['GET', 'POST'])
def callback():
    """
    {
        "bot_name": "xxxxxx",  # 要操作的bot name
        "query": "xxxxxx"  # 用户query
        "intent": "xxxxxx"  # 匹配到的标准答案
    }
    """
    resq_data = json.loads(request.get_data())
    bot_n = resq_data["bot_name"].strip()
    query = resq_data["query"]  # 此处不能strip()
    intent = resq_data["intent"].strip()

    # 回写recent文件
    if intent in bot_recents[bot_n]:
        bot_recents[bot_n].remove(intent)
    bot_recents[bot_n].insert(0, intent)

    # 回写frequency文件
    bot_frequency[bot_n].setdefault(intent, 0)
    bot_frequency[bot_n][intent] = bot_frequency[bot_n][intent] + 1

    # 回写纠错表
    query = pre_process(query)
    intent = pre_process(intent)
    if len(trie.keys(query)) > 0:
        peak_wrong_word(query, intent)
    else:
        query_ = re.split(r'[,|.]', query)[-1]
        peak_wrong_word(query_, intent)

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
    resq_data = json.loads(request.get_data())
    bot_n = resq_data["bot_name"].strip()
    operate = resq_data["operate"].strip()

    if operate == "upsert":
        # 刷新intents文件
        INTENT_FILE_ = os.path.join(BOT_SRC_DIR, bot_n, "intents.txt")
        intents_lower_dict_ = {pre_process(intent): intent for intent in read_file(INTENT_FILE_)}
        trie_ = marisa_trie.Trie(list(intents_lower_dict_.keys()))

        bot_intents_lower_dict[bot_n] = intents_lower_dict_
        bot_trie[bot_n] = trie_
        print(bot_n, "intents trie finished rebuilding...")

        # 重建whoosh索引
        index_dir_ = os.path.join(BOT_SRC_DIR, bot_n, "index")
        if not os.path.exists(index_dir_):
            os.mkdir(index_dir_)

        schema_ = Schema(content=TEXT(stored=True))
        ix_ = create_in(index_dir_, schema_)
        writer_ = ix_.writer()
        for line_ in read_file(INTENT_FILE_):
            writer_.add_document(content=line_)
        writer_.commit()
        searcher_ = ix_.searcher()

        qp_ = QueryParser("content", ix_.schema, group=OrGroup)
        qp_.add_plugin(qparser.FuzzyTermPlugin())

        bot_searcher[bot_n] = searcher_
        bot_qp[bot_n] = qp_
        print(bot_n, "whoosh index finished rebuilding...")

        # 刷新priority文件
        PRIORITY_FILE_ = os.path.join(BOT_SRC_DIR, bot_n, "priority.txt")
        bot_priorities[bot_n] = read_file(PRIORITY_FILE_)
        print(bot_n, "priority file finished reloading...")
    elif operate == "delete":
        # 删除bot
        try:
            shutil.rmtree(os.path.join(BOT_SRC_DIR, bot_n))
            del bot_intents_lower_dict[bot_n]
            del bot_trie[bot_n]
            del bot_recents[bot_n]
            del bot_frequency[bot_n]
            del bot_priorities[bot_n]

            del bot_searcher[bot_n]
            del bot_qp[bot_n]
        except:
            print(bot_n, "deleted already...")
            # traceback.print_stack()
    else:
        return {'code': -1, 'msg': 'unsupported operation', 'bot': bot_n}
    return {'code': 0, 'msg': 'success', 'bot': bot_n}


if __name__ == '__main__':
    server = pywsgi.WSGIServer(('0.0.0.0', 8088), app)
    server.serve_forever()
    # app.run(debug=False, threaded=True, host='0.0.0.0', port=8088)
