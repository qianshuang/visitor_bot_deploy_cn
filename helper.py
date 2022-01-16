# -*- coding: utf-8 -*-

import Levenshtein
import pandas as pd
from config import *


def peak_wrong_word(query, intent):
    query_words = query.split(" ")
    intent_words = intent.split(" ")
    for i in range(len(query_words) - 1):
        if query_words[i] != intent_words[i] and Levenshtein.ratio(query_words[i], intent_words[i]) >= 0.8:
            corrections[query_words[i]] = intent_words[i]


def smart_hint(bot_n, query):
    query = pre_process(query)
    # 4. 前缀匹配
    result = bot_trie[bot_n].keys(query)

    # 5. 纠错
    if len(result) == 0:
        query = query.strip()
        pres = query.split(" ")[:-1]
        last = query.split(" ")[-1]
        pre_corr_query = " ".join([correction(w) for w in pres])
        result = bot_trie[bot_n].keys(pre_corr_query + " " + last)
        if len(result) == 0:
            corr_query = pre_corr_query + " " + correction(last)
            result = bot_trie[bot_n].keys(corr_query)

    # 6. 还原原文本
    return [bot_intents_lower_dict[bot_n][res] for res in result]


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


def leven(bot_n, query):
    query = pre_process(query)
    res = []
    for k, v in bot_intents_lower_dict[bot_n].items():
        score = Levenshtein.ratio(k[:len(query)], query)
        if score >= 0.8:
            # res.append((score, v))
            res.append(v)
    # return sorted(res, reverse=True)
    return res


def whoosh_search(bot_n, query):
    query = pre_process(query)
    query = " ".join([w + "~" for w in query.split(" ")])
    query = bot_qp[bot_n].parse(query)
    results = bot_searcher[bot_n].search(query)

    res = []
    for r in results:
        res.extend(r.values())
    return res


# 单词纠错
def P(word, N=sum(WORDS.values())):
    """Probability of `word`."""
    return WORDS[word] / N


def correction(word):
    if word in corrections:
        return corrections[word]
    """Most probable spelling correction for word."""
    return max(candidates(word), key=P)


def candidates(word):
    """Generate possible spelling corrections for word."""
    return known([word]) or known(edits1(word)) or known(edits2(word)) or [word]


def known(words_):
    """The subset of `words` that appear in the dictionary of WORDS."""
    return set(w for w in words_ if w in WORDS)


def edits1(word):
    """All edits that are one edit away from `word`."""
    letters = 'abcdefghijklmnopqrstuvwxyz'
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [L + R[1:] for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
    replaces = [L + c + R[1:] for L, R in splits if R for c in letters]
    inserts = [L + c + R for L, R in splits for c in letters]
    return set(deletes + transposes + replaces + inserts)


def edits2(word):
    """All edits that are two edits away from `word`."""
    return (e2 for e1 in edits1(word) for e2 in edits1(e1))
