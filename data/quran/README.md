# 古兰经 RAG 数据集（Pickthall 英译 / Саблуков 俄译 / 马坚中译简体）

与 `../bible-rag-data/` 的圣经数据集同构，可放进同一个索引（用 `corpus` 字段区分）。

## 文件
- `quran_en.jsonl`：英文 Pickthall 译本《The Meaning of the Glorious Koran》(1930)，6,236 节
- `quran_ru.jsonl`：俄文 Г. С. Саблуков 译本（初版 1878，喀山），6,236 节
- `quran_zh.jsonl`：中文马坚译本（简体），6,236 节
- `surahs.json`：book_index(1-114) → code (Q001…Q114)、translit（拉丁转写）、arabic（阿拉伯文）、en/ru/zh 章名、ayah_count、revelation_place
- 原始数据与构建脚本在盒子 `/workspace/bible/quran-raw/`（`build.py` 可重新生成全部输出）

三个文件均为 6,236 行，114 章，每章节数与 quran.com 的 `verses_count`（哈夫斯/库法计数）逐章核对一致，无缺节、无重复。

## 字段（每行一节）
translation（`pickthall` / `sablukov` / `majian`）, corpus（固定为 `quran`）, book_index（章号 1-114）, book_code（`Q001`…）, book_name（本语言章名）, chapter, verse, text（已去掉标记、注脚、多余空白和 BOM）

## 注意
- 古兰经只有一级编号（章:节，surah:ayah），没有"卷→章"两级。为了和圣经数据字段一致：**chapter == book_index**（都等于章号），verse 为节号。引用写作 `2:255` 即 (book_index=2, verse=255)。
- 编号采用通行的哈夫斯/库法体系：「奉至仁至慈的真主之名」(Basmala) 只在第 1 章算作第 1 节；其他章开头的 Basmala 不单独成节、也不出现在文本里。
- 俄文 Саблуков 的原版 (1878/1894) 使用 Flügel 编号，这里用的是 Tanzil 已按哈夫斯编号重新对齐、并改为现代正字法的版本。他把章首神秘字母译成教会斯拉夫字母名，如 2:1 “(Аз, люди, мыслете.)”，原文如此，已保留。
- 章名：en/ru 取自 quran.com 的译名；zh 取马坚译本自身的章名（如 开端、黄牛、仪姆兰的家属）。
- 中文含个别 CJK 扩展 C 区字，如 “𪴙楛”（攒楛树，3 处），需要支持该区的字体。
- 中文引号已统一为 “” ‘’，括号统一为 （）；〔〕是原书用来标补充语的另一种括号，保留。

## 来源与许可（请认真看）
| 文件 | 译本 | 下载来源 | 版权状态 |
|---|---|---|---|
| quran_en | M. M. Pickthall，1930 年 Knopf (纽约) / Allen & Unwin (伦敦) 初版 | https://tanzil.net/trans/en.pickthall | **公有领域**：美国 1930 年出版物自 2026-01-01 起进入公有领域；Pickthall 卒于 1936 年，按“终生+70 年”在英国/欧盟早已进入公有领域 |
| quran_ru | Г. С. Саблуков (1804–1880)，1878 年初版 | https://tanzil.net/trans/ru.sablukov | **公有领域**（译者 1880 年去世） |
| quran_zh | 马坚 (1906–1978)，中国社会科学出版社 1981 年出版 | 主文本：香港伊斯兰联会网站 https://www.islam.org.hk/quran_chinese/ （繁体，经 OpenCC t2s 转简体）；对照/补缺：https://tanzil.net/trans/zh.jian 及简体镜像 b4.zhunei.love | **仍受版权保护**：中国著作权为作者终生+50 年，马坚 1978 年去世，保护至 **2028-12-31**。不是公有领域 |
| surahs.json | 章名 | https://api.quran.com/api/v4/chapters?language=en / ru / zh | 许可未声明；仅为简短事实性名称 |

- Tanzil 译文页的条款 (https://tanzil.net/trans/)：译文“仅限非商业用途”，商用需向译者或出版方取得许可；使用多于三个译本须附 Tanzil 链接。该条款不能给已属公有领域的 Pickthall、Саблуков 增加版权，但对马坚译本有效。
- **马坚中译仅适合个人/研究/非商业用途**；若要商用或公开再发布，需要取得版权方许可，或改用公有领域译本。目前没有完整的公有领域中文电子本：王静斋《古兰经译解》丙种本 (1946，译者卒于 1949 年，已进入公有领域) 在维基文库 https://zh.wikisource.org/wiki/古蘭經譯解 仅有部分章节，可作为将来的替代方案。
- 未选用的译本：Sahih International（英，1997，有版权）；Кулиев（俄，1990 年代，有版权）；Крачковский（俄，译者 1951 年去世但译本 1963 年才首次出版，按俄罗斯民法典第 1281 条第 3 款自出版起保护 70 年，约至 2034 年，有争议，故不用）。

## 已做的清洗与修正
- **中文改用 islam.org.hk 文本为主**：Tanzil / quran.com / fawazahmed0 上流传的马坚简体本 (zh.jian) 有大量损坏：
  2:282、4:12 被截断（约 750 字节处断掉，4:12 中间还缺一段）；GBK 乱码 “棗” 替代 “——”；
  阿拉伯数字/字母混入（如 6:84 “达5德”、7:54 “6日”、9:36 “十2个月”）；200 多处汉字间多余空格；
  `<br>`；半角标点；以及节文错位/重复（如 7:109 与 7:110、26:217–219、4:110、85:10、99:6–8 等处整节错位）。
  islam.org.hk 版未见这些问题，并修正了不少错别字（如 赈济贫民、木桩、拈阄）。与 Tanzil 相比共有 1,240 节存在文字差异（多数为用字差异如“甚么/什么”，少数为该网站版的修订措辞，如 3:102、4:69）。
- islam.org.hk 的第 21、23 章网页在服务器端被截断，缺 21:105–112、23:111–118 共 16 节，取自同一文本的简体镜像 (b4.zhunei.love mkq021/mkq023) 补齐。
- 原书 “－” 误作 “一” 的 19 处已改正（如 4:12 “八分之一”）。
- 14 处叩头节 (sajdah) 标记 “※” 已删除（7:206、13:15、16:50、17:109、19:58、22:18 等）。
- 2 处无法显示的造字占位符已处理：12:41 “【燄鳥】” 改为 “吃”（与 Tanzil 本一致）；71:28 “【？】” 删除。
- 2 处括号不配对 “﹙…〕”（27:54、31:11）改为 “（…）”。
- 俄文：3 处 OCR 残留 “№” 已修正（5:111、40:37 改为引号，23:109 按 1894 年版改为冒号）。
- 英文：22:76 末尾残留的 “$$A” 已删除。

## Python 示例
```python
import json
from dataclasses import dataclass

@dataclass
class Verse:
    translation: str   # pickthall / sablukov / majian
    corpus: str        # "quran"
    book_index: int    # 章号 1-114
    book_code: str     # "Q002"
    book_name: str
    chapter: int       # == book_index
    verse: int
    text: str

with open("quran_zh.jsonl", encoding="utf-8") as f:
    verses = [Verse(**json.loads(line)) for line in f]
print(len(verses))  # 6236
```
