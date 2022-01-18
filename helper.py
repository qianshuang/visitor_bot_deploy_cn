# -*- coding: utf-8 -*-

import pandas as pd
from config import *


def rank(bot_n, trie_res):
    frequency_ = []
    recents_ = []
    for item in trie_res:
        if item in bot_frequency[bot_n]:
            frequency_.append(bot_frequency[bot_n][item])
        else:
            frequency_.append(0)

        if item in bot_recents[bot_n]:
            recents_.append(len(bot_recents[bot_n]) - bot_recents[bot_n].index(item))
        else:
            recents_.append(0)
    df = pd.DataFrame({"trie_res": trie_res, "frequency": frequency_, "recents": recents_})
    df.sort_values(by=["frequency", "recents"], ascending=False, inplace=True)
    return df["trie_res"].values.tolist()


def whoosh_search(bot_n, query, type_):
    query = pre_process(query)
    pres = query.split(" ")[:-1]
    last = query.split(" ")[-1]
    pres_fuzzy = " ".join([w + "~2" for w in pres])
    last_fuzzy = last + "~2/" + str(len(last))
    query = (pres_fuzzy + " " + last_fuzzy).strip()

    if type_ == "and":
        query = bot_qp_and[bot_n].parse(query)
    else:
        query = bot_qp_or[bot_n].parse(query)

    results = bot_searcher[bot_n].search(query)

    # 还原源文本
    res = []
    for r in results:
        res.extend(r.values())
    ori_res = [bot_intents_dict[bot_n][r] for r in res]
    return sorted(set(ori_res), key=ori_res.index)
