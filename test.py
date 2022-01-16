# -*- coding: utf-8 -*-

import re
from zhon.hanzi import punctuation

from common import *

line = "测试。。去除标点『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿。。      "
print(pre_process(line))
