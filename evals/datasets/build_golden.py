#!/usr/bin/env python3
"""Build the Bible-RAG golden evaluation datasets (golden_en.jsonl, golden_zh.jsonl).

Every item is defined once below (usually as an English/Chinese pair sharing the
same refs). `expected_contexts` are NOT hand-written: they are pulled verbatim
from the corpus jsonl files, and the build fails loudly if any ref is missing
or empty.

Usage:
    python build_golden.py                      # auto-detect data dir (repo ../../data)
    python build_golden.py --data-dir ../../data
    BIBLE_RAG_DATA=/path/to/data python build_golden.py
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# translation code -> candidate relative paths (repo layout first, then dev-box layout)
FILES = {
    "kjv": ["bible/kjv.jsonl", "bible-rag-data/kjv.jsonl", "kjv.jsonl"],
    "cuv": ["bible/cuv.jsonl", "bible-rag-data/cuv.jsonl", "cuv.jsonl"],
    "quran_en": ["quran/quran_en.jsonl", "quran-data/quran_en.jsonl", "quran_en.jsonl"],
    "quran_zh": ["quran/quran_zh.jsonl", "quran-data/quran_zh.jsonl", "quran_zh.jsonl"],
}
LANG_TR = {"en": {"bible": "kjv", "quran": "quran_en"},
           "zh": {"bible": "cuv", "quran": "quran_zh"}}
OTHER = {"en": "zh", "zh": "en"}
CATEGORIES = ["factual", "topical", "verse_lookup", "cross_lingual", "cross_corpus",
              "paraphrase", "negative", "trap", "numbering"]

# ---------------------------------------------------------------------------
# Item definitions
# ---------------------------------------------------------------------------
# I(category, corpus, difficulty, refs, en=(question, answer), zh=(question, answer),
#   en_refs=..., zh_refs=..., behavior=..., notes=...)
# behavior: "answer" (default)
#           "not_found"       -> say it is not in the scriptures, cite nothing
#           "correct_premise" -> point out the misquote / false premise, cite the real verse
ITEMS: list[dict] = []


def I(cat, corpus, diff, refs, en=None, zh=None, *, en_refs=None, zh_refs=None,
      behavior="answer", notes=None):
    ITEMS.append(dict(cat=cat, corpus=corpus, diff=diff, refs=refs, en=en, zh=zh,
                      en_refs=en_refs, zh_refs=zh_refs, behavior=behavior, notes=notes))

# ============================== FACTUAL — Bible ==============================
I("factual", "bible", "easy", ["Gen.6.13", "Gen.6.14", "Gen.6.22"],
  en=("Who built the ark, and who told him to build it?",
      "God told Noah to make an ark of gopher wood, and Noah did all that God commanded him (Gen.6.13-14, Gen.6.22)."),
  zh=("谁建造了方舟？是谁吩咐他造的？",
      "神吩咐挪亚用歌斐木造一只方舟，挪亚就照着神所吩咐的行了（Gen.6.13-14, Gen.6.22）。"))
I("factual", "bible", "easy", ["1Sam.17.49", "1Sam.17.50"],
  en=("How did David defeat Goliath?",
      "David slung a stone that sank into the Philistine's forehead, prevailing over Goliath with a sling and a stone and no sword in his hand (1Sam.17.49-50)."),
  zh=("大卫是怎样打败歌利亚的？",
      "大卫用机弦甩石，打中非利士人的额，石子进入额内；他手中没有刀，只用机弦和石子胜了那非利士人（1Sam.17.49-50）。"))
I("factual", "bible", "easy", ["Matt.2.1", "Luke.2.4", "Luke.2.7"],
  en=("Where was Jesus born?",
      "Jesus was born in Bethlehem of Judaea, the city of David; Mary laid him in a manger because there was no room in the inn (Matt.2.1, Luke.2.4, Luke.2.7)."),
  zh=("耶稣出生在哪里？",
      "耶稣生在犹太的伯利恒，就是大卫的城；马利亚把他放在马槽里，因为客店里没有地方（Matt.2.1, Luke.2.4, Luke.2.7）。"))
I("factual", "bible", "easy", ["Matt.26.34", "Matt.26.75"],
  en=("Which disciple denied Jesus three times before the cock crowed?",
      "Peter. Jesus foretold that before the cock crew he would deny him thrice, and after it happened Peter remembered and wept bitterly (Matt.26.34, Matt.26.75)."),
  zh=("哪个门徒在鸡叫以前三次不认耶稣？",
      "是彼得。耶稣预言鸡叫以先他要三次不认主，事后彼得想起这话就出去痛哭（Matt.26.34, Matt.26.75）。"))
I("factual", "bible", "easy", ["Matt.26.14", "Matt.26.15"],
  en=("Who betrayed Jesus, and for how much?",
      "Judas Iscariot, one of the twelve, agreed with the chief priests to deliver Jesus for thirty pieces of silver (Matt.26.14-15)."),
  zh=("谁出卖了耶稣？得了多少钱？",
      "十二门徒之一的加略人犹大去见祭司长，他们给了他三十块钱，要他把耶稣交给他们（Matt.26.14-15）。"))
I("factual", "bible", "easy", ["Gen.4.8", "Gen.4.9"],
  en=("Who committed the first murder recorded in the Bible?",
      "Cain rose up against his brother Abel in the field and slew him; afterwards he asked, \"Am I my brother's keeper?\" (Gen.4.8-9)."),
  zh=("圣经记载的第一宗谋杀案是谁做的？",
      "该隐在田间起来打他兄弟亚伯，把他杀了；事后耶和华问他，他还说「我岂是看守我兄弟的吗？」（Gen.4.8-9）。"))
I("factual", "bible", "easy", ["Dan.6.16", "Dan.6.22"],
  en=("Who was thrown into the den of lions, and how did he survive?",
      "Daniel was cast into the den of lions at King Darius's command; God sent his angel and shut the lions' mouths (Dan.6.16, Dan.6.22)."),
  zh=("谁被扔进狮子坑？他是怎么活下来的？",
      "但以理被王下令扔在狮子坑中；神差遣使者封住狮子的口，叫狮子不伤他（Dan.6.16, Dan.6.22）。"))
I("factual", "bible", "medium", ["Exod.20.1", "Exod.31.18", "Exod.34.28"],
  en=("How were the Ten Commandments given to Moses?",
      "God spoke these words, and on Mount Sinai gave Moses two tables of testimony, tables of stone written with the finger of God; later the ten commandments were written again on tables (Exod.20.1, Exod.31.18, Exod.34.28)."),
  zh=("十诫是怎样颁给摩西的？",
      "神吩咐这一切的话，在西奈山把两块法版交给摩西，是神用指头写的石版；后来又把十条诫写在版上（Exod.20.1, Exod.31.18, Exod.34.28）。"))
I("factual", "bible", "medium", ["1Kgs.3.9", "1Kgs.3.12"],
  en=("What did Solomon ask God for when God appeared to him in a dream?",
      "Solomon asked for an understanding heart to judge the people and discern between good and bad; God gave him a wise and understanding heart (1Kgs.3.9, 1Kgs.3.12)."),
  zh=("神在梦中向所罗门显现时，所罗门求什么？",
      "所罗门求一颗智慧的心，可以判断百姓、能辨别是非；神就赐他聪明智慧的心（1Kgs.3.9, 1Kgs.3.12）。"))
I("factual", "bible", "easy", ["John.2.9", "John.2.11"],
  en=("What was Jesus' first miracle according to John's Gospel?",
      "At the wedding in Cana of Galilee Jesus turned water into wine; John calls this the beginning of his miracles (John.2.9, John.2.11)."),
  zh=("根据约翰福音，耶稣行的头一件神迹是什么？",
      "在加利利的迦拿婚宴上把水变成酒，这是耶稣所行的头一件神迹（John.2.9, John.2.11）。"))
I("factual", "bible", "easy", ["Gen.7.12", "Gen.7.17"],
  en=("How long did it rain during Noah's flood?",
      "The rain was upon the earth forty days and forty nights (Gen.7.12, Gen.7.17)."),
  zh=("挪亚时代的洪水下了多久的雨？",
      "四十昼夜降大雨在地上（Gen.7.12, Gen.7.17）。"))
I("factual", "bible", "easy", ["Gen.21.2", "Gen.21.3", "Gen.21.5"],
  en=("What was the name of the son Sarah bore to Abraham, and how old was Abraham?",
      "Sarah bore Abraham a son in his old age and he called him Isaac; Abraham was a hundred years old (Gen.21.2-3, Gen.21.5)."),
  zh=("撒拉给亚伯拉罕生的儿子叫什么名字？那时亚伯拉罕多大？",
      "撒拉在亚伯拉罕年老的时候给他生了儿子，起名叫以撒；那时亚伯拉罕一百岁（Gen.21.2-3, Gen.21.5）。"))
I("factual", "bible", "medium", ["Gen.41.15", "Gen.41.16", "Gen.41.29", "Gen.41.30"],
  en=("Who interpreted Pharaoh's dreams, and what did they mean?",
      "Joseph, saying the answer comes from God, interpreted them as seven years of great plenty followed by seven years of famine (Gen.41.15-16, Gen.41.29-30)."),
  zh=("谁为法老解梦？梦是什么意思？",
      "约瑟说解梦在乎神；梦的意思是埃及遍地必来七个大丰年，随后又要来七个荒年（Gen.41.15-16, Gen.41.29-30）。"))
I("factual", "bible", "easy", ["Josh.6.20"],
  en=("What happened to the walls of Jericho?",
      "When the people shouted with a great shout at the sound of the trumpets, the wall fell down flat and they took the city (Josh.6.20)."),
  zh=("耶利哥的城墙后来怎样了？",
      "百姓听见角声便大声呼喊，城墙就塌陷，百姓便上去进城，将城夺取（Josh.6.20）。"))
I("factual", "bible", "easy", ["Judg.16.17"],
  en=("What was the secret of Samson's strength?",
      "He was a Nazarite from birth and no razor had come on his head; if he were shaven his strength would go from him (Judg.16.17)."),
  zh=("参孙力气大的秘密是什么？",
      "他从出母胎就归神作拿细耳人，向来没有用剃头刀剃过头；若剃了头发，力气就离开他（Judg.16.17）。"))
I("factual", "bible", "easy", ["Matt.3.13", "Matt.3.16", "Matt.3.17"],
  en=("Who baptized Jesus, and what happened at his baptism?",
      "John baptized Jesus at the Jordan; the Spirit of God descended like a dove and a voice from heaven said, \"This is my beloved Son\" (Matt.3.13, Matt.3.16-17)."),
  zh=("谁给耶稣施洗？受洗时发生了什么？",
      "约翰在约旦河给耶稣施洗；神的灵仿佛鸽子降下，又有声音从天上说「这是我的爱子」（Matt.3.13, Matt.3.16-17）。"))
I("factual", "bible", "medium", ["Acts.9.3", "Acts.9.4", "Acts.9.5"],
  en=("What happened to Saul on the road to Damascus?",
      "A light from heaven shone round him, he fell to the earth and heard a voice: \"Saul, Saul, why persecutest thou me?\" — it was Jesus (Acts.9.3-5)."),
  zh=("扫罗在往大马色的路上遇到了什么事？",
      "忽然从天上发光四面照着他，他仆倒在地，听见有声音说「扫罗！扫罗！你为甚么逼迫我？」那是耶稣（Acts.9.3-5）。"))
I("factual", "bible", "medium", ["2Kgs.2.11"],
  en=("Which prophet was taken up to heaven in a whirlwind?",
      "Elijah; a chariot of fire and horses of fire parted him and Elisha, and Elijah went up by a whirlwind into heaven (2Kgs.2.11)."),
  zh=("哪位先知乘旋风升天？",
      "以利亚；有火车火马将以利亚和以利沙隔开，以利亚就乘旋风升天去了（2Kgs.2.11）。"))
I("factual", "bible", "easy", ["Luke.19.2", "Luke.19.4"],
  en=("Who climbed a sycomore tree to see Jesus?",
      "Zacchaeus, a rich chief tax collector who was short, ran ahead and climbed a sycomore tree (Luke.19.2, Luke.19.4)."),
  zh=("谁爬上桑树去看耶稣？",
      "撒该，他是税吏长，是个财主；因为身量矮小，就跑到前头爬上桑树（Luke.19.2, Luke.19.4）。"))
I("factual", "bible", "easy", ["Exod.3.2", "Exod.3.4", "Exod.3.5"],
  en=("What did Moses see at the burning bush and what was he told?",
      "The angel of the Lord appeared in a flame of fire out of a bush that burned but was not consumed; God called to Moses and told him to put off his shoes, for the place was holy ground (Exod.3.2, Exod.3.4-5)."),
  zh=("摩西在燃烧的荆棘那里看见什么？神对他说什么？",
      "耶和华的使者从荆棘里火焰中向他显现，荆棘被火烧着却没有烧毁；神呼叫摩西，叫他把脚上的鞋脱下，因为所站之地是圣地（Exod.3.2, Exod.3.4-5）。"))
I("factual", "bible", "easy", ["Gen.25.33", "Gen.25.34"],
  en=("What did Esau sell to Jacob, and for what?",
      "Esau sold his birthright to Jacob for bread and pottage of lentiles (Gen.25.33-34)."),
  zh=("以扫把什么卖给了雅各？换了什么？",
      "以扫把长子的名分卖给雅各，换了饼和红豆汤（Gen.25.33-34）。"))
I("factual", "bible", "easy", ["Matt.14.17", "Matt.14.19", "Matt.14.21"],
  en=("How many loaves and fish did Jesus use to feed the five thousand?",
      "Five loaves and two fishes; about five thousand men, besides women and children, ate (Matt.14.17, Matt.14.19, Matt.14.21)."),
  zh=("耶稣用多少饼和鱼喂饱五千人？",
      "五个饼、两条鱼；吃的人除了妇女孩子，约有五千（Matt.14.17, Matt.14.19, Matt.14.21）。"))
I("factual", "bible", "medium", ["Gen.37.3", "Gen.37.28"],
  en=("Why were Joseph's brothers jealous, and what did they do to him?",
      "Israel loved Joseph more than all his children and made him a coat of many colours; the brothers sold Joseph to the Ishmeelites for twenty pieces of silver (Gen.37.3, Gen.37.28)."),
  zh=("约瑟的哥哥们为什么嫉妒他？他们对他做了什么？",
      "以色列爱约瑟过于众子，给他做了一件彩衣；哥哥们把约瑟从坑里拉上来，以二十舍客勒银子卖给以实玛利人（Gen.37.3, Gen.37.28）。"))

# ============================== FACTUAL — Quran ==============================
I("factual", "quran", "easy", ["Q002.2.34", "Q007.7.12"],
  en=("According to the Quran, who refused to prostrate before Adam, and why?",
      "Iblis refused out of pride; he said, \"I am better than him. Thou createdst me of fire while him Thou didst create of mud\" (Q002.2.34, Q007.7.12)."),
  zh=("根据《古兰经》，谁不肯向阿丹叩头？理由是什么？",
      "易卜劣厮不肯，因为他自大；他说：「我比他优越，你用火造我，用泥造他。」（Q002.2.34, Q007.7.12）"))
I("factual", "quran", "easy", ["Q029.29.14"],
  en=("How long did Noah stay among his people according to the Quran?",
      "A thousand years save fifty years, i.e. 950 years, before the flood engulfed them (Q029.29.14)."),
  zh=("《古兰经》说努哈在他的宗族中逗留了多少年？",
      "九百五十年，之后洪水袭击了他们，因为他们是不义的（Q029.29.14）。"))
I("factual", "quran", "medium", ["Q011.11.44"],
  en=("Where did Noah's ship come to rest according to the Quran?",
      "On (the mount) Al-Judi, after the earth swallowed its water and the water subsided (Q011.11.44)."),
  zh=("《古兰经》说努哈的船停在哪里？",
      "洪水退去后，船停舶在朱迭山上（Q011.11.44）。"))
I("factual", "quran", "medium", ["Q018.18.25"],
  en=("How long did the sleepers of the cave stay in their cave?",
      "Three hundred years, and nine more were added (Q018.18.25)."),
  zh=("山洞里的人在洞中逗留了多久？",
      "三百年，（按阴历算）又加九年（Q018.18.25）。"))
I("factual", "quran", "easy", ["Q002.2.127"],
  en=("Who raised the foundations of the House (the Kaaba) according to the Quran?",
      "Abraham and Ishmael raised the foundations of the House, praying that Allah accept it from them (Q002.2.127)."),
  zh=("《古兰经》说谁树起了天房的基础？",
      "易卜拉欣和易司马仪树起天房的基础，并祈祷主接受他们的敬意（Q002.2.127）。"))
I("factual", "quran", "medium", ["Q027.27.18", "Q027.27.19"],
  en=("What happened when Solomon and his army reached the Valley of the Ants?",
      "An ant warned the others to enter their dwellings lest Solomon and his armies crush them unknowingly; Solomon smiled at her speech and prayed to be thankful (Q027.27.18-19)."),
  zh=("素莱曼和他的大军来到蚁谷时发生了什么？",
      "一个母蚁叫蚂蚁们快进住处，以免被素莱曼的大军不知不觉地践踏；素莱曼听了微笑，并祈求真主使他常常感恩（Q027.27.18-19）。"))
I("factual", "quran", "medium", ["Q019.19.29", "Q019.19.30"],
  en=("In Surah Maryam, what did the infant Jesus say from the cradle?",
      "When Mary pointed to him, he spoke: \"Lo! I am the slave of Allah. He hath given me the Scripture and hath appointed me a Prophet\" (Q019.19.29-30)."),
  zh=("在《麦尔彦》章中，婴儿尔撒在摇篮里说了什么？",
      "麦尔彦指一指婴儿，婴儿说：「我确是真主的仆人，他要把经典赏赐我，要使我做先知。」（Q019.19.29-30）"))
I("factual", "quran", "easy", ["Q002.2.185"],
  en=("In which month was the Quran revealed, and what is commanded in it?",
      "The month of Ramadan; whoever is present should fast the month, while the sick or travellers make up the days later (Q002.2.185)."),
  zh=("《古兰经》在哪个月开始降示？这个月有什么命令？",
      "赖买丹月；在此月中应当斋戒，害病或旅行的人依所缺的日数补斋（Q002.2.185）。"))
I("factual", "quran", "medium", ["Q028.28.7"],
  en=("What was Moses' mother inspired to do with her baby according to the Quran?",
      "To suckle him and, when she feared for him, cast him into the river without fear or grief, with the promise that he would be returned to her and made a messenger (Q028.28.7)."),
  zh=("《古兰经》说真主启示穆萨的母亲怎样处置婴儿？",
      "哺乳他，当她怕他受害时把他投在河里，不要畏惧忧愁；真主应许把他送还她，并任命他为使者（Q028.28.7）。"))
I("factual", "quran", "medium", ["Q021.21.69"],
  en=("What did Allah command the fire when Abraham was thrown into it?",
      "\"O fire, be coolness and peace for Abraham\" (Q021.21.69)."),
  zh=("易卜拉欣被投入火中时，真主对火说了什么？",
      "「火啊！你对易卜拉欣变成凉爽的和平的吧！」（Q021.21.69）"))
I("factual", "quran", "medium", ["Q027.27.20", "Q027.27.22", "Q027.27.23"],
  en=("What news did the hoopoe bring to Solomon?",
      "Solomon noticed the hoopoe was absent; it returned with sure tidings from Sheba of a woman ruling over a people, given abundance of all things, with a mighty throne (Q027.27.20, Q027.27.22-23)."),
  zh=("戴胜给素莱曼带来了什么消息？",
      "素莱曼检阅众鸟时不见戴胜；它回来说从赛百邑带来确实消息：有一个妇人统治一族人，获得万物享受，有一个庞大的宝座（Q027.27.20, Q027.27.22-23）。"))
I("factual", "quran", "medium", ["Q033.33.40"],
  en=("How does the Quran describe Muhammad's position among the prophets?",
      "Muhammad is not the father of any man among them, but the messenger of Allah and the Seal of the Prophets (Q033.33.40)."),
  zh=("《古兰经》怎样描述穆罕默德在众先知中的地位？",
      "穆罕默德不是任何男人的父亲，而是真主的使者和众先知的封印（Q033.33.40）。"))
I("factual", "quran", "medium", ["Q097.97.1", "Q097.97.3"],
  en=("What does Surah 97 say about the Night of Power (Laylat al-Qadr)?",
      "The Quran was revealed on that night, and the Night of Power is better than a thousand months (Q097.97.1, Q097.97.3)."),
  zh=("第97章怎样描述那高贵的夜间？",
      "真主在那高贵的夜间降示了它（《古兰经》），那高贵的夜间胜过一千个月（Q097.97.1, Q097.97.3）。"))
I("factual", "quran", "medium", ["Q020.20.12", "Q007.7.143"],
  en=("What happened when Moses met his Lord according to the Quran?",
      "At the holy valley of Tuwa he was told to take off his shoes (Q020.20.12); at the appointed tryst Moses asked to see Allah and was told \"Thou wilt not see Me\" but to look at the mountain (Q007.7.143)."),
  zh=("《古兰经》怎样记载穆萨与主相遇？",
      "在圣谷「杜瓦」中，主叫他脱掉鞋子（Q020.20.12）；在约定的会期，穆萨求看见主，主说「你不能看见我」，叫他看那座山（Q007.7.143）。"))
I("factual", "quran", "medium", ["Q012.12.15", "Q012.12.23"],
  en=("What did Joseph's brothers do to him, and how did he respond to the woman who tried to seduce him, according to Surah Yusuf?",
      "His brothers agreed to put him in the depth of the pit (Q012.12.15); when the woman of the house bolted the doors and invited him, he said \"I seek refuge in Allah!\" (Q012.12.23)."),
  zh=("根据《优素福》章，哥哥们怎样对待优素福？女主人勾引他时他怎样回应？",
      "哥哥们一致决定把他投入井底（Q012.12.15）；女主人关紧所有的门勾引他时，他说「求真主保祐我！」（Q012.12.23）"))
# ============================== TOPICAL — Bible ==============================
I("topical", "bible", "medium", ["Matt.6.14", "Matt.6.15", "Matt.18.21", "Matt.18.22", "Eph.4.32"],
  en=("What does the Bible teach about forgiving others?",
      "If you forgive men their trespasses your heavenly Father will forgive you, but not if you refuse (Matt.6.14-15); forgive not seven times but seventy times seven (Matt.18.21-22); be kind and forgive one another as God for Christ's sake forgave you (Eph.4.32)."),
  zh=("圣经关于饶恕别人有什么教导？",
      "你们饶恕人的过犯，天父也必饶恕你们，不饶恕人则不然（Matt.6.14-15）；饶恕不是到七次，乃是到七十个七次（Matt.18.21-22）；要以恩慈相待，彼此饶恕，正如神在基督里饶恕了你们（Eph.4.32）。"))
I("topical", "bible", "easy", ["Matt.5.44", "Luke.6.27", "Luke.6.28"],
  en=("How should Christians treat their enemies?",
      "Love your enemies, bless them that curse you, do good to them that hate you, and pray for them that despitefully use you (Matt.5.44, Luke.6.27-28)."),
  zh=("基督徒应当怎样对待仇敌？",
      "要爱你们的仇敌，为那逼迫你们的祷告；恨你们的要待他好，咒诅你们的要为他祝福（Matt.5.44, Luke.6.27-28）。"))
I("topical", "bible", "medium", ["2Cor.9.7", "Matt.6.3", "Acts.20.35"],
  en=("What attitude does the Bible ask for when giving?",
      "Give as you purpose in your heart, not grudgingly or of necessity, for God loves a cheerful giver (2Cor.9.7); give in secret, not letting the left hand know what the right does (Matt.6.3); it is more blessed to give than to receive (Acts.20.35)."),
  zh=("圣经要人以什么态度施舍、捐献？",
      "要随本心所酌定的，不要作难，不要勉强，因为捐得乐意的人是神所喜爱的（2Cor.9.7）；施舍不要叫左手知道右手所做的（Matt.6.3）；施比受更为有福（Acts.20.35）。"))
I("topical", "bible", "medium", ["Rom.12.12", "Jas.5.7", "Jas.1.4"],
  en=("What does the Bible say about patience?",
      "Be patient in tribulation and continue instant in prayer (Rom.12.12); be patient like the husbandman waiting for the fruit of the earth (Jas.5.7); let patience have her perfect work, that ye may be perfect and entire (Jas.1.4)."),
  zh=("圣经关于忍耐说了什么？",
      "在患难中要忍耐，祷告要恒切（Rom.12.12）；要忍耐，像农夫忍耐等候地里宝贵的出产（Jas.5.7）；忍耐也当成功，使你们成全完备（Jas.1.4）。"))
I("topical", "bible", "easy", ["Matt.6.34", "Phil.4.6", "1Pet.5.7"],
  en=("What does the Bible say about worry and anxiety?",
      "Take no thought for the morrow (Matt.6.34); be careful for nothing but bring your requests to God in prayer with thanksgiving (Phil.4.6); cast all your care upon him, for he careth for you (1Pet.5.7)."),
  zh=("圣经关于忧虑和焦虑怎么说？",
      "不要为明天忧虑（Matt.6.34）；应当一无挂虑，只要凡事借着祷告、祈求和感谢，将所要的告诉神（Phil.4.6）；你们要将一切的忧虑卸给神，因为他顾念你们（1Pet.5.7）。"))
I("topical", "bible", "medium", ["Prov.16.18", "Jas.4.6", "Phil.2.3", "Mic.6.8"],
  en=("What does the Bible teach about pride and humility?",
      "Pride goeth before destruction (Prov.16.18); God resisteth the proud but giveth grace unto the humble (Jas.4.6); in lowliness of mind let each esteem other better than themselves (Phil.2.3); walk humbly with thy God (Mic.6.8)."),
  zh=("圣经关于骄傲与谦卑有什么教导？",
      "骄傲在败坏以先（Prov.16.18）；神阻挡骄傲的人，赐恩给谦卑的人（Jas.4.6）；只要存心谦卑，各人看别人比自己强（Phil.2.3）；存谦卑的心，与你的神同行（Mic.6.8）。"))
I("topical", "bible", "easy", ["Exod.20.12", "Eph.6.1", "Eph.6.2"],
  en=("What does the Bible say about honouring parents?",
      "Honour thy father and thy mother, that thy days may be long (Exod.20.12); children, obey your parents in the Lord — the first commandment with promise (Eph.6.1-2)."),
  zh=("圣经关于孝敬父母怎么说？",
      "当孝敬父母，使你的日子在地上得以长久（Exod.20.12）；你们作儿女的，要在主里听从父母，这是第一条带应许的诫命（Eph.6.1-2）。"))
I("topical", "bible", "medium", ["1Cor.13.4", "1Cor.13.7", "1Cor.13.13"],
  en=("How does 1 Corinthians 13 describe love?",
      "It suffers long and is kind, envies not, vaunts not itself (1Cor.13.4); beareth, believeth, hopeth and endureth all things (1Cor.13.7); of faith, hope and charity, the greatest is charity (1Cor.13.13). KJV renders love as \"charity\"."),
  zh=("哥林多前书13章怎样描述爱？",
      "爱是恒久忍耐，又有恩慈；爱是不嫉妒，不自夸（1Cor.13.4）；凡事包容，凡事相信，凡事盼望，凡事忍耐（1Cor.13.7）；信、望、爱这三样，其中最大的是爱（1Cor.13.13）。"))
I("topical", "bible", "easy", ["Heb.11.1", "Heb.11.6"],
  en=("How does the Bible define faith?",
      "Faith is the substance of things hoped for, the evidence of things not seen; without faith it is impossible to please God (Heb.11.1, Heb.11.6)."),
  zh=("圣经怎样定义信心？",
      "信就是所望之事的实底，是未见之事的确据；人非有信，就不能得神的喜悦（Heb.11.1, Heb.11.6）。"))
I("topical", "bible", "medium", ["1Tim.6.10", "Matt.6.24", "Matt.19.24"],
  en=("What does the Bible warn about wealth and money?",
      "The love of money is the root of all evil (1Tim.6.10); ye cannot serve God and mammon (Matt.6.24); it is easier for a camel to go through the eye of a needle than for a rich man to enter the kingdom of God (Matt.19.24)."),
  zh=("圣经对钱财有什么警告？",
      "贪财是万恶之根（1Tim.6.10）；你们不能又事奉神，又事奉玛门（Matt.6.24）；骆驼穿过针的眼，比财主进神的国还容易（Matt.19.24）。"))
I("topical", "bible", "medium", ["Prov.19.17", "Matt.25.40", "Jas.1.27"],
  en=("What does the Bible say about caring for the poor?",
      "He that hath pity upon the poor lendeth unto the Lord (Prov.19.17); whatever you did to the least of my brethren you did unto me (Matt.25.40); pure religion is to visit the fatherless and widows in their affliction (Jas.1.27)."),
  zh=("圣经关于照顾穷人怎么说？",
      "怜悯贫穷的，就是借给耶和华（Prov.19.17）；你们这样行在我这弟兄中一个最小的身上，就是行在我身上了（Matt.25.40）；清洁没有玷污的虔诚，就是看顾在患难中的孤儿寡妇（Jas.1.27）。"))
I("topical", "bible", "medium", ["Eph.4.26", "Jas.1.19", "Jas.1.20"],
  en=("What does the Bible teach about anger?",
      "Be ye angry and sin not; let not the sun go down upon your wrath (Eph.4.26); be swift to hear, slow to speak, slow to wrath, for man's wrath works not God's righteousness (Jas.1.19-20)."),
  zh=("圣经关于发怒有什么教导？",
      "生气却不要犯罪，不可含怒到日落（Eph.4.26）；各人要快快地听，慢慢地说，慢慢地动怒，因为人的怒气并不成就神的义（Jas.1.19-20）。"))
I("topical", "bible", "medium", ["Prov.6.6", "2Thess.3.10", "Col.3.23"],
  en=("What does the Bible say about work and laziness?",
      "Go to the ant, thou sluggard; consider her ways and be wise (Prov.6.6); if any would not work, neither should he eat (2Thess.3.10); whatever you do, do it heartily as to the Lord (Col.3.23)."),
  zh=("圣经关于工作与懒惰怎么说？",
      "懒惰人哪，你去察看蚂蚁的动作，就可得智慧（Prov.6.6）；若有人不肯做工，就不可吃饭（2Thess.3.10）；无论做什么，都要从心里做，像是给主做的（Col.3.23）。"))
I("topical", "bible", "medium", ["Prov.18.21", "Eph.4.29", "Jas.3.5"],
  en=("What does the Bible say about the power of words and the tongue?",
      "Death and life are in the power of the tongue (Prov.18.21); let no corrupt communication proceed out of your mouth (Eph.4.29); the tongue is a little member that boasts great things, like a little fire kindling a great matter (Jas.3.5)."),
  zh=("圣经关于言语和舌头的力量怎么说？",
      "生死在舌头的权下（Prov.18.21）；污秽的言语一句不可出口（Eph.4.29）；舌头是最小的肢体，却能说大话，最小的火能点着最大的树林（Jas.3.5）。"))
I("topical", "bible", "medium", ["Heb.13.2", "Lev.19.34"],
  en=("How should strangers and foreigners be treated according to the Bible?",
      "Be not forgetful to entertain strangers, for some have entertained angels unawares (Heb.13.2); love the stranger as thyself, for ye were strangers in Egypt (Lev.19.34)."),
  zh=("按照圣经，应该如何对待寄居的外人？",
      "不可忘记用爱心接待客旅，曾有接待客旅的，不知不觉就接待了天使（Heb.13.2）；要爱寄居的外人如己，因为你们在埃及地也作过寄居的（Lev.19.34）。"))
I("topical", "bible", "easy", ["Isa.41.10", "Josh.1.9"],
  en=("Which verses tell believers not to be afraid because God is with them?",
      "Fear thou not, for I am with thee; be not dismayed, for I am thy God (Isa.41.10); be strong and of a good courage, for the Lord thy God is with thee whithersoever thou goest (Josh.1.9)."),
  zh=("哪些经文告诉信徒不要惧怕，因为神与他们同在？",
      "你不要害怕，因为我与你同在；不要惊惶，因为我是你的神（Isa.41.10）；你当刚强壮胆，不要惧怕，因为你无论往哪里去，耶和华你的神必与你同在（Josh.1.9）。"))

# ============================== TOPICAL — Quran ==============================
I("topical", "quran", "medium", ["Q002.2.153", "Q002.2.155", "Q002.2.156", "Q103.103.3"],
  en=("What does the Quran teach about patience (sabr) in hardship?",
      "Seek help in patience and prayer; Allah is with the steadfast (Q002.2.153); believers will be tried with fear, hunger and loss, and glad tidings are for the steadfast who say \"Lo! we are Allah's and lo! unto Him we are returning\" (Q002.2.155-156); those saved exhort one another to truth and endurance (Q103.103.3)."),
  zh=("《古兰经》关于在困难中坚忍有什么教导？",
      "你们当借坚忍和礼拜而求佑助，真主确是与坚忍者同在的（Q002.2.153）；真主必以恐怖、饥馑和损失考验你们，你当向坚忍者报喜，他们遭难时说「我们确是真主所有的，我们必定只归依他」（Q002.2.155-156）；得救者以真理相劝，以坚忍相勉（Q103.103.3）。"))
I("topical", "quran", "medium", ["Q002.2.261", "Q002.2.262", "Q002.2.271"],
  en=("What does the Quran say about spending in charity?",
      "Spending in Allah's way is like a grain that grows seven ears each with a hundred grains (Q002.2.261); its reward is kept if not followed by reproach or injury (Q002.2.262); giving openly is good, but giving secretly to the poor is better (Q002.2.271)."),
  zh=("《古兰经》关于施舍有什么说法？",
      "为主道施舍财产的，譬如一粒谷长出七穗，每穗结一百颗（Q002.2.261）；施舍后不责备、不损害受施者，就在主那里得报酬（Q002.2.262）；公开施舍是很好的，秘密地施济贫民对你们更好（Q002.2.271）。"))
I("topical", "quran", "easy", ["Q017.17.23", "Q017.17.24", "Q031.31.14"],
  en=("What does the Quran command regarding parents?",
      "Show kindness to parents; if they reach old age, do not say \"Fie\" to them or repulse them, speak gracious words (Q017.17.23), lower the wing of humility and pray for mercy on them (Q017.17.24); be thankful to Allah and to your parents, whose mother bore him in weakness (Q031.31.14)."),
  zh=("《古兰经》关于对待父母有什么命令？",
      "应当孝敬父母；若他俩老迈，不要对他俩说「呸」，不要喝斥他俩，应当对他俩说有礼貌的话（Q017.17.23）；应当必恭必敬地服侍他俩，并为他俩祈求真主的慈恩（Q017.17.24）；应当感谢真主和父母，母亲在弱上加弱中怀他（Q031.31.14）。"))
I("topical", "quran", "medium", ["Q039.39.53", "Q015.15.56"],
  en=("What does the Quran say to someone who despairs of God's mercy because of their sins?",
      "Despair not of the mercy of Allah, who forgiveth all sins (Q039.39.53); none despaireth of the mercy of his Lord save those who are astray (Q015.15.56)."),
  zh=("对因罪过而对真主的慈恩绝望的人，《古兰经》说什么？",
      "你们对真主的恩惠不要绝望，真主必定赦宥一切罪过（Q039.39.53）；除迷误者外，谁对主的恩惠绝望呢？（Q015.15.56）"))
I("topical", "quran", "medium", ["Q004.4.135", "Q005.5.8", "Q016.16.90"],
  en=("What does the Quran teach about justice?",
      "Stand firm for justice as witnesses for Allah even against yourselves, parents or kin (Q004.4.135); let not hatred of a people make you deal unjustly — be just, that is nearer to piety (Q005.5.8); Allah enjoins justice and kindness (Q016.16.90)."),
  zh=("《古兰经》关于公正有什么教导？",
      "你们当维护公道，当为真主作证，即使不利于你们自己、父母和至亲（Q004.4.135）；绝不要因为怨恨一伙人而不公道，公道是最近于敬畏的（Q005.5.8）；真主命人公平、行善（Q016.16.90）。"))
I("topical", "quran", "medium", ["Q003.3.134", "Q024.24.22", "Q042.42.40"],
  en=("What does the Quran say about forgiving people who wrong you?",
      "The righteous control their wrath and pardon men (Q003.3.134); let them forgive and show indulgence — do you not love that Allah should forgive you? (Q024.24.22); whoever pardons and makes amends, his wage is the affair of Allah (Q042.42.40)."),
  zh=("《古兰经》关于宽恕冒犯你的人怎么说？",
      "敬畏者抑怒，并且恕人（Q003.3.134）；叫他们原谅、宽恕吧，难道你们不愿真主赦宥你们吗？（Q024.24.22）；谁愿恕饶而且和解，真主必报酬谁（Q042.42.40）。"))
I("topical", "quran", "medium", ["Q093.93.9", "Q004.4.10", "Q107.107.2"],
  en=("How does the Quran tell believers to treat orphans?",
      "Do not oppress the orphan (Q093.93.9); those who devour the wealth of orphans wrongfully swallow fire into their bellies (Q004.4.10); denying religion is linked to repelling the orphan (Q107.107.2)."),
  zh=("《古兰经》怎样要求信士对待孤儿？",
      "至于孤儿，你不要压迫他（Q093.93.9）；不义地吃孤儿财产的人，只是把火吃进肚里（Q004.4.10）；否认报应者就是那个呵斥孤儿的人（Q107.107.2）。"))
I("topical", "quran", "easy", ["Q014.14.7", "Q031.31.12"],
  en=("What does the Quran say about gratitude?",
      "If you give thanks, Allah will give you more, but if you are thankless His punishment is dire (Q014.14.7); whoever gives thanks does so for the good of his own soul (Q031.31.12)."),
  zh=("《古兰经》关于感恩怎么说？",
      "如果你们感谢，我誓必对你们恩上加恩；如果你们辜负，我的刑罚确是严厉的（Q014.14.7）；谁感谢，谁自受其益（Q031.31.12）。"))
I("topical", "quran", "easy", ["Q002.2.183", "Q002.2.184", "Q002.2.185"],
  en=("What does the Quran say about fasting?",
      "Fasting is prescribed for believers as it was for those before them, that they may ward off evil (Q002.2.183); the sick or travellers make up the days, and those who can afford it may feed a needy person (Q002.2.184); the fast is in Ramadan, the month the Quran was revealed (Q002.2.185)."),
  zh=("《古兰经》关于斋戒怎么说？",
      "斋戒已成为你们的定制，正如它曾为前人的定制一样，以便你们敬畏（Q002.2.183）；害病或旅行的人当依所缺的日数补斋，能斋而不斋者应纳罚赎（Q002.2.184）；赖买丹月中，《古兰经》开始降示，在此月中应当斋戒（Q002.2.185）。"))
I("topical", "quran", "medium", ["Q005.5.90", "Q002.2.219"],
  en=("What is the Quran's ruling on wine and gambling?",
      "Strong drink and games of chance are an infamy of Satan's handiwork, so leave them (Q005.5.90); in both is great sin and some utility, but the sin is greater than the usefulness (Q002.2.219)."),
  zh=("《古兰经》对饮酒和赌博的规定是什么？",
      "饮酒、赌博是恶魔的行为，你们当远离（Q005.5.90）；这两件事都包含着大罪，对于世人都有许多利益，而其罪过比利益还大（Q002.2.219）。"))
I("topical", "quran", "easy", ["Q049.49.13"],
  en=("What does the Quran say about the diversity of nations and tribes?",
      "Mankind was created from male and female and made into nations and tribes that they may know one another; the noblest in Allah's sight is the best in conduct (Q049.49.13)."),
  zh=("《古兰经》关于民族和宗族的多样性怎么说？",
      "真主从一男一女创造人类，使你们成为许多民族和宗族，以便你们互相认识；在真主看来，你们中最尊贵者是最敬畏者（Q049.49.13）。"))
I("topical", "quran", "medium", ["Q002.2.256", "Q010.10.99"],
  en=("What does the Quran say about forcing people into religion?",
      "There is no compulsion in religion (Q002.2.256); had your Lord willed, all on earth would have believed — would you compel mankind to become believers? (Q010.10.99)."),
  zh=("《古兰经》关于强迫人信教怎么说？",
      "对于宗教，绝无强迫（Q002.2.256）；假若你的主意欲，大地上所有的人都会信道，难道你要强迫众人都做信士吗？（Q010.10.99）"))
I("topical", "quran", "medium", ["Q002.2.43", "Q011.11.114", "Q002.2.238"],
  en=("What does the Quran command about prayer (salah)?",
      "Establish worship and pay the poor-due (Q002.2.43); establish worship at the two ends of the day and in some watches of the night, for good deeds annul ill deeds (Q011.11.114); be guardians of the prayers and the midmost prayer (Q002.2.238)."),
  zh=("《古兰经》关于礼拜有什么命令？",
      "你们当谨守拜功，完纳天课（Q002.2.43）；你当在白昼的两端和初更时谨守拜功，善行必能消除恶行（Q011.11.114）；你们当谨守许多拜功和最贵的拜功（Q002.2.238）。"))
# ============================== VERSE LOOKUP — Bible ==============================
I("verse_lookup", "bible", "easy", ["John.3.16"],
  en=("What does John 3:16 say?",
      "\"For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life\" (John.3.16)."),
  zh=("约翰福音3章16节说什么？",
      "「神爱世人，甚至将他的独生子赐给他们，叫一切信他的，不致灭亡，反得永生。」（John.3.16）"))
I("verse_lookup", "bible", "easy", ["John.1.1"],
  en=("Quote the first verse of the Gospel of John.",
      "\"In the beginning was the Word, and the Word was with God, and the Word was God\" (John.1.1)."),
  zh=("请引用约翰福音的第一节经文。",
      "「太初有道，道与神同在，道就是神。」（John.1.1）"))
I("verse_lookup", "bible", "easy", ["Phil.4.13"],
  en=("Which verse says \"I can do all things through Christ\"?",
      "Philippians 4:13: \"I can do all things through Christ which strengtheneth me\" (Phil.4.13)."),
  zh=("「我靠着那加给我力量的，凡事都能做」出自哪里？",
      "腓立比书4章13节：「我靠着那加给我力量的，凡事都能做。」（Phil.4.13）"))
I("verse_lookup", "bible", "medium", ["Rom.3.23", "Rom.6.23"],
  en=("What do Romans 3:23 and 6:23 say about sin?",
      "All have sinned and come short of the glory of God (Rom.3.23); the wages of sin is death, but the gift of God is eternal life through Jesus Christ our Lord (Rom.6.23)."),
  zh=("罗马书3章23节和6章23节关于罪说了什么？",
      "世人都犯了罪，亏缺了神的荣耀（Rom.3.23）；罪的工价乃是死，惟有神的恩赐，在我们的主基督耶稣里，乃是永生（Rom.6.23）。"))
I("verse_lookup", "bible", "easy", ["John.14.6"],
  en=("Where does Jesus say \"I am the way, the truth, and the life\"?",
      "John 14:6: \"I am the way, the truth, and the life: no man cometh unto the Father, but by me\" (John.14.6)."),
  zh=("耶稣在哪里说「我就是道路、真理、生命」？",
      "约翰福音14章6节：「我就是道路、真理、生命；若不藉着我，没有人能到父那里去。」（John.14.6）"))
I("verse_lookup", "bible", "easy", ["Ps.46.10"],
  en=("Which psalm says \"Be still, and know that I am God\"?",
      "Psalm 46:10: \"Be still, and know that I am God: I will be exalted among the heathen\" (Ps.46.10)."),
  zh=("哪一篇诗篇说「你们要休息，要知道我是神」？",
      "诗篇46篇10节：「你们要休息，要知道我是神！我必在外邦中被尊崇。」（Ps.46.10）"))
I("verse_lookup", "bible", "easy", ["Prov.3.5", "Prov.3.6"],
  en=("What does Proverbs 3:5-6 say?",
      "\"Trust in the LORD with all thine heart; and lean not unto thine own understanding. In all thy ways acknowledge him, and he shall direct thy paths\" (Prov.3.5-6)."),
  zh=("箴言3章5至6节说什么？",
      "「你要专心仰赖耶和华，不可倚靠自己的聪明，在你一切所行的事上都要认定他，他必指引你的路。」（Prov.3.5-6）"))
I("verse_lookup", "bible", "easy", ["Eccl.3.1"],
  en=("Which verse says there is a time for everything?",
      "Ecclesiastes 3:1: \"To every thing there is a season, and a time to every purpose under the heaven\" (Eccl.3.1)."),
  zh=("哪节经文说凡事都有定时？",
      "传道书3章1节：「凡事都有定期，天下万务都有定时。」（Eccl.3.1）"))
I("verse_lookup", "bible", "easy", ["Isa.40.31"],
  en=("Which verse promises that those who wait on the Lord will mount up with wings as eagles?",
      "Isaiah 40:31: they that wait upon the LORD shall renew their strength; they shall mount up with wings as eagles; they shall run, and not be weary (Isa.40.31)."),
  zh=("哪节经文应许等候耶和华的人必如鹰展翅上腾？",
      "以赛亚书40章31节：「但那等候耶和华的必重新得力。他们必如鹰展翅上腾；他们奔跑却不困倦，行走却不疲乏。」（Isa.40.31）"))
I("verse_lookup", "bible", "medium", ["Jer.29.11"],
  en=("What does Jeremiah 29:11 say about God's plans?",
      "\"For I know the thoughts that I think toward you, saith the LORD, thoughts of peace, and not of evil, to give you an expected end\" (Jer.29.11)."),
  zh=("耶利米书29章11节关于神的意念说了什么？",
      "耶和华说：「我知道我向你们所怀的意念是赐平安的意念，不是降灾祸的意念，要叫你们末后有指望。」（Jer.29.11）"))
I("verse_lookup", "bible", "easy", ["Matt.7.7"],
  en=("Which verse says \"Ask, and it shall be given you\"?",
      "Matthew 7:7: \"Ask, and it shall be given you; seek, and ye shall find; knock, and it shall be opened unto you\" (Matt.7.7)."),
  zh=("「你们祈求，就给你们」出自哪节经文？",
      "马太福音7章7节：「你们祈求，就给你们；寻找，就寻见；叩门，就给你们开门。」（Matt.7.7）"))
I("verse_lookup", "bible", "easy", ["Matt.11.28"],
  en=("Where does Jesus invite the weary to come to him for rest?",
      "Matthew 11:28: \"Come unto me, all ye that labour and are heavy laden, and I will give you rest\" (Matt.11.28)."),
  zh=("耶稣在哪里邀请劳苦的人到他那里得安息？",
      "马太福音11章28节：「凡劳苦担重担的人可以到我这里来，我就使你们得安息。」（Matt.11.28）"))
I("verse_lookup", "bible", "easy", ["Rom.8.28"],
  en=("Which verse says all things work together for good?",
      "Romans 8:28: all things work together for good to them that love God, to them who are the called according to his purpose (Rom.8.28)."),
  zh=("哪节经文说万事都互相效力？",
      "罗马书8章28节：「我们晓得万事都互相效力，叫爱神的人得益处，就是按他旨意被召的人。」（Rom.8.28）"))
I("verse_lookup", "bible", "medium", ["Eph.2.8", "Eph.2.9"],
  en=("Which passage says we are saved by grace through faith, not of works?",
      "Ephesians 2:8-9: by grace are ye saved through faith, and that not of yourselves: it is the gift of God; not of works, lest any man should boast (Eph.2.8-9)."),
  zh=("哪段经文说我们得救是本乎恩、也因着信，不是出于行为？",
      "以弗所书2章8至9节：你们得救是本乎恩，也因着信；这并不是出于自己，乃是神所赐的；也不是出于行为，免得有人自夸（Eph.2.8-9）。"))
I("verse_lookup", "bible", "easy", ["Gen.1.3"],
  en=("What were God's first spoken words in Genesis?",
      "\"Let there be light: and there was light\" (Gen.1.3)."),
  zh=("创世记中神所说的第一句话是什么？",
      "「要有光」，就有了光（Gen.1.3）。"))
I("verse_lookup", "bible", "medium", ["Lev.19.18", "Matt.22.39"],
  en=("Where does the command \"love thy neighbour as thyself\" appear?",
      "It is first given in Leviticus 19:18 and quoted by Jesus as the second great commandment in Matthew 22:39 (Lev.19.18, Matt.22.39)."),
  zh=("「爱人如己」这条命令出现在哪里？",
      "最早见于利未记19章18节，耶稣在马太福音22章39节引用为第二条最大的诫命（Lev.19.18, Matt.22.39）。"))
I("verse_lookup", "bible", "medium", ["Ruth.1.16"],
  en=("What did Ruth say to Naomi when she refused to leave her?",
      "\"Whither thou goest, I will go; and where thou lodgest, I will lodge: thy people shall be my people, and thy God my God\" (Ruth.1.16)."),
  zh=("路得不肯离开拿俄米时对她说了什么？",
      "「你往哪里去，我也往那里去；你在哪里住宿，我也在那里住宿；你的国就是我的国，你的神就是我的神。」（Ruth.1.16）"))
I("verse_lookup", "bible", "easy", ["Prov.1.7"],
  en=("Which verse says the fear of the Lord is the beginning of knowledge?",
      "Proverbs 1:7: the fear of the LORD is the beginning of knowledge, but fools despise wisdom and instruction (Prov.1.7)."),
  zh=("哪节经文说敬畏耶和华是知识的开端？",
      "箴言1章7节：「敬畏耶和华是知识的开端；愚妄人藐视智慧和训诲。」（Prov.1.7）"))
I("verse_lookup", "bible", "medium", ["Matt.6.9", "Matt.6.10", "Matt.6.11", "Matt.6.12", "Matt.6.13"],
  en=("What are the words of the Lord's Prayer in Matthew?",
      "\"Our Father which art in heaven, Hallowed be thy name. Thy kingdom come. Thy will be done in earth, as it is in heaven. Give us this day our daily bread. And forgive us our debts, as we forgive our debtors. And lead us not into temptation, but deliver us from evil...\" (Matt.6.9-13)."),
  zh=("马太福音中的主祷文是怎样的？",
      "「我们在天上的父：愿人都尊你的名为圣。愿你的国降临；愿你的旨意行在地上，如同行在天上。我们日用的饮食，今日赐给我们。免我们的债，如同我们免了人的债。不叫我们遇见试探；救我们脱离凶恶……」（Matt.6.9-13）"))
I("verse_lookup", "bible", "easy", ["Matt.28.19"],
  en=("What is the Great Commission?",
      "\"Go ye therefore, and teach all nations, baptizing them in the name of the Father, and of the Son, and of the Holy Ghost\" (Matt.28.19)."),
  zh=("什么是大使命？",
      "「你们要去，使万民作我的门徒，奉父、子、圣灵的名给他们施洗。」（Matt.28.19）"))
I("verse_lookup", "bible", "easy", ["Mic.6.8"],
  en=("What does Micah 6:8 say the Lord requires?",
      "To do justly, to love mercy, and to walk humbly with thy God (Mic.6.8)."),
  zh=("弥迦书6章8节说耶和华向人所要的是什么？",
      "行公义，好怜悯，存谦卑的心，与你的神同行（Mic.6.8）。"))

# ============================== VERSE LOOKUP — Quran ==============================
I("verse_lookup", "quran", "easy", ["Q002.2.255"],
  en=("What does Ayat al-Kursi (the Throne Verse) say?",
      "Allah! There is no deity save Him, the Alive, the Eternal; neither slumber nor sleep overtaketh Him; His throne includeth the heavens and the earth and He is never weary of preserving them (Q002.2.255)."),
  zh=("宝座经（库尔西经文）说什么？",
      "真主，除他外绝无应受崇拜的，他是永生不灭的，是维护万物的；瞌睡不能侵犯他，睡眠不能克服他；他的知觉包罗天地，天地的维持不能使他疲倦（Q002.2.255）。"))
I("verse_lookup", "quran", "easy", ["Q002.2.256"],
  en=("Which verse says \"There is no compulsion in religion\"?",
      "Surah 2:256: \"There is no compulsion in religion. The right direction is henceforth distinct from error\" (Q002.2.256)."),
  zh=("「对于宗教，绝无强迫」出自哪节经文？",
      "第2章第256节：「对于宗教，绝无强迫；因为正邪确已分明了。」（Q002.2.256）"))
I("verse_lookup", "quran", "medium", ["Q002.2.286"],
  en=("Which Quran verse says Allah does not burden a soul beyond its capacity?",
      "Surah 2:286: \"Allah tasketh not a soul beyond its scope\", followed by the prayer \"Our Lord! Condemn us not if we forget, or miss the mark\" (Q002.2.286)."),
  zh=("哪节《古兰经》说真主只依人的能力而加以责成？",
      "第2章第286节：「真主只依各人的能力而加以责成」，随后是祈祷「我们的主啊！求你不要惩罚我们，如果我们遗忘或错误」（Q002.2.286）。"))
I("verse_lookup", "quran", "easy", ["Q112.112.1", "Q112.112.2", "Q112.112.3", "Q112.112.4"],
  en=("What does Surah al-Ikhlas say?",
      "\"Say: He is Allah, the One! Allah, the eternally Besought of all! He begetteth not nor was begotten. And there is none comparable unto Him\" (Q112.112.1-4)."),
  zh=("《忠诚》章（第112章）说什么？",
      "「你说：他是真主，是独一的主；真主是万物所仰赖的；他没有生产，也没有被生产；没有任何物可以做他的匹敌。」（Q112.112.1-4）"))
I("verse_lookup", "quran", "easy", ["Q003.3.185"],
  en=("Which verse says every soul will taste death?",
      "Surah 3:185: every soul will taste of death; on the Day of Resurrection you will be paid only that which you have fairly earned; the life of this world is but comfort of illusion (Q003.3.185)."),
  zh=("哪节经文说人人都要尝死的滋味？",
      "第3章第185节：人人都要尝死的滋味；在复活日你们才得享受你们的完全的报酬；今世的生活只是虚幻的享受（Q003.3.185）。"))
I("verse_lookup", "quran", "medium", ["Q024.24.35"],
  en=("What is the Verse of Light?",
      "Surah 24:35: \"Allah is the Light of the heavens and the earth\", likened to a niche wherein is a lamp in a glass like a shining star, light upon light (Q024.24.35)."),
  zh=("光明经文说什么？",
      "第24章第35节：真主是天地的光明，他的光明像一座灯台，那座灯台上有一盏明灯，那盏明灯在一个玻璃罩里，那个玻璃罩仿佛一颗灿烂的明星……光上加光（Q024.24.35）。"))
I("verse_lookup", "quran", "easy", ["Q055.55.13"],
  en=("Which refrain is repeated throughout Surah ar-Rahman?",
      "\"Which is it, of the favours of your Lord, that ye deny?\" (Q055.55.13)."),
  zh=("《至仁主》章中反复出现的叠句是什么？",
      "「你们究竟否认你们的主的哪一件恩典呢？」（Q055.55.13）"))
I("verse_lookup", "quran", "easy", ["Q094.94.5", "Q094.94.6"],
  en=("Which verses say that with hardship comes ease?",
      "Surah 94:5-6: \"But lo! with hardship goeth ease, Lo! with hardship goeth ease\" (Q094.94.5-6)."),
  zh=("哪节经文说艰难与容易同在？",
      "第94章第5至6节：「与艰难相伴的，确是容易；与艰难相伴的，确是容易。」（Q094.94.5-6）"))
I("verse_lookup", "quran", "easy", ["Q001.1.6", "Q001.1.7"],
  en=("What guidance is asked for at the end of al-Fatiha?",
      "\"Show us the straight path, the path of those whom Thou hast favoured; not (the path) of those who earn Thine anger nor of those who go astray\" (Q001.1.6-7)."),
  zh=("《开端》章结尾祈求什么引导？",
      "「求你引导我们上正路，你所祐助者的路，不是受谴怒者的路，也不是迷误者的路。」（Q001.1.6-7）"))
I("verse_lookup", "quran", "medium", ["Q096.96.1"],
  en=("What is traditionally considered the first revealed word of the Quran, and where is it?",
      "\"Read: In the name of thy Lord who createth\" — the opening of Surah 96 (Q096.96.1). The retrieved text supports the verse wording; the claim that it was first revealed is tradition, not stated in the verse."),
  zh=("传统上认为《古兰经》最早降示的经文是什么？在哪里？",
      "「你应当奉你的创造主的名义而宣读」，即第96章开头（Q096.96.1）。经文本身支持其措辞；“最早降示”是传统说法，经文本身未提及。"))
# ============================== CROSS-LINGUAL ==============================
# The question uses vocabulary from the OTHER language's tradition (or a gloss that does not
# match the native translation wording). parallel_contexts holds the other-language text so
# cross-lingual retrieval (e.g. zh query -> kjv chunk) can also be scored.
I("cross_lingual", "bible", "easy", ["John.11.35"],
  en=("Which verse is rendered in Chinese as 「耶稣哭了」, and what does it say in English?",
      "John 11:35, \"Jesus wept\" (John.11.35)."),
  zh=("英文圣经里 \"Jesus wept\" 这节经文中文怎么说？出自哪里？",
      "约翰福音11章35节：「耶稣哭了。」（John.11.35）"))
I("cross_lingual", "bible", "easy", ["1John.4.8", "1John.4.16"],
  en=("Where is the Chinese phrase 「神就是爱」 found in the Bible?",
      "1 John 4:8 and 4:16: \"God is love\" (1John.4.8, 1John.4.16)."),
  zh=("\"God is love\" 这句话出自圣经哪里？",
      "约翰一书4章8节和16节：「神就是爱」（1John.4.8, 1John.4.16）。"))
I("cross_lingual", "bible", "medium", ["Matt.6.33"],
  en=("A Chinese friend quoted 「你们要先求他的国和他的义」. Which verse is that in English?",
      "Matthew 6:33: \"But seek ye first the kingdom of God, and his righteousness; and all these things shall be added unto you\" (Matt.6.33)."),
  zh=("英文常说 \"Seek ye first the kingdom of God\"，对应哪节经文？",
      "马太福音6章33节：「你们要先求他的国和他的义，这些东西都要加给你们了。」（Matt.6.33）"))
I("cross_lingual", "bible", "easy", ["John.8.32"],
  en=("What verse is 「你们必晓得真理，真理必叫你们得以自由」?",
      "John 8:32: \"And ye shall know the truth, and the truth shall make you free\" (John.8.32)."),
  zh=("\"The truth shall make you free\" 出自哪里？",
      "约翰福音8章32节：「你们必晓得真理，真理必叫你们得以自由。」（John.8.32）"))
I("cross_lingual", "bible", "easy", ["Matt.5.9"],
  en=("Which beatitude is 「使人和睦的人有福了」?",
      "Matthew 5:9: \"Blessed are the peacemakers: for they shall be called the children of God\" (Matt.5.9)."),
  zh=("\"Blessed are the peacemakers\" 是哪一句八福？",
      "马太福音5章9节：「使人和睦的人有福了！因为他们必称为神的儿子。」（Matt.5.9）"))
I("cross_lingual", "bible", "hard", ["1Cor.13.4"],
  en=("Where does the Bible say 「爱是恒久忍耐，又有恩慈」 (\"love is patient and kind\")?",
      "1 Corinthians 13:4. Note the KJV says \"Charity suffereth long, and is kind\" — it uses the word charity rather than love (1Cor.13.4)."),
  zh=("英文 \"Charity suffereth long, and is kind\" 里的 charity 是什么意思？出自哪里？",
      "出自哥林多前书13章4节，KJV 的 charity 在和合本中译作「爱」：「爱是恒久忍耐，又有恩慈」（1Cor.13.4）。"),
  notes="KJV 'charity' vs modern 'love' / CUV 爱 — lexical mismatch")
I("cross_lingual", "bible", "easy", ["Exod.20.13"],
  en=("Which commandment is 「不可杀人」?",
      "The sixth commandment, Exodus 20:13: \"Thou shalt not kill\" (Exod.20.13)."),
  zh=("\"Thou shalt not kill\" 是哪一条诫命？",
      "出埃及记20章13节：「不可杀人。」（Exod.20.13）"))
I("cross_lingual", "bible", "medium", ["2Cor.12.9"],
  en=("Which verse says 「我的恩典够你用的，因为我的能力是在人的软弱上显得完全」?",
      "2 Corinthians 12:9: \"My grace is sufficient for thee: for my strength is made perfect in weakness\" (2Cor.12.9)."),
  zh=("\"My grace is sufficient for thee\" 出自哪里？",
      "哥林多后书12章9节：「我的恩典够你用的，因为我的能力是在人的软弱上显得完全。」（2Cor.12.9）"))
I("cross_lingual", "bible", "medium", ["Eccl.1.2"],
  en=("Where is 「虚空的虚空，凡事都是虚空」 from?",
      "Ecclesiastes 1:2: \"Vanity of vanities, saith the Preacher... all is vanity\" (Eccl.1.2)."),
  zh=("\"Vanity of vanities; all is vanity\" 出自哪里？",
      "传道书1章2节：「虚空的虚空，虚空的虚空，凡事都是虚空。」（Eccl.1.2）"))
I("cross_lingual", "bible", "easy", ["Ps.119.105"],
  en=("Which verse is 「你的话是我脚前的灯，是我路上的光」?",
      "Psalm 119:105: \"Thy word is a lamp unto my feet, and a light unto my path\" (Ps.119.105)."),
  zh=("\"Thy word is a lamp unto my feet\" 出自哪里？",
      "诗篇119篇105节：「你的话是我脚前的灯，是我路上的光。」（Ps.119.105）"))
I("cross_lingual", "quran", "medium", ["Q050.50.16"],
  en=("Which Quran verse is 「我比他的命脉还近于他」 (closer than the jugular vein)?",
      "Surah 50:16: \"We are nearer to him than his jugular vein\" (Q050.50.16)."),
  zh=("\"We are nearer to him than his jugular vein\" 是哪节经文？",
      "第50章第16节：「我比他的命脉还近于他。」（Q050.50.16）"))
I("cross_lingual", "quran", "medium", ["Q013.13.11"],
  en=("Which verse says (in Chinese) 「真主必定不变更任何民众的情况，直到他们变更自己的情况」?",
      "Surah 13:11: \"Allah changeth not the condition of a folk until they (first) change that which is in their hearts\" (Q013.13.11)."),
  zh=("\"Allah changeth not the condition of a folk until they first change that which is in their hearts\" 是哪节经文？",
      "第13章第11节：真主必定不变更任何民众的情况，直到他们变更自己的情况（Q013.13.11）。"))
I("cross_lingual", "quran", "medium", ["Q002.2.152"],
  en=("Which Quran verse is 「你们当记忆我……我就记忆你们」?",
      "Surah 2:152: \"Therefore remember Me, I will remember you. Give thanks to Me, and reject not Me\" (Q002.2.152)."),
  zh=("\"Remember Me, I will remember you\" 是哪节经文？",
      "第2章第152节：「故你们当记忆我，（你们记忆我），我就记忆你们；你们当感谢我；不要孤负我。」（Q002.2.152）"))
I("cross_lingual", "quran", "hard", ["Q093.93.7"],
  en=("Which verse in Surah ad-Duha says, in Ma Jian's Chinese, that Allah found the Prophet 「徘徊歧途」 and guided him?",
      "Surah 93:7: \"Did He not find thee wandering and direct (thee)?\" (Q093.93.7)."),
  zh=("\"Did He not find thee wandering and direct thee?\" 是哪节经文？",
      "第93章第7节：他曾发现你徘徊歧途，而把你引入正路（Q093.93.7）。"))
I("cross_lingual", "quran", "medium", ["Q093.93.4"],
  en=("Which verse says 「后世于你，确比今世更好」?",
      "Surah 93:4: \"And verily the latter portion will be better for thee than the former\" (Q093.93.4)."),
  zh=("\"The latter portion will be better for thee than the former\" 是哪节经文？",
      "第93章第4节：「后世于你，确比今世更好。」（Q093.93.4）"))
I("cross_lingual", "quran", "hard", ["Q109.109.6"],
  en=("Surah 109:6 in Ma Jian's Chinese reads 「你们有你们的报应，我也有我的报应」. What does the English say?",
      "Pickthall renders it \"Unto you your religion, and unto me my religion\" — Ma Jian translates the word as 报应 (recompense) rather than religion (Q109.109.6)."),
  zh=("\"Unto you your religion, and unto me my religion\" 中文译本怎么说？",
      "马坚译为「你们有你们的报应，我也有我的报应。」英译作 religion，中译作「报应」（Q109.109.6）。"),
  notes="translation divergence: din = religion (Pickthall) vs 报应 (Ma Jian)")

# ============================== CROSS-CORPUS ==============================
I("cross_corpus", "both", "medium", ["Gen.7.12", "Gen.8.4", "Q011.11.44", "Q029.29.14"],
  en=("Compare the flood story of Noah in the Bible and the Quran.",
      "Both tell of a flood and the ark resting on a mountain: the Bible has forty days of rain and the ark resting on the mountains of Ararat (Gen.7.12, Gen.8.4); the Quran says the ship came to rest on al-Judi (Q011.11.44) and that Noah stayed among his people 950 years (Q029.29.14)."),
  zh=("比较圣经和《古兰经》中挪亚（努哈）洪水的记载。",
      "两者都讲洪水和方舟停在山上：圣经说四十昼夜降大雨，方舟停在亚拉腊山上（Gen.7.12, Gen.8.4）；《古兰经》说船停在朱迭山上（Q011.11.44），努哈在族中逗留九百五十年（Q029.29.14）。"))
I("cross_corpus", "both", "medium", ["Exod.14.21", "Exod.14.28", "Q026.26.63", "Q010.10.90", "Q010.10.92"],
  en=("How do the Bible and the Quran describe the parting of the sea and Pharaoh's fate?",
      "In Exodus Moses stretched out his hand, the Lord divided the waters and the sea covered Pharaoh's host (Exod.14.21, Exod.14.28); in the Quran Moses struck the sea with his staff and it parted (Q026.26.63), Pharaoh declared belief as he drowned and his body was preserved as a sign (Q010.10.90, Q010.10.92)."),
  zh=("圣经和《古兰经》怎样记载分海和法老的结局？",
      "出埃及记说摩西向海伸杖，耶和华使水分开，水回流淹没了法老的全军（Exod.14.21, Exod.14.28）；《古兰经》说穆萨用手杖击海，海就分开（Q026.26.63），法老临溺时声称信道，真主保全他的尸体作为迹象（Q010.10.90, Q010.10.92）。"))
I("cross_corpus", "both", "medium", ["Luke.1.30", "Luke.1.31", "Luke.1.34", "Q019.19.19", "Q019.19.20"],
  en=("Compare the annunciation to Mary in the Bible and the Quran.",
      "In Luke the angel tells Mary she will conceive and bear a son named Jesus, and she asks how, since she knows not a man (Luke.1.30-31, Luke.1.34); in the Quran the messenger says he will bestow a faultless son, and Mary asks how, when no mortal has touched her (Q019.19.19-20)."),
  zh=("比较圣经和《古兰经》中天使向马利亚（麦尔彦）报信的记载。",
      "路加福音中天使说她要怀孕生子，起名叫耶稣，马利亚问：「我没有出嫁，怎么有这事呢？」（Luke.1.30-31, Luke.1.34）；《古兰经》中使者说要赏赐她一个纯洁的儿子，麦尔彦说：「任何人没有接触过我，我又不是失节的，我怎么会有儿子呢？」（Q019.19.19-20）"))
I("cross_corpus", "both", "hard", ["Gen.22.2", "Gen.22.12", "Gen.22.13", "Q037.37.102", "Q037.37.107"],
  en=("How do the Bible and the Quran describe Abraham's willingness to sacrifice his son?",
      "In Genesis God tells Abraham to offer Isaac, then stops him and a ram is offered instead (Gen.22.2, Gen.22.12-13); in the Quran Abraham tells his son of a dream that he must sacrifice him, the son submits, and he is ransomed with a tremendous victim (Q037.37.102, Q037.37.107). The Quran passage does not name the son."),
  zh=("圣经和《古兰经》怎样记载亚伯拉罕（易卜拉欣）献子？",
      "创世记中神叫亚伯拉罕献以撒，后来拦阻他，以公羊代替（Gen.22.2, Gen.22.12-13）；《古兰经》中易卜拉欣告诉儿子梦见要宰他，儿子顺从，真主以一个大牺牲赎了他（Q037.37.102, Q037.37.107）。《古兰经》这段没有点名是哪个儿子。"))
I("cross_corpus", "both", "medium", ["Gen.2.2", "Exod.20.11", "Q007.7.54"],
  en=("Do the Bible and the Quran both say the world was created in six days?",
      "Yes. The Bible says God made heaven and earth in six days and rested on the seventh (Gen.2.2, Exod.20.11); the Quran says Allah created the heavens and the earth in six days and then mounted the Throne (Q007.7.54), without mentioning rest."),
  zh=("圣经和《古兰经》是否都说世界是六天造成的？",
      "是的。圣经说耶和华六日造天地，第七日歇了工（Gen.2.2, Exod.20.11）；《古兰经》说真主在六日内创造了天地，然后升上宝座（Q007.7.54），没有提到安息。"))
I("cross_corpus", "both", "medium", ["Gen.3.6", "Gen.3.7", "Q007.7.22", "Q020.20.121"],
  en=("Compare what happened when Adam and his wife ate from the forbidden tree in the Bible and the Quran.",
      "In Genesis the woman ate and gave to her husband; their eyes were opened, they knew they were naked and sewed fig leaves (Gen.3.6-7); in the Quran both tasted the tree, their shame became manifest and they covered themselves with leaves of the Garden (Q007.7.22, Q020.20.121)."),
  zh=("比较圣经和《古兰经》中亚当（阿丹）和妻子吃禁果后的情形。",
      "创世记中女人先吃，又给丈夫吃，二人眼睛就明亮了，知道自己赤身露体，便拿无花果树的叶子编作裙子（Gen.3.6-7）；《古兰经》说他俩尝了那棵树的果实，他俩的阴部就对自己显露出来，就用乐园的树叶遮盖（Q007.7.22, Q020.20.121）。"))
I("cross_corpus", "both", "medium", ["Gen.37.9", "Q012.12.4"],
  en=("What dream of Joseph is told in both the Bible and the Quran?",
      "Joseph dreamt that the sun, the moon and eleven stars bowed down to him (Gen.37.9, Q012.12.4)."),
  zh=("约瑟（优素福）的哪个梦在圣经和《古兰经》中都有记载？",
      "他梦见太阳、月亮和十一颗星向他下拜（Gen.37.9, Q012.12.4）。"))
I("cross_corpus", "both", "easy", ["1Sam.17.50", "Q002.2.251"],
  en=("Is David's killing of Goliath mentioned in both the Bible and the Quran?",
      "Yes. 1 Samuel says David prevailed over the Philistine with a sling and a stone (1Sam.17.50); the Quran says \"David slew Goliath\" (Q002.2.251)."),
  zh=("大卫（达五德）杀歌利亚（查鲁特）的事在圣经和《古兰经》中都有吗？",
      "有。撒母耳记上说大卫用机弦甩石胜了非利士人（1Sam.17.50）；《古兰经》说「达五德杀死查鲁特」（Q002.2.251）。"))
I("cross_corpus", "both", "medium", ["Jonah.1.17", "Jonah.2.10", "Q037.37.142", "Q037.37.145"],
  en=("How is Jonah's story with the fish told in the Bible and the Quran?",
      "In the Bible a great fish swallowed Jonah, he was in its belly three days and three nights and it vomited him onto dry land (Jonah.1.17, Jonah.2.10); in the Quran the fish swallowed him while he was blameworthy, and he was cast onto a desert shore while sick (Q037.37.142, Q037.37.145)."),
  zh=("约拿（优努斯）被鱼吞的故事在圣经和《古兰经》中是怎样讲的？",
      "圣经说耶和华安排一条大鱼吞了约拿，他在鱼腹中三日三夜，后来鱼把他吐在旱地上（Jonah.1.17, Jonah.2.10）；《古兰经》说大鱼吞了他，后来真主在他有病时将他抛在旱地上（Q037.37.142, Q037.37.145）。"))
I("cross_corpus", "both", "medium", ["Gen.18.10", "Gen.18.12", "Q011.11.71", "Q011.11.72"],
  en=("How did Abraham's wife react to the news she would have a son, in the Bible and the Quran?",
      "In both she laughed: in Genesis Sarah laughed within herself at being old (Gen.18.10, Gen.18.12); in the Quran his wife laughed and asked how she could bear a child when she and her husband were old (Q011.11.71-72)."),
  zh=("在圣经和《古兰经》中，亚伯拉罕的妻子听说要生子时有什么反应？",
      "两处都说她笑了：创世记中撒拉心里暗笑，因自己已经衰败（Gen.18.10, Gen.18.12）；《古兰经》中他的妻子笑了，说我已是老太婆，丈夫也是老头子，我怎么还会生育呢（Q011.11.71-72）。"))
I("cross_corpus", "both", "medium", ["Gen.4.8", "Gen.4.10", "Q005.5.27", "Q005.5.30", "Q005.5.31"],
  en=("Compare the story of Adam's two sons (Cain and Abel) in the Bible and the Quran.",
      "In Genesis Cain killed Abel and Abel's blood cried from the ground (Gen.4.8, Gen.4.10); the Quran tells of Adam's two sons whose offerings were accepted from one only, the killing, and a raven showing the killer how to hide his brother's corpse (Q005.5.27, Q005.5.30-31). The Quran does not name them."),
  zh=("比较圣经和《古兰经》中亚当两个儿子（该隐和亚伯）的故事。",
      "创世记说该隐杀了亚伯，亚伯的血从地里哀告（Gen.4.8, Gen.4.10）；《古兰经》讲阿丹的两个儿子献祭，只有一个被接受，后来一个杀了另一个，真主派一只乌鸦教他掩埋兄弟的尸体（Q005.5.27, Q005.5.30-31）。《古兰经》未提他们的名字。"))
I("cross_corpus", "both", "hard", ["Exod.32.4", "Q020.20.85", "Q020.20.88"],
  en=("Who made the golden calf according to the Bible versus the Quran?",
      "In Exodus Aaron fashioned the molten calf (Exod.32.4); in the Quran As-Samiri misled the people (Q020.20.85) and produced for them a calf which gave forth a lowing sound, and they cried \"This is your god and the god of Moses\" (Q020.20.88)."),
  zh=("根据圣经和《古兰经》，金牛犊分别是谁造的？",
      "出埃及记说是亚伦铸了一只牛犊（Exod.32.4）；《古兰经》说撒米里使穆萨的宗族迷误（Q020.20.85），他为他们铸出一头牛犊——一个有犊声的躯壳，他们说「这是你们的主，也是穆萨的主」（Q020.20.88）。"))
I("cross_corpus", "both", "easy", ["1Kgs.10.1", "Q027.27.22", "Q027.27.23"],
  en=("Is the Queen of Sheba's encounter with Solomon in both scriptures?",
      "Yes. In 1 Kings the queen of Sheba heard of Solomon's fame and came to prove him with hard questions (1Kgs.10.1); in the Quran the hoopoe brings Solomon news from Sheba of a woman ruling there with a mighty throne (Q027.27.22-23)."),
  zh=("示巴女王与所罗门相遇的事在两部经典中都有吗？",
      "有。列王纪上说示巴女王听见所罗门的名声，就来要用难解的话试问他（1Kgs.10.1）；《古兰经》说戴胜从赛百邑带来消息，那里有一个妇人统治，有一个庞大的宝座（Q027.27.22-23）。"))
I("cross_corpus", "both", "hard", ["Luke.1.20", "Q003.3.41", "Q019.19.10"],
  en=("What sign was Zechariah given about the birth of John, in the Bible and the Quran?",
      "In Luke he would be dumb until the day these things came to pass, because he did not believe (Luke.1.20); in the Quran his sign is that he would not speak to people for three days except by signs (Q003.3.41) / three nights (Q019.19.10)."),
  zh=("关于约翰（叶哈雅）的诞生，撒迦利亚（宰凯里雅）得到了什么兆头？",
      "路加福音说他因不信，必哑巴不能说话，直到这事成就（Luke.1.20）；《古兰经》说他的迹象是三日不能和人说话，只做手势（Q003.3.41）；另一处说三日三夜不能和人说话（Q019.19.10）。"))
I("cross_corpus", "both", "hard", ["Matt.27.35", "Matt.27.50", "Q004.4.157"],
  en=("Do the Bible and the Quran agree that Jesus was crucified?",
      "No. Matthew says they crucified him and he yielded up the ghost (Matt.27.35, Matt.27.50); the Quran says they slew him not nor crucified him, but it appeared so unto them (Q004.4.157)."),
  zh=("圣经和《古兰经》对耶稣是否被钉十字架看法一致吗？",
      "不一致。马太福音说他们把他钉在十字架上，耶稣大声喊叫，气就断了（Matt.27.35, Matt.27.50）；《古兰经》说他们没有杀死他，也没有把他钉死在十字架上，但他们不明白这件事的真相（Q004.4.157）。"))
I("cross_corpus", "both", "hard", ["John.1.14", "Q003.3.45", "Q004.4.171"],
  en=("Both scriptures call Jesus a \"Word\". How do they differ?",
      "John says the Word was made flesh and dwelt among us, the only begotten of the Father (John.1.14); the Quran calls the Messiah Jesus son of Mary a word from Allah (Q003.3.45) but only a messenger of Allah and His word conveyed to Mary — not three, Allah is One (Q004.4.171)."),
  zh=("两部经典都称耶稣为「道 / 言」，有什么不同？",
      "约翰福音说道成了肉身，住在我们中间，是父独生子的荣光（John.1.14）；《古兰经》称麦尔彦之子麦西哈·尔撒是真主的一句话（Q003.3.45），但只是真主的使者和他授予麦尔彦的一句话，不要说三位，真主是独一的（Q004.4.171）。"))
# ============================== PARAPHRASE (hard: no keyword overlap) ==============================
I("paraphrase", "bible", "hard", ["1Sam.16.7"],
  en=("Is there a verse saying God doesn't judge by appearances but by what's inside a person?",
      "Yes: \"the LORD seeth not as man seeth; for man looketh on the outward appearance, but the LORD looketh on the heart\" (1Sam.16.7)."),
  zh=("有没有经文说神不看外表，而是看人的内在？",
      "有：「耶和华不像人看人，人是看外貌，耶和华是看内心。」（1Sam.16.7）"))
I("paraphrase", "bible", "hard", ["1Cor.15.33"],
  en=("Where does the Bible warn that hanging out with the wrong crowd ruins your character?",
      "\"Be not deceived: evil communications corrupt good manners\" (1Cor.15.33)."),
  zh=("圣经哪里警告说交坏朋友会败坏品行？",
      "「你们不要自欺，滥交是败坏善行。」（1Cor.15.33）"))
I("paraphrase", "bible", "hard", ["Prov.15.1"],
  en=("Which proverb says a gentle reply calms someone down while harsh words make them angrier?",
      "\"A soft answer turneth away wrath: but grievous words stir up anger\" (Prov.15.1)."),
  zh=("哪句箴言说温和的回答能平息怒气，粗暴的话会激起怒火？",
      "「回答柔和，使怒消退；言语暴戾，触动怒气。」（Prov.15.1）"))
I("paraphrase", "bible", "hard", ["Prov.27.17"],
  en=("Is there a proverb about friends making each other better, like sharpening tools?",
      "\"Iron sharpeneth iron; so a man sharpeneth the countenance of his friend\" (Prov.27.17)."),
  zh=("有没有箴言讲朋友互相砥砺、彼此造就，就像磨利工具一样？",
      "「铁磨铁，磨出刃来；朋友相感（原文是磨朋友的脸）也是如此。」（Prov.27.17）"))
I("paraphrase", "bible", "hard", ["Prov.13.12"],
  en=("What verse talks about how waiting endlessly for something makes you heartsick, but getting it feels like new life?",
      "\"Hope deferred maketh the heart sick: but when the desire cometh, it is a tree of life\" (Prov.13.12)."),
  zh=("哪节经文说迟迟得不到盼望的事让人心里难受，愿望实现时却像得了新生命？",
      "「所盼望的迟延未得，令人心忧；所愿意的临到，却是生命树。」（Prov.13.12）"))
I("paraphrase", "bible", "hard", ["Gal.6.7"],
  en=("Where does the Bible say that what goes around comes around — your actions come back to you?",
      "\"Be not deceived; God is not mocked: for whatsoever a man soweth, that shall he also reap\" (Gal.6.7)."),
  zh=("圣经哪里说种瓜得瓜、种豆得豆——人的所作所为会回到自己身上？",
      "「不要自欺，神是轻慢不得的。人种的是甚么，收的也是甚么。」（Gal.6.7）"))
I("paraphrase", "bible", "hard", ["1Cor.10.13"],
  en=("Is there a promise that God won't let us face more pressure to do wrong than we can handle?",
      "Yes: God is faithful, who will not suffer you to be tempted above that ye are able, but will with the temptation also make a way to escape (1Cor.10.13)."),
  zh=("有没有应许说神不会让我们承受超过能力的诱惑？",
      "有：神是信实的，必不叫你们受试探过于所能受的，在受试探的时候总要给你们开一条出路（1Cor.10.13）。"))
I("paraphrase", "bible", "hard", ["Matt.7.3", "Matt.7.5"],
  en=("What did Jesus say about criticizing small faults in others while ignoring your own bigger ones?",
      "Why behold the mote in thy brother's eye but not the beam in thine own? First cast out the beam out of thine own eye (Matt.7.3, Matt.7.5)."),
  zh=("耶稣怎样评论只挑别人小毛病却无视自己大问题的人？",
      "为什么看见你弟兄眼中有刺，却不想自己眼中有梁木呢？先去掉自己眼中的梁木（Matt.7.3, Matt.7.5）。"))
I("paraphrase", "bible", "hard", ["Eccl.1.9"],
  en=("Which verse says that history just repeats itself and nothing is truly new?",
      "\"The thing that hath been, it is that which shall be... and there is no new thing under the sun\" (Eccl.1.9)."),
  zh=("哪节经文说历史不断重演，世上没有真正新的事？",
      "「已有的事，后必再有；已行的事，后必再行。日光之下并无新事。」（Eccl.1.9）"))
I("paraphrase", "bible", "hard", ["Eccl.4.9", "Eccl.4.10"],
  en=("Is there a passage saying teamwork is better than going it alone, since a partner can help you up?",
      "\"Two are better than one... For if they fall, the one will lift up his fellow: but woe to him that is alone when he falleth\" (Eccl.4.9-10)."),
  zh=("有没有经文说合作胜过单打独斗，因为跌倒时有同伴扶起？",
      "「两个人总比一个人好……若是跌倒，这人可以扶起他的同伴；若是孤身跌倒，没有别人扶起他来，这人就有祸了。」（Eccl.4.9-10）"))
I("paraphrase", "bible", "hard", ["Prov.27.1", "Jas.4.14"],
  en=("What does the Bible say about making big plans for tomorrow when life is so short and uncertain?",
      "Boast not thyself of to morrow, for thou knowest not what a day may bring forth (Prov.27.1); your life is even a vapour that appeareth for a little time and then vanisheth away (Jas.4.14)."),
  zh=("生命短暂又难以预料，圣经对夸口明天的计划怎么说？",
      "不要为明日自夸，因为一日要生何事，你尚且不能知道（Prov.27.1）；你们的生命原来是一片云雾，出现少时就不见了（Jas.4.14）。"))
I("paraphrase", "bible", "hard", ["Matt.6.1", "Matt.6.2"],
  en=("Did Jesus say anything about people who do good deeds just to show off?",
      "Do not your alms before men to be seen of them; do not sound a trumpet as the hypocrites do — they have their reward (Matt.6.1-2)."),
  zh=("耶稣有没有说过那些行善只为炫耀的人？",
      "你们要小心，不可将善事行在人的面前，故意叫他们看见；施舍时不可吹号，像假冒为善的人那样，他们已经得了他们的赏赐（Matt.6.1-2）。"))
I("paraphrase", "bible", "hard", ["Prov.17.22"],
  en=("Which proverb says being cheerful is like good medicine?",
      "\"A merry heart doeth good like a medicine: but a broken spirit drieth the bones\" (Prov.17.22)."),
  zh=("哪句箴言说心情愉快就像良药？",
      "「喜乐的心乃是良药；忧伤的灵使骨枯干。」（Prov.17.22）"))
I("paraphrase", "bible", "hard", ["Matt.7.24", "Matt.7.26"],
  en=("What's the story about building on solid ground versus building on something unstable?",
      "Whoever hears Jesus' sayings and does them is like a wise man who built his house upon a rock; whoever does not is like a foolish man who built upon the sand (Matt.7.24, Matt.7.26)."),
  zh=("在坚固的地基上盖房和在不稳的地方盖房的比喻是什么？",
      "听了耶稣的话就去行的，好比聪明人把房子盖在磐石上；听了不去行的，好比无知的人把房子盖在沙土上（Matt.7.24, Matt.7.26）。"))
I("paraphrase", "bible", "hard", ["Rom.8.38", "Rom.8.39"],
  en=("Is there a passage that says absolutely nothing can cut us off from God's love?",
      "Neither death, nor life, nor angels... nor any other creature shall be able to separate us from the love of God which is in Christ Jesus our Lord (Rom.8.38-39)."),
  zh=("有没有经文说任何事物都不能使我们与神的爱隔绝？",
      "无论是死，是生，是天使……是别的受造之物，都不能叫我们与神的爱隔绝，这爱是在我们的主基督耶稣里的（Rom.8.38-39）。"))
I("paraphrase", "bible", "hard", ["Luke.16.10"],
  en=("Where does it say that if you can be trusted with small things you can be trusted with big ones?",
      "\"He that is faithful in that which is least is faithful also in much\" (Luke.16.10)."),
  zh=("哪里说在小事上可靠的人，在大事上也可靠？",
      "「人在最小的事上忠心，在大事上也忠心。」（Luke.16.10）"))
I("paraphrase", "bible", "hard", ["John.8.7"],
  en=("What did Jesus say to the crowd ready to punish a woman, to make them think about their own faults?",
      "\"He that is without sin among you, let him first cast a stone at her\" (John.8.7)."),
  zh=("耶稣对准备惩罚一个妇人的人群说了什么，让他们反省自己？",
      "「你们中间谁是没有罪的，谁就可以先拿石头打她。」（John.8.7）"))

I("paraphrase", "quran", "hard", ["Q041.41.34"],
  en=("Does the Quran advise answering hostility with kindness so an enemy may become a friend?",
      "Yes: \"Repel the evil deed with one which is better, then lo! he, between whom and thee there was enmity (will become) as though he was a bosom friend\" (Q041.41.34)."),
  zh=("《古兰经》是否劝人以善报恶，使仇人变为朋友？",
      "是的：你应当以最优美的品行去对付恶劣的品行，那么，与你相仇者，忽然间会变得亲如密友（Q041.41.34）。"))
I("paraphrase", "quran", "hard", ["Q002.2.186"],
  en=("Is there a Quran verse saying God is close and answers whoever calls on Him?",
      "\"I am nigh. I answer the prayer of the suppliant when he crieth unto Me\" (Q002.2.186)."),
  zh=("有没有经文说真主很临近，应答呼求他的人？",
      "有：我确是临近的，确是答应祈祷者的祈祷的（Q002.2.186）。"))
I("paraphrase", "quran", "hard", ["Q025.25.63", "Q031.31.18", "Q031.31.19"],
  en=("What does the Quran say about walking around arrogantly or talking loudly?",
      "The servants of the Beneficent walk on the earth modestly (Q025.25.63); do not turn your cheek in scorn or walk with pertness, be modest in your bearing and lower your voice — the harshest voice is the braying of the ass (Q031.31.18-19)."),
  zh=("《古兰经》对走路傲慢、说话大声怎么说？",
      "至仁主的仆人在大地上谦逊而行（Q025.25.63）；你不要为藐视而转脸，不要骄傲地在地上行走，你应当节制你的步伐，应当抑制你的声音，最讨厌的声音是驴子的叫声（Q031.31.18-19）。"))
I("paraphrase", "quran", "hard", ["Q005.5.32"],
  en=("Is there a verse saying that saving one life is like saving all of humanity?",
      "Yes: whoever kills a soul (not for murder or corruption) it is as if he killed all mankind, and whoever saves the life of one it is as if he saved the life of all mankind (Q005.5.32)."),
  zh=("有没有经文说救活一个人就像救活了全人类？",
      "有：凡枉杀一人的，如杀众人；凡救活一人的，如救活众人（Q005.5.32）。"))
I("paraphrase", "quran", "hard", ["Q049.49.12"],
  en=("Does the Quran say anything about gossiping and spying on people?",
      "Avoid much suspicion, spy not, and do not backbite one another — would one of you love to eat the flesh of his dead brother? (Q049.49.12)."),
  zh=("《古兰经》对背后议论和窥探别人有什么说法？",
      "你们应当远离许多猜疑，不要互相侦探，不要互相背毁，难道你们中有人喜欢吃他的已死的教胞的肉吗？（Q049.49.12）"))
I("paraphrase", "quran", "hard", ["Q017.17.26", "Q017.17.27"],
  en=("What does the Quran say about wasting money?",
      "Give the kinsman, the needy and the wayfarer their due, and squander not in wantonness; squanderers are brothers of the devils (Q017.17.26-27)."),
  zh=("《古兰经》对挥霍浪费怎么说？",
      "你应当把亲戚、贫民和旅客应得的赠给他们，你不要挥霍；挥霍者确是恶魔的朋友（Q017.17.26-27）。"))
I("paraphrase", "quran", "hard", ["Q017.17.29", "Q025.25.67"],
  en=("Does the Quran recommend a middle way between being stingy and overspending?",
      "Yes: do not chain your hand to your neck nor open it with complete opening (Q017.17.29); the righteous, when they spend, are neither prodigal nor grudging, and there is ever a firm station between the two (Q025.25.67)."),
  zh=("《古兰经》是否主张在吝啬和挥霍之间取中道？",
      "是的：你不要把你的手束在脖子上，也不要把手完全伸开（Q017.17.29）；他们用钱的时候，既不挥霍，又不吝啬，谨守中道（Q025.25.67）。"))
I("paraphrase", "quran", "hard", ["Q013.13.28"],
  en=("Where does the Quran say hearts find peace?",
      "\"Verily in the remembrance of Allah do hearts find rest!\" (Q013.13.28)."),
  zh=("《古兰经》说人心在什么里面得到安宁？",
      "「真的，一切心境因记忆真主而安静。」（Q013.13.28）"))
I("paraphrase", "quran", "hard", ["Q002.2.282"],
  en=("Does the Quran tell people to put loans and debts in writing?",
      "Yes: when you contract a debt for a fixed term, record it in writing, let a scribe write it in equity and call two witnesses (Q002.2.282)."),
  zh=("《古兰经》是否要求把借贷写成文书？",
      "是的：你们彼此间成立定期借贷的时候，你们应当写一张借券，请一个会写字的人秉公代书，并邀请两个男人作证（Q002.2.282）。"))
# ============================== NEGATIVE (out of scope; system should decline) ==============================
NEG = [
    ("What does the Bible say about smartphones?", "圣经怎样谈论智能手机？"),
    ("What does the Quran say about cryptocurrency and Bitcoin?", "《古兰经》对加密货币和比特币有什么规定？"),
    ("Which verse describes the conversion of Emperor Constantine?", "哪节经文记载了君士坦丁大帝的归信？"),
    ("Where does the Bible prophesy the founding of the United States of America?", "圣经哪里预言了美利坚合众国的建立？"),
    ("Who won the 2018 FIFA World Cup?", "2018年世界杯冠军是谁？"),
    ("Which surah mentions the city of Paris?", "《古兰经》哪一章提到了巴黎？"),
    ("Give me a recipe for borscht.", "给我一个罗宋汤的做法。"),
    ("Does the Bible say COVID-19 vaccines are forbidden?", "圣经是否禁止接种新冠疫苗？"),
    ("What does the Quran say about using Instagram and social media?", "《古兰经》对使用社交媒体有什么说法？"),
    ("What did the Buddha teach about the Four Noble Truths?", "佛陀关于四圣谛的教导是什么？"),
    ("Which Bible verse mentions Napoleon?", "哪节圣经提到了拿破仑？"),
    ("How do I install Python on Windows?", "怎样在 Windows 上安装 Python？"),
    ("What does the Bible say about nuclear power plants?", "圣经对核电站怎么说？"),
    ("Which Quran verse explains how electricity works?", "《古兰经》哪节经文解释了电的原理？"),
]
for en_q, zh_q in NEG:
    I("negative", "none", "easy", [],
      en=(en_q, "The Bible (KJV) and Quran corpora contain no passage on this topic; the system should say so instead of citing unrelated verses."),
      zh=(zh_q, "圣经（和合本）和《古兰经》语料中没有涉及该主题的经文；系统应说明找不到，而不是引用无关经文。"),
      behavior="not_found")

# ============================== TRAP (false premise / misattributed quotes) ==============================
I("trap", "bible", "medium", [],
  en=("Which Bible verse says \"God helps those who help themselves\"?",
      "No verse says this; it is a proverb (popularised by Benjamin Franklin), not a Bible quotation. The system should not invent a reference."),
  zh=("哪节圣经说「天助自助者」？",
      "圣经中没有这句话；它是一句谚语（因富兰克林而流行），不是圣经经文。系统不应编造出处。"),
  behavior="not_found")
I("trap", "bible", "medium", [],
  en=("Where in the Bible does it say \"cleanliness is next to godliness\"?",
      "Nowhere; the saying is not in the Bible (it is usually attributed to John Wesley). The system should not cite a verse."),
  zh=("圣经哪里说「清洁近乎敬虔」？",
      "圣经中没有这句话（通常认为出自约翰·卫斯理）。系统不应引用经文。"),
  behavior="not_found")
I("trap", "bible", "medium", [],
  en=("Quote the Bible verse \"This too shall pass\".",
      "There is no such verse in the Bible; \"this too shall pass\" is a folk saying. The system should say it is not found."),
  zh=("请引用圣经中「这一切都会过去」那节经文。",
      "圣经中没有这节经文；这是民间谚语。系统应说明找不到。"),
  behavior="not_found")
I("trap", "bible", "medium", [],
  en=("Which verse says \"God works in mysterious ways\"?",
      "No Bible verse says this; it comes from a hymn by William Cowper. The system should not invent a reference."),
  zh=("哪节经文说「神的作为是奥秘莫测的」（God works in mysterious ways）？",
      "圣经中没有这句原话；它出自威廉·柯珀的一首赞美诗。系统不应编造出处。"),
  behavior="not_found")
I("trap", "quran", "medium", [],
  en=("Which Quran verse says \"Seek knowledge even unto China\"?",
      "This is not a Quran verse; it is a saying attributed to the Prophet in hadith literature (of disputed authenticity). The system should not cite a Quran reference."),
  zh=("哪节《古兰经》说「求知哪怕远在中国」？",
      "这不是《古兰经》经文，而是圣训文献中归于先知的一句话（真实性有争议）。系统不应引用《古兰经》出处。"),
  behavior="not_found")
I("trap", "bible", "medium", ["1Tim.6.10"],
  en=("The Bible says money is the root of all evil, right?",
      "Not exactly: 1 Timothy 6:10 says \"the love of money is the root of all evil\" — it is the love of money, not money itself (1Tim.6.10)."),
  zh=("圣经说金钱是万恶之根，对吗？",
      "不完全对：提摩太前书6章10节说「贪财是万恶之根」，是贪财，而不是钱本身（1Tim.6.10）。"),
  behavior="correct_premise")
I("trap", "bible", "hard", ["Prov.13.24"],
  en=("Quote the Bible verse \"Spare the rod, spoil the child\".",
      "That exact wording is not in the Bible (it is from a 17th-century poem); the closest verse is Proverbs 13:24: \"He that spareth his rod hateth his son: but he that loveth him chasteneth him betimes\" (Prov.13.24)."),
  zh=("请引用圣经中「孩子不打不成器」（Spare the rod, spoil the child）这节经文。",
      "圣经中没有这句原话；最接近的是箴言13章24节：「不忍用杖打儿子的，是恨恶他；疼爱儿子的，随时管教。」（Prov.13.24）"),
  behavior="correct_premise")
I("trap", "bible", "medium", ["Prov.16.18"],
  en=("Which verse says \"Pride comes before a fall\"?",
      "The popular saying shortens Proverbs 16:18: \"Pride goeth before destruction, and an haughty spirit before a fall\" (Prov.16.18)."),
  zh=("哪节经文说「骄者必败」（Pride comes before a fall）？",
      "这是箴言16章18节的简化说法：「骄傲在败坏以先；狂心在跌倒之前。」（Prov.16.18）"),
  behavior="correct_premise")
I("trap", "bible", "hard", ["Isa.11.6"],
  en=("Where does the Bible say \"the lion shall lie down with the lamb\"?",
      "That exact phrase is not in the KJV. Isaiah 11:6 says \"The wolf also shall dwell with the lamb, and the leopard shall lie down with the kid\" (Isa.11.6)."),
  zh=("圣经哪里说「狮子必与羊羔同卧」？",
      "圣经中没有这句原话。以赛亚书11章6节说「豺狼必与绵羊羔同居，豹子与山羊羔同卧」（Isa.11.6）。"),
  behavior="correct_premise")
I("trap", "bible", "medium", ["Gen.3.6"],
  en=("What kind of apple did Eve eat in the Garden of Eden?",
      "The Bible never says it was an apple; Genesis 3:6 only speaks of \"the fruit thereof\" of the tree (Gen.3.6)."),
  zh=("夏娃在伊甸园吃的是什么品种的苹果？",
      "圣经从未说那是苹果；创世记3章6节只说「那棵树的果子」（Gen.3.6）。"),
  behavior="correct_premise")
I("trap", "bible", "medium", ["Matt.2.1", "Matt.2.11"],
  en=("What were the names of the three wise men who visited Jesus?",
      "The Bible neither names the wise men nor says there were three; Matthew mentions \"wise men from the east\" who offered gold, frankincense and myrrh (Matt.2.1, Matt.2.11). Three gifts, not a stated number of men."),
  zh=("拜访耶稣的三位博士叫什么名字？",
      "圣经没有记载博士的名字，也没说是三位；马太福音只说「有几个博士从东方来」，献上黄金、乳香、没药三样礼物（Matt.2.1, Matt.2.11）。"),
  behavior="correct_premise")
I("trap", "bible", "medium", ["Jonah.1.17", "Matt.12.40"],
  en=("What species of whale swallowed Jonah?",
      "The book of Jonah says \"a great fish\" (Jonah.1.17); only the KJV of Matthew 12:40 says \"whale's belly\" (Matt.12.40). No species is given."),
  zh=("吞下约拿的是什么品种的鲸鱼？",
      "约拿书说的是「一条大鱼」（Jonah.1.17），马太福音12章40节也说「大鱼肚腹」（Matt.12.40）；经文没有说明品种。"),
  behavior="correct_premise", notes="KJV Matt.12.40 'whale' vs CUV 大鱼")
I("trap", "bible", "hard", ["Gen.2.21", "Gen.2.22"],
  en=("Since Eve was made from Adam's rib, do men have one fewer rib than women according to the Bible?",
      "The Bible says God took one of Adam's ribs and made a woman (Gen.2.21-22), but it says nothing about men having fewer ribs; that inference is not in the text."),
  zh=("既然夏娃是用亚当的肋骨造的，圣经是否说男人比女人少一根肋骨？",
      "圣经说神取下亚当的一条肋骨造成一个女人（Gen.2.21-22），但并没有说男人比女人少一根肋骨；那是推论，经文中没有。"),
  behavior="correct_premise")
I("trap", "quran", "hard", ["Q066.66.11"],
  en=("What is the name of Pharaoh's wife given in the Quran?",
      "The Quran does not name her; it refers to \"the wife of Pharaoh\" who prayed for a home with Allah in Paradise (Q066.66.11). The name Asiya comes from later tradition."),
  zh=("《古兰经》中法老的妻子叫什么名字？",
      "《古兰经》没有记载她的名字，只说「法老的妻子」祈求真主在乐园中为她建一所房屋（Q066.66.11）；“阿西亚”之名出自后世传统。"),
  behavior="correct_premise")
I("trap", "quran", "hard", ["Q003.3.35", "Q003.3.36"],
  en=("What was the name of Mary's mother according to the Quran?",
      "The Quran does not give her name; it calls her \"the wife of Imran\", who dedicated her unborn child and named the girl Mary (Q003.3.35-36)."),
  zh=("《古兰经》中麦尔彦的母亲叫什么名字？",
      "《古兰经》没有记载她的名字，只称她为「仪姆兰的女人」，她把腹中的孩子献给真主，并给女孩起名麦尔彦（Q003.3.35-36）。"),
  behavior="correct_premise")
I("trap", "quran", "hard", ["Q031.31.14", "Q046.46.15"],
  en=("Which Quran verse says \"Paradise lies at the feet of mothers\"?",
      "No Quran verse says this; it is a hadith. The Quran does stress the mother's hardship and kindness to parents (Q031.31.14, Q046.46.15)."),
  zh=("哪节《古兰经》说「天堂在母亲的脚下」？",
      "《古兰经》中没有这句话，它出自圣训。《古兰经》确实强调母亲怀孕的艰辛和孝敬父母（Q031.31.14, Q046.46.15）。"),
  behavior="correct_premise")
# ============================== MORE HAND-WRITTEN ITEMS (expansion) ==============================
# --- factual: Bible ---
I("factual", "bible", "medium", ["Judg.16.30"],
  en=("How did Samson die, and how did the number he killed at his death compare with his life?",
      'Saying "Let me die with the Philistines", he "bowed himself with all his might; and the house fell upon the lords"; "the dead which he slew at his death were more than they which he slew in his life" (Judg.16.30).'),
  zh=("参孙是怎样死的？他死时所杀的人与生前相比如何？",
      "他说「我情愿与非利士人同死」，「就尽力屈身，房子倒塌，压住首领和房内的众人」；「参孙死时所杀的人比活着所杀的还多」（Judg.16.30）。"))
I("factual", "bible", "easy", ["Judg.7.7"],
  en=("How many men did God tell Gideon He would use to save Israel from the Midianites?",
      'Three hundred: "By the three hundred men that lapped will I save you, and deliver the Midianites into thine hand" (Judg.7.7).'),
  zh=("神告诉基甸要用多少人从米甸人手中拯救以色列？",
      "三百人：「我要用这舔水的三百人拯救你们，将米甸人交在你手中」（Judg.7.7）。"))
I("factual", "bible", "easy", ["Ruth.4.13"],
  en=("Whom did Ruth marry?",
      'Boaz: "So Boaz took Ruth, and she was his wife", and the Lord gave her a son (Ruth.4.13).'),
  zh=("路得嫁给了谁？",
      "波阿斯：「波阿斯娶了路得为妻」，耶和华使她怀孕生了一个儿子（Ruth.4.13）。"))
I("factual", "bible", "easy", ["1Sam.16.13"],
  en=("Who anointed David, and what happened to David from that day?",
      'Samuel "took the horn of oil, and anointed him in the midst of his brethren: and the Spirit of the Lord came upon David from that day forward" (1Sam.16.13).'),
  zh=("谁膏立了大卫？从那天起大卫有什么变化？",
      "撒母耳「用角里的膏油，在他诸兄中膏了他。从这日起，耶和华的灵就大大感动大卫」（1Sam.16.13）。"))
I("factual", "bible", "medium", ["1Kgs.3.25", "1Kgs.3.27"],
  en=("How did King Solomon decide which of two women was the real mother of a child?",
      'He ordered, "Divide the living child in two, and give half to the one, and half to the other" (1Kgs.3.25); when the true mother pleaded for the child, he ruled, "Give her the living child, and in no wise slay it: she is the mother thereof" (1Kgs.3.27).'),
  zh=("所罗门王怎样判断两个妇人中谁是孩子真正的母亲？",
      "王说「将活孩子劈成两半，一半给那妇人，一半给这妇人」（1Kgs.3.25）；随后判定「将活孩子给这妇人，万不可杀他；这妇人实在是他的母亲」（1Kgs.3.27）。"))
I("factual", "bible", "medium", ["1Kgs.18.38"],
  en=("What happened when Elijah called on the Lord in the contest with the prophets of Baal?",
      '"Then the fire of the Lord fell, and consumed the burnt sacrifice, and the wood, and the stones, and the dust, and licked up the water that was in the trench" (1Kgs.18.38).'),
  zh=("以利亚与巴力先知较量时求告耶和华，结果发生了什么？",
      "「耶和华降下火来，烧尽燔祭、木柴、石头、尘土，又烧干沟里的水」（1Kgs.18.38）。"))
I("factual", "bible", "easy", ["2Kgs.5.14"],
  en=("How was Naaman healed of his leprosy?",
      'He "dipped himself seven times in Jordan, according to the saying of the man of God: and his flesh came again like unto the flesh of a little child, and he was clean" (2Kgs.5.14).'),
  zh=("乃缦的大麻疯是怎样得医治的？",
      "乃缦「照着神人的话，在约旦河里沐浴七回；他的肉复原，好像小孩子的肉，他就洁净了」（2Kgs.5.14）。"))
I("factual", "bible", "medium", ["Neh.6.15"],
  en=("How long did it take Nehemiah's builders to finish the wall of Jerusalem?",
      'Fifty-two days: "the wall was finished in the twenty and fifth day of the month Elul, in fifty and two days" (Neh.6.15).'),
  zh=("尼希米带领百姓修城墙用了多少天？",
      "五十二天：「以禄月二十五日，城墙修完了，共修了五十二天」（Neh.6.15）。"))
I("factual", "bible", "medium", ["Esth.4.16", "Esth.7.10"],
  en=("What did Esther say before going to the king uninvited, and what became of Haman?",
      'She asked the Jews to fast three days and said, "so will I go in unto the king, which is not according to the law: and if I perish, I perish" (Esth.4.16). In the end "they hanged Haman on the gallows that he had prepared for Mordecai" (Esth.7.10).'),
  zh=("以斯帖未蒙召去见王之前说了什么？哈曼的结局如何？",
      "她请犹大人为她禁食三昼三夜，并说「然后我违例进去见王，我若死就死吧」（Esth.4.16）。最后「人将哈曼挂在他为末底改所预备的木架上」（Esth.7.10）。"))
I("factual", "bible", "medium", ["Dan.5.25", "Dan.5.26"],
  en=("What words were written on the wall at Belshazzar's feast, and what did MENE mean?",
      '"MENE, MENE, TEKEL, UPHARSIN" (Dan.5.25); "MENE; God hath numbered thy kingdom, and finished it" (Dan.5.26).'),
  zh=("伯沙撒王宴席时墙上写的是什么字？「弥尼」是什么意思？",
      "「弥尼，弥尼，提客勒，乌法珥新」（Dan.5.25）；「弥尼，就是神已经数算你国的年日到此完毕」（Dan.5.26）。"))
I("factual", "bible", "easy", ["Jonah.3.5"],
  en=("How did the people of Nineveh respond to Jonah's warning?",
      '"the people of Nineveh believed God, and proclaimed a fast, and put on sackcloth, from the greatest of them even to the least of them" (Jonah.3.5).'),
  zh=("尼尼微人对约拿的警告有什么反应？",
      "「尼尼微人信服神，便宣告禁食，从最大的到至小的都穿麻衣」（Jonah.3.5）。"))
I("factual", "bible", "easy", ["Job.42.10"],
  en=("What did the Lord do for Job after his trials?",
      'When Job prayed for his friends, "the Lord gave Job twice as much as he had before" (Job.42.10).'),
  zh=("约伯经历试炼之后，耶和华为他做了什么？",
      "约伯为朋友祈祷后，「耶和华赐给他的比他从前所有的加倍」（Job.42.10）。"))
I("factual", "bible", "easy", ["Acts.2.4"],
  en=("What happened when the disciples were all filled with the Holy Ghost in Acts 2?",
      'They "began to speak with other tongues, as the Spirit gave them utterance" (Acts.2.4).'),
  zh=("使徒行传第2章门徒被圣灵充满时发生了什么？",
      "他们「按着圣灵所赐的口才说起别国的话来」（Acts.2.4）。"))
I("factual", "bible", "easy", ["Acts.7.59"],
  en=("What did Stephen pray while he was being stoned?",
      '"Lord Jesus, receive my spirit" (Acts.7.59).'),
  zh=("司提反被石头打的时候祷告说什么？",
      "「求主耶稣接收我的灵魂」（Acts.7.59）。"))
I("factual", "bible", "easy", ["Luke.10.33", "Luke.10.34"],
  en=("What did the Samaritan do for the man who had fallen among thieves?",
      'He "had compassion on him" (Luke.10.33), "bound up his wounds, pouring in oil and wine, and set him on his own beast, and brought him to an inn, and took care of him" (Luke.10.34).'),
  zh=("那个撒马利亚人为落在强盗手中的人做了什么？",
      "他「看见他就动了慈心」（Luke.10.33），「上前用油和酒倒在他的伤处，包裹好了，扶他骑上自己的牲口，带到店里去照应他」（Luke.10.34）。"))
I("factual", "bible", "easy", ["Luke.15.20"],
  en=("How did the father react when his prodigal son came home?",
      '"when he was yet a great way off, his father saw him, and had compassion, and ran, and fell on his neck, and kissed him" (Luke.15.20).'),
  zh=("浪子回家时父亲有什么反应？",
      "「相离还远，他父亲看见，就动了慈心，跑去抱着他的颈项，连连与他亲嘴」（Luke.15.20）。"))
I("factual", "bible", "easy", ["Matt.14.29"],
  en=("Which disciple walked on the water to go to Jesus?",
      'Peter: "when Peter was come down out of the ship, he walked on the water, to go to Jesus" (Matt.14.29).'),
  zh=("哪个门徒在水面上走要到耶稣那里去？",
      "彼得：「彼得就从船上下去，在水面上走，要到耶稣那里去」（Matt.14.29）。"))
I("factual", "bible", "easy", ["Mark.4.39"],
  en=("What did Jesus say to the sea during the storm, and what happened?",
      'He "rebuked the wind, and said unto the sea, Peace, be still. And the wind ceased, and there was a great calm" (Mark.4.39).'),
  zh=("风暴中耶稣对海说了什么？结果如何？",
      "耶稣斥责风，向海说「住了吧！静了吧！」，「风就止住，大大地平静了」（Mark.4.39）。"))
I("factual", "bible", "easy", ["John.11.43", "John.11.44"],
  en=("What did Jesus say at Lazarus's tomb, and what happened?",
      'He cried, "Lazarus, come forth" (John.11.43). "he that was dead came forth, bound hand and foot with graveclothes", and Jesus said, "Loose him, and let him go" (John.11.44).'),
  zh=("耶稣在拉撒路的坟墓前说了什么？结果如何？",
      "耶稣大声呼叫「拉撒路出来」（John.11.43）。「那死人就出来了，手脚裹着布」，耶稣说「解开，叫他走」（John.11.44）。"))
I("factual", "bible", "easy", ["Gen.11.9"],
  en=("Why was the city called Babel?",
      '"because the Lord did there confound the language of all the earth" (Gen.11.9).'),
  zh=("那城为什么叫巴别？",
      "「因为耶和华在那里变乱天下人的言语，使众人分散在全地上，所以那城名叫巴别」（Gen.11.9）。"))
I("factual", "bible", "easy", ["Gen.19.26"],
  en=("What happened to Lot's wife?",
      '"his wife looked back from behind him, and she became a pillar of salt" (Gen.19.26).'),
  zh=("罗得的妻子怎么了？",
      "「罗得的妻子在后边回头一看，就变成了一根盐柱」（Gen.19.26）。"))
I("factual", "bible", "medium", ["Num.22.28"],
  en=("Which animal spoke to Balaam, and what did it say?",
      'His ass: "the Lord opened the mouth of the ass, and she said unto Balaam, What have I done unto thee, that thou hast smitten me these three times?" (Num.22.28).'),
  zh=("哪个动物对巴兰说话？说了什么？",
      "他的驴：「耶和华叫驴开口，对巴兰说：『我向你行了甚么，你竟打我这三次呢？』」（Num.22.28）。"))
I("factual", "bible", "medium", ["2Sam.11.15"],
  en=("What did David write in his letter about Uriah?",
      '"Set ye Uriah in the forefront of the hottest battle, and retire ye from him, that he may be smitten, and die" (2Sam.11.15).'),
  zh=("大卫在信中对乌利亚作了什么安排？",
      "信内写着「要派乌利亚前进，到阵势极险之处，你们便退后，使他被杀」（2Sam.11.15）。"))
I("factual", "bible", "medium", ["Ezra.1.2"],
  en=("What did Cyrus king of Persia say the Lord had charged him to do?",
      '"he hath charged me to build him an house at Jerusalem, which is in Judah" (Ezra.1.2).'),
  zh=("波斯王塞鲁士说耶和华嘱咐他做什么？",
      "「嘱咐我在犹大的耶路撒冷为他建造殿宇」（Ezra.1.2）。"))
I("factual", "bible", "easy", ["Rev.21.1"],
  en=("In Revelation, what did John see after the first heaven and earth passed away?",
      '"I saw a new heaven and a new earth: for the first heaven and the first earth were passed away; and there was no more sea" (Rev.21.1).'),
  zh=("启示录中，先前的天地过去之后约翰看见了什么？",
      "「我又看见一个新天新地；因为先前的天地已经过去了，海也不再有了」（Rev.21.1）。"))

# --- factual: Quran ---
I("factual", "quran", "medium", ["Q018.18.65"],
  en=("In Surah al-Kahf, whom did Moses and his servant find?",
      '"one of Our slaves, unto whom We had given mercy from Us, and had taught him knowledge from Our presence" (Q018.18.65).'),
  zh=("在《山洞章》中，穆萨和他的仆人发现了谁？",
      "「我的一个仆人，我已把从我这里发出的恩惠赏赐他，我已把从我这里发出的知识传授他」（Q018.18.65）。"))
I("factual", "quran", "medium", ["Q018.18.94", "Q018.18.95"],
  en=("What did the people ask Dhu'l-Qarneyn to do about Gog and Magog?",
      'They offered tribute "on condition that thou set a barrier between us and them" (Q018.18.94). He replied, "That wherein my Lord hath established me is better", asked only for help with strength, and promised "I will set between you and them a bank" (Q018.18.95).'),
  zh=("人们请求左勒盖尔奈英怎样对付雅朱者和马朱者？",
      "他们愿意进贡，「务请你在我们和他们之间建筑一座壁垒」（Q018.18.94）。他说「我的主使我能够享受的，尤为优美」，只要人力扶助，「我就在你们和他们之间建筑一座壁垒」（Q018.18.95）。"))
I("factual", "quran", "medium", ["Q028.28.23", "Q028.28.24"],
  en=("What did Moses do at the water of Midian, according to the Quran?",
      'He found "two women keeping back (their flocks)" (Q028.28.23); "he watered (their flock) for them", then turned to the shade and prayed, "My Lord! I am needy of whatever good Thou sendest down for me" (Q028.28.24).'),
  zh=("据《古兰经》，穆萨在麦德彦的泉边做了什么？",
      "他看见「两个女子，拦著她们俩的羊群」（Q028.28.23）；「他就替她俩饮羊」，然后退到树荫下祈祷「我的主啊！我确需求你所降给我的任何福利的」（Q028.28.24）。"))
I("factual", "quran", "medium", ["Q011.11.42", "Q011.11.43"],
  en=("What happened to Noah's son in the flood, according to the Quran?",
      'Noah called, "O my son! Come ride with us" (Q011.11.42); the son answered, "I shall betake me to some mountain that will save me from the water", but "the wave came in between them, so he was among the drowned" (Q011.11.43).'),
  zh=("据《古兰经》，努哈的儿子在洪水中结局如何？",
      "努哈喊叫「我的孩子啊！你来和我们一道乘船吧」（Q011.11.42）；他儿子说「我要到一座山上去躲避洪水」，结果「波涛隔开了他们俩，他就被淹死了」（Q011.11.43）。"))
I("factual", "quran", "medium", ["Q007.7.73"],
  en=("What sign did the prophet Salih bring to the tribe of Thamud?",
      'A she-camel: "this is the camel of Allah, a token unto you; so let her feed in Allah\'s earth, and touch her not with hurt" (Q007.7.73).'),
  zh=("先知撒立哈给赛莫德人带来了什么迹象？",
      "一只母驼：「这只真主的母驼可以作你们的迹象。故你们让牠在真主的大地上随便吃草，不要伤害牠」（Q007.7.73）。"))
I("factual", "quran", "easy", ["Q007.7.65"],
  en=("To which tribe was the prophet Hud sent?",
      'To A\'ad: "unto (the tribe of) A\'ad (We sent) their brother, Hud" (Q007.7.65).'),
  zh=("先知呼德被派往哪个民族？",
      "阿德人：「（我确已派遣）阿德人的弟兄呼德去教化他们」（Q007.7.65）。"))
I("factual", "quran", "medium", ["Q007.7.85"],
  en=("What did Shu'eyb command the people of Midian about trade?",
      '"give full measure and full weight and wrong not mankind in their goods" (Q007.7.85).'),
  zh=("舒阿卜在买卖方面命令麦德彦人做什么？",
      "「你们当使用充足的斗和秤，不要克扣别人所应得的货物」（Q007.7.85）。"))
I("factual", "quran", "easy", ["Q012.12.43"],
  en=("What did the king dream in Surah Yusuf?",
      '"seven fat kine which seven lean were eating, and seven green ears of corn and other (seven) dry" (Q012.12.43).'),
  zh=("《优素福章》中国王做了什么梦？",
      "「我确已梦见七头胖黄牛，被七头瘦黄牛吃掉了，又梦见七穗青麦子，和七穗干麦子」（Q012.12.43）。"))
I("factual", "quran", "easy", ["Q012.12.93"],
  en=("What did Joseph send to his father to restore his sight, in the Quran?",
      'His shirt: "Go with this shirt of mine and lay it on my father\'s face, he will become (again) a seer" (Q012.12.93).'),
  zh=("《古兰经》中优素福送什么给父亲使他恢复视力？",
      "他的衬衣：「你们把我这件衬衣带回去，把它蒙在我父亲的脸上，他就会恢复视力」（Q012.12.93）。"))
I("factual", "quran", "medium", ["Q019.19.23", "Q019.19.25"],
  en=("Where did Mary give birth according to Surah Maryam, and what was she told to do?",
      '"the pangs of childbirth drove her unto the trunk of the palm-tree" (Q019.19.23), and she was told, "shake the trunk of the palm-tree toward thee, thou wilt cause ripe dates to fall upon thee" (Q019.19.25).'),
  zh=("据《麦尔彦章》，麦尔彦在哪里分娩？她被吩咐做什么？",
      "「阵痛迫使她来到一棵椰枣树旁」（Q019.19.23）；她被告知「你向著你的方向摇撼椰枣树，就有新鲜的、成熟的椰枣纷纷落在你的面前」（Q019.19.25）。"))
I("factual", "quran", "medium", ["Q003.3.49"],
  en=("Which miracles does the Quran attribute to Jesus in Surah Al Imran?",
      '"I fashion for you out of clay the likeness of a bird, and I breathe into it and it is a bird, by Allah\'s leave. I heal him who was born blind, and the leper, and I raise the dead, by Allah\'s leave" (Q003.3.49).'),
  zh=("《仪姆兰的家属章》说尔撒行了哪些奇迹？",
      "「我必定为你们用泥做一个像鸟样的东西，我吹口气在里面，它就奉真主的命令而飞动。我奉真主的命令，能医治天然盲、大麻疯，又能使死者复活」（Q003.3.49）。"))
I("factual", "quran", "medium", ["Q005.5.112", "Q005.5.114"],
  en=("What did the disciples ask Jesus to request from heaven in Surah al-Ma'idah?",
      '"a table spread with food from heaven" (Q005.5.112); Jesus prayed for it "that it may be a feast for us, for the first of us and for the last of us, and a sign from Thee" (Q005.5.114).'),
  zh=("《筵席章》中众门徒请尔撒向天求什么？",
      "他们问「你的主能从天上降筵席给我们吗」（Q005.5.112）；尔撒祈求「求你从天上降筵席给我们，以便我们先辈和后辈都以降筵之日为节日」（Q005.5.114）。"))
I("factual", "quran", "easy", ["Q002.2.67"],
  en=("What did Moses command his people to sacrifice in Surah al-Baqarah, and how did they react?",
      '"Allah commandeth you that ye sacrifice a cow, they said: Dost thou make game of us?" (Q002.2.67).'),
  zh=("《黄牛章》中穆萨命令他的宗族宰什么？他们怎样回应？",
      "「真主的确命令你们宰一头牛」，他们说「你愚弄我们吗」（Q002.2.67）。"))
I("factual", "quran", "hard", ["Q002.2.249"],
  en=("How did Saul (Talut) test his army before facing Goliath, according to the Quran?",
      'By a river: "Whosoever therefore drinketh thereof he is not of me ... save him who taketh (thereof) in the hollow of his hand. But they drank thereof, all save a few of them" (Q002.2.249).'),
  zh=("据《古兰经》，塔鲁特在迎战查鲁特之前怎样考验他的军队？",
      "用一条河：「谁饮河水，谁不是我的部属；谁不尝河水，谁确是我的部属」，只用手捧一捧水的人不算违命；结果「他们除少数人外，都饮了河水」（Q002.2.249）。"))
I("factual", "quran", "easy", ["Q105.105.3", "Q105.105.4"],
  en=("What did God send against the army in Surah al-Fil (the Elephant)?",
      '"swarms of flying creatures" (Q105.105.3), "Which pelted them with stones of baked clay" (Q105.105.4).'),
  zh=("《象章》中真主派什么去对付那支军队？",
      "「他曾派遣成群的鸟去伤他们」（Q105.105.3），「以粘土石射击他们」（Q105.105.4）。"))
I("factual", "quran", "easy", ["Q031.31.13"],
  en=("What was Luqman's first advice to his son?",
      '"O my dear son! Ascribe no partners unto Allah. Lo! to ascribe partners (unto Him) is a tremendous wrong" (Q031.31.13).'),
  zh=("鲁格曼对儿子的第一条教训是什么？",
      "「我的小子啊！你不要以任何物配主。以物配主，确是大逆不道的」（Q031.31.13）。"))
I("factual", "quran", "medium", ["Q002.2.144"],
  en=("Toward which direction does the Quran tell believers to turn their faces in prayer?",
      '"turn thy face toward the Inviolable Place of Worship, and ye (O Muslims), wheresoever ye may be, turn your faces (when ye pray) toward it" (Q002.2.144).'),
  zh=("《古兰经》吩咐信士礼拜时把脸转向哪里？",
      "「你应当把你的脸转向禁寺。你们无论在哪里，都应当把你们的睑转向禁寺」（Q002.2.144）。"))
I("factual", "quran", "medium", ["Q009.9.40"],
  en=("What did the Prophet say to his companion when the two were in the cave?",
      '"Grieve not. Lo! Allah is with us" (Q009.9.40).'),
  zh=("先知和同伴在山洞里时，他对同伴说了什么？",
      "「不要忧愁，真主确是和我们在一起的」（Q009.9.40）。"))
I("factual", "quran", "medium", ["Q034.34.12", "Q027.27.16"],
  en=("What special powers does the Quran say Solomon was given?",
      'The wind, "whereof the morning course was a month\'s journey and the evening course a month\'s journey", a "fount of copper", and jinn who worked before him (Q034.34.12); he also said, "we have been taught the language of birds" (Q027.27.16).'),
  zh=("《古兰经》说素莱曼被赐予哪些特殊能力？",
      "「我曾使风供素莱曼的驱使，风在上午走一月的路程，在下午也走一月的路程」，又使「熔铜像泉水样涌出」，并有精灵为他工作（Q034.34.12）；他还说「我们曾学会百鸟的语言」（Q027.27.16）。"))

# --- cross_corpus ---
I("cross_corpus", "both", "medium", ["Job.1.21", "Job.42.10", "Q021.21.83", "Q021.21.84"],
  en=("How do the Bible and the Quran describe Job's suffering and restoration?",
      'In the Bible Job says, "the Lord gave, and the Lord hath taken away; blessed be the name of the Lord" (Job.1.21), and later "the Lord gave Job twice as much as he had before" (Job.42.10). In the Quran Job cries, "Lo! adversity afflicteth me, and Thou art Most Merciful of all who show mercy" (Q021.21.83), and God "removed that adversity" and gave him "his household ... and the like thereof along with them" (Q021.21.84).'),
  zh=("圣经和《古兰经》怎样记载约伯（艾优卜）的苦难与复兴？",
      "圣经中约伯说「赏赐的是耶和华，收取的也是耶和华。耶和华的名是应当称颂的」（Job.1.21），后来「耶和华赐给他的比他从前所有的加倍」（Job.42.10）。《古兰经》中他呼吁「痼疾确已伤害我，你是最仁慈的」（Q021.21.83），真主「解除他所患的痼疾，并以他的家属和同样的人赏赐他」（Q021.21.84）。"))
I("cross_corpus", "both", "medium", ["Gen.19.24", "Q011.11.82"],
  en=("How was Lot's city destroyed, according to the Bible and the Quran?",
      'The Bible says "the Lord rained upon Sodom and upon Gomorrah brimstone and fire from the Lord out of heaven" (Gen.19.24). The Quran says "We overthrew (that township) and rained upon it stones of clay, one after another" (Q011.11.82).'),
  zh=("据圣经和《古兰经》，鲁特（罗得）的城是怎样被毁灭的？",
      "圣经说「耶和华将硫磺与火从天上耶和华那里降与所多玛和蛾摩拉」（Gen.19.24）。《古兰经》说「我使那个市镇天翻地覆，我使预定的连续的陶石像雨点般地降落在他们身上」（Q011.11.82）。"))
I("cross_corpus", "both", "hard", ["1Kgs.18.40", "Q037.37.123", "Q037.37.125"],
  en=("Do both scriptures tell of Elijah (Elias) opposing the worship of Baal?",
      'Yes. In the Bible Elijah says, "Take the prophets of Baal; let not one of them escape" and slays them at the brook Kishon (1Kgs.18.40). The Quran says "Elias was of those sent (to warn)" (Q037.37.123) and he asked his people, "Will ye cry unto Baal and forsake the Best of creators" (Q037.37.125).'),
  zh=("两部经典都记载以利亚（易勒雅斯）反对拜巴力吗？",
      "是的。圣经中以利亚说「拿住巴力的先知，不容一人逃脱」，并在基顺河边杀了他们（1Kgs.18.40）。《古兰经》说「易勒雅斯确是使者」（Q037.37.123），他质问宗族「难道你们祈祷白耳利，而舍弃最优越的创造者」（Q037.37.125）。"))
I("cross_corpus", "both", "medium", ["1Kgs.4.29", "Q027.27.16"],
  en=("How do the Bible and the Quran describe Solomon's wisdom or knowledge?",
      'The Bible: "God gave Solomon wisdom and understanding exceeding much, and largeness of heart, even as the sand that is on the sea shore" (1Kgs.4.29). The Quran has Solomon say, "we have been taught the language of birds, and have been given (abundance) of all things" (Q027.27.16).'),
  zh=("圣经和《古兰经》怎样描述所罗门（素莱曼）的智慧或知识？",
      "圣经：「神赐给所罗门极大的智慧聪明和广大的心，如同海沙不可测量」（1Kgs.4.29）。《古兰经》中素莱曼说「我们曾学会百鸟的语言，我们曾获得万物的享受」（Q027.27.16）。"))
I("cross_corpus", "both", "medium", ["Exod.31.18", "Q007.7.145"],
  en=("Do both the Bible and the Quran mention tablets given to Moses?",
      'Yes. The Bible: "two tables of testimony, tables of stone, written with the finger of God" (Exod.31.18). The Quran: "We wrote for him, upon the tablets, the lesson to be drawn from all things and the explanation of all things" (Q007.7.145).'),
  zh=("圣经和《古兰经》都提到赐给穆萨（摩西）的法版吗？",
      "是的。圣经：「就把两块法版交给他，是神用指头写的石版」（Exod.31.18）。《古兰经》：「我曾为他在法版中制定各种教训和各种解释」（Q007.7.145）。"))
I("cross_corpus", "both", "hard", ["Exod.4.3", "Exod.4.6", "Q020.20.20", "Q020.20.22"],
  en=("Compare the signs of the staff and the hand given to Moses in the Bible and the Quran.",
      'In both, the cast-down staff becomes a serpent: "it became a serpent; and Moses fled from before it" (Exod.4.3); "lo! it was a serpent, gliding" (Q020.20.20). They differ on the hand: in the Bible "his hand was leprous as snow" (Exod.4.6), while the Quran says "it will come forth white without hurt" (Q020.20.22).'),
  zh=("比较圣经和《古兰经》中赐给摩西（穆萨）的杖和手的神迹。",
      "两者都说杖丢在地上变成蛇：「他一丢下去，就变作蛇；摩西便跑开」（Exod.4.3）；「它忽然变成了一条婉蜒的蛇」（Q020.20.20）。关于手则不同：圣经说「手长了大麻疯，有雪那样白」（Exod.4.6），《古兰经》说「手变成雪白的，但是没有甚么疾病」（Q020.20.22）。"))
I("cross_corpus", "both", "medium", ["Gen.37.31", "Q012.12.18"],
  en=("How did Joseph's brothers deceive their father about Joseph, in the Bible and the Quran?",
      'In both they bring his garment stained with blood. The Bible: "they took Joseph’s coat, and killed a kid of the goats, and dipped the coat in the blood" (Gen.37.31). The Quran: "they came with false blood on his shirt", and Jacob answers, "(My course is) comely patience" (Q012.12.18).'),
  zh=("圣经和《古兰经》中，约瑟（优素福）的哥哥们怎样欺骗父亲？",
      "两者都说他们拿来染血的衣服。圣经：「他们宰了一只公山羊，把约瑟的那件彩衣染了血」（Gen.37.31）。《古兰经》：「他们用假血染了优素福的衬衣」，父亲说「我只有很好地忍耐」（Q012.12.18）。"))
I("cross_corpus", "both", "hard", ["Gen.39.12", "Q012.12.25"],
  en=("What happened to Joseph's garment when his master's wife tried to seduce him, in the Bible versus the Quran?",
      'In the Bible she caught him by his garment, and "he left his garment in her hand, and fled" (Gen.39.12). In the Quran they raced to the door "and she tore his shirt from behind" (Q012.12.25).'),
  zh=("主人的妻子引诱约瑟（优素福）时，他的衣服怎么了？圣经与《古兰经》有何不同？",
      "圣经说她拉住他的衣裳，「约瑟把衣裳丢在妇人手里，跑到外边去了」（Gen.39.12）。《古兰经》说他俩奔向大门，「她已把他的衬衣从后面撕破了」（Q012.12.25）。"))
I("cross_corpus", "both", "hard", ["Gen.18.8", "Q011.11.69", "Q011.11.70"],
  en=("Did Abraham's heavenly guests eat the food he served them? Compare the Bible and the Quran.",
      'They differ. The Bible says Abraham set the calf before them "and they did eat" (Gen.18.8). The Quran says he brought "a roasted calf" (Q011.11.69), but "he saw their hands reached not to it" and became afraid (Q011.11.70).'),
  zh=("亚伯拉罕（易卜拉欣）款待的天使吃了他预备的食物吗？比较圣经和《古兰经》。",
      "两者不同。圣经说亚伯拉罕把牛犊摆在他们面前，「他们就吃了」（Gen.18.8）。《古兰经》说他「拿来一只烤犊来」（Q011.11.69），但「他看见他们不伸手去取犊肉」，便有点害怕（Q011.11.70）。"))
I("cross_corpus", "both", "hard", ["Josh.24.2", "Q006.6.74"],
  en=("What do the Bible and the Quran say about Abraham's father and idolatry?",
      'The Bible names him Terah: "Terah, the father of Abraham ... they served other gods" (Josh.24.2). The Quran names him Azar: "Abraham said unto his father Azar: Takest thou idols for gods?" (Q006.6.74).'),
  zh=("圣经和《古兰经》怎样记载亚伯拉罕（易卜拉欣）的父亲与偶像崇拜？",
      "圣经称他为他拉：「亚伯拉罕和拿鹤的父亲他拉，住在大河那边事奉别神」（Josh.24.2）。《古兰经》称他为阿宰尔：「易卜拉欣对他的父亲阿宰尔说：『你把偶像当作主宰吗？』」（Q006.6.74）。"))
I("cross_corpus", "both", "medium", ["Luke.1.13", "Q019.19.7"],
  en=("Who named John the Baptist (Yahya), according to the Bible and the Quran?",
      'In both, God announces the name through the message to Zechariah. The Bible: "thou shalt call his name John" (Luke.1.13). The Quran: "a son whose name is John; we have given the same name to none before (him)" (Q019.19.7).'),
  zh=("据圣经和《古兰经》，施洗约翰（叶哈雅）的名字是谁起的？",
      "两者都说是神借着报喜信息告诉撒迦利亚（宰凯里雅）的。圣经：「你要给他起名叫约翰」（Luke.1.13）。《古兰经》：「他的名字是叶哈雅，我以前没有使任何人与他同名」（Q019.19.7）。"))
I("cross_corpus", "both", "medium", ["Exod.21.24", "Q005.5.45"],
  en=("Is the law of 'an eye for an eye' found in both the Bible and the Quran?",
      'Yes. Exodus: "Eye for eye, tooth for tooth, hand for hand, foot for foot" (Exod.21.24). The Quran, referring to what was prescribed for the Children of Israel: "the eye for the eye ... and the tooth for the tooth, and for wounds retaliation", adding "whoso forgoeth it (in the way of charity) it shall be expiation for him" (Q005.5.45).'),
  zh=("「以眼还眼」的律法在圣经和《古兰经》中都有吗？",
      "有。出埃及记：「以眼还眼，以牙还牙，以手还手，以脚还脚」（Exod.21.24）。《古兰经》说在《讨拉特》中制定「以命偿命，以眼偿眼」等，并补充「自愿不究的人，得以抵偿权自赎其罪愆」（Q005.5.45）。"))
I("cross_corpus", "both", "easy", ["Lev.11.7", "Q002.2.173"],
  en=("Do both the Bible and the Quran forbid eating pork?",
      'Yes. Leviticus: "the swine ... he is unclean to you" (Lev.11.7). The Quran: "He hath forbidden you only carrion, and blood, and swineflesh" (Q002.2.173).'),
  zh=("圣经和《古兰经》都禁止吃猪肉吗？",
      "是的。利未记：「猪」「就与你们不洁净」（Lev.11.7）。《古兰经》：「他只禁戒你们吃自死物、血液、猪肉」（Q002.2.173）。"))
I("cross_corpus", "both", "medium", ["Deut.23.19", "Q002.2.275"],
  en=("What do the Bible and the Quran say about lending at interest (usury)?",
      'Deuteronomy: "Thou shalt not lend upon usury to thy brother" (Deut.23.19). The Quran: "Allah permitteth trading and forbiddeth usury" (Q002.2.275).'),
  zh=("圣经和《古兰经》对放贷取利有什么教导？",
      "申命记：「你借给你弟兄的，或是钱财或是粮食，无论甚么可生利的物，都不可取利」（Deut.23.19）。《古兰经》：「真主准许买卖，而禁止利息」（Q002.2.275）。"))
I("cross_corpus", "both", "medium", ["Gen.2.7", "Q003.3.59"],
  en=("What were humans created from, according to the Bible and the Quran?",
      'Both say dust. The Bible: "the Lord God formed man of the dust of the ground, and breathed into his nostrils the breath of life" (Gen.2.7). The Quran, comparing Jesus to Adam: "He created him of dust, then He said unto him: Be! and he is" (Q003.3.59).'),
  zh=("据圣经和《古兰经》，人是用什么造的？",
      "两者都说是尘土。圣经：「耶和华神用地上的尘土造人，将生气吹在他鼻孔里」（Gen.2.7）。《古兰经》把尔撒比作阿丹：「他用土创造阿丹，然后他对他说：『有』，他就有了」（Q003.3.59）。"))

# --- paraphrase (hard: no keyword overlap with the verse) ---
I("paraphrase", "bible", "hard", ["Eph.4.26"],
  en=("Is there a verse telling you not to go to bed still mad at someone?",
      'Ephesians 4:26: "Be ye angry, and sin not: let not the sun go down upon your wrath" (Eph.4.26).'),
  zh=("有没有经文说不要带着火气过夜？",
      "以弗所书4章26节：「生气却不要犯罪；不可含怒到日落」（Eph.4.26）。"))
I("paraphrase", "bible", "hard", ["Matt.6.28"],
  en=("Where did Jesus point to wildflowers to tell people to stop stressing about what to wear?",
      'Matthew 6:28: "why take ye thought for raiment? Consider the lilies of the field, how they grow; they toil not, neither do they spin" (Matt.6.28).'),
  zh=("耶稣在哪里用野花来劝人不要为穿着焦虑？",
      "马太福音6章28节：「何必为衣裳忧虑呢？你想野地里的百合花怎么长起来；它也不劳苦，也不纺线」（Matt.6.28）。"))
I("paraphrase", "bible", "hard", ["Jas.2.26"],
  en=("Which verse says believing without actually doing anything is like a corpse?",
      'James 2:26: "as the body without the spirit is dead, so faith without works is dead also" (Jas.2.26).'),
  zh=("哪节经文说光相信却不付诸实践就像一具尸体？",
      "雅各书2章26节：「身体没有灵魂是死的，信心没有行为也是死的」（Jas.2.26）。"))
I("paraphrase", "bible", "hard", ["Matt.5.39"],
  en=("Where does Jesus say not to hit back when someone slaps you?",
      'Matthew 5:39: "resist not evil: but whosoever shall smite thee on thy right cheek, turn to him the other also" (Matt.5.39).'),
  zh=("耶稣在哪里说别人扇你耳光时不要还手？",
      "马太福音5章39节：「不要与恶人作对。有人打你的右脸，连左脸也转过来由他打」（Matt.5.39）。"))
I("paraphrase", "bible", "hard", ["1Tim.5.18"],
  en=("Is there a verse saying people who work deserve to get paid?",
      '1 Timothy 5:18: "Thou shalt not muzzle the ox that treadeth out the corn. And, The labourer is worthy of his reward" (1Tim.5.18).'),
  zh=("有没有经文说干活的人理应拿到报酬？",
      "提摩太前书5章18节：「牛在场上踹谷的时候，不可笼住它的嘴」；又说：「工人得工价是应当的」（1Tim.5.18）。"))
I("paraphrase", "bible", "hard", ["2Cor.6.14"],
  en=("Where does Paul warn believers against partnering closely with people who don't share their faith?",
      '2 Corinthians 6:14: "Be ye not unequally yoked together with unbelievers: for what fellowship hath righteousness with unrighteousness?" (2Cor.6.14).'),
  zh=("保罗在哪里提醒信徒不要和不同信仰的人紧密结伙？",
      "哥林多后书6章14节：「你们和不信的原不相配，不要同负一轭。义和不义有甚么相交呢」（2Cor.6.14）。"))
I("paraphrase", "bible", "hard", ["Prov.22.1"],
  en=("Which proverb says your reputation is worth more than being rich?",
      'Proverbs 22:1: "A good name is rather to be chosen than great riches, and loving favour rather than silver and gold" (Prov.22.1).'),
  zh=("哪句箴言说名声比财富更值钱？",
      "箴言22章1节：「美名胜过大财；恩宠强如金银」（Prov.22.1）。"))
I("paraphrase", "bible", "hard", ["Prov.17.28"],
  en=("Which proverb says even a fool can seem smart if he just keeps quiet?",
      'Proverbs 17:28: "Even a fool, when he holdeth his peace, is counted wise: and he that shutteth his lips is esteemed a man of understanding" (Prov.17.28).'),
  zh=("哪句箴言说傻瓜只要不开口也能显得聪明？",
      "箴言17章28节：「愚昧人若静默不言也可算为智慧；闭口不说也可算为聪明」（Prov.17.28）。"))
I("paraphrase", "bible", "hard", ["Prov.26.11"],
  en=("Which proverb compares someone repeating the same stupid mistakes to an animal going back to what it threw up?",
      'Proverbs 26:11: "As a dog returneth to his vomit, so a fool returneth to his folly" (Prov.26.11).'),
  zh=("哪句箴言把一再重犯同样蠢事的人比作回头去吃自己呕吐物的动物？",
      "箴言26章11节：「愚昧人行愚妄事，行了又行，就如狗转过来吃它所吐的」（Prov.26.11）。"))
I("paraphrase", "bible", "hard", ["Prov.26.27"],
  en=("Is there a proverb saying people who set traps for others end up caught in them themselves?",
      'Proverbs 26:27: "Whoso diggeth a pit shall fall therein: and he that rolleth a stone, it will return upon him" (Prov.26.27).'),
  zh=("有没有箴言说给别人设圈套的人最后自己中招？",
      "箴言26章27节：「挖陷坑的，自己必掉在其中；滚石头的，石头必反滚在他身上」（Prov.26.27）。"))
I("paraphrase", "bible", "hard", ["Matt.26.41"],
  en=("Where does Jesus say you may want to do the right thing but your body gives in?",
      'Matthew 26:41: "Watch and pray, that ye enter not into temptation: the spirit indeed is willing, but the flesh is weak" (Matt.26.41).'),
  zh=("耶稣在哪里说人心里想做对的事，身体却撑不住？",
      "马太福音26章41节：「总要警醒祷告，免得入了迷惑。你们心灵固然愿意，肉体却软弱了」（Matt.26.41）。"))
I("paraphrase", "bible", "hard", ["Mark.6.4"],
  en=("Where does Jesus say people back home never respect someone sent by God?",
      'Mark 6:4: "A prophet is not without honour, but in his own country, and among his own kin, and in his own house" (Mark.6.4).'),
  zh=("耶稣在哪里说神差来的人在老家总是不受尊重？",
      "马可福音6章4节：「大凡先知，除了本地、亲属、本家之外，没有不被人尊敬的」（Mark.6.4）。"))
I("paraphrase", "bible", "hard", ["Matt.20.16"],
  en=("Which verse says those at the back of the line will end up at the front?",
      'Matthew 20:16: "So the last shall be first, and the first last" (Matt.20.16).'),
  zh=("哪节经文说排在队尾的人最后会排到前头？",
      "马太福音20章16节：「这样，那在后的，将要在前；在前的，将要在后了」（Matt.20.16）。"),
  notes="CUV appends a textual note (有古卷加) for the second clause.")
I("paraphrase", "bible", "hard", ["Mark.3.25"],
  en=("Which verse says a family that fights among itself can't survive?",
      'Mark 3:25: "if a house be divided against itself, that house cannot stand" (Mark.3.25).'),
  zh=("哪节经文说内斗的家庭撑不下去？",
      "马可福音3章25节：「若一家自相纷争，那家就站立不住」（Mark.3.25）。"))
I("paraphrase", "bible", "hard", ["Matt.5.13"],
  en=("Where does Jesus tell his followers they are what gives the world its flavor?",
      'Matthew 5:13: "Ye are the salt of the earth: but if the salt have lost his savour, wherewith shall it be salted?" (Matt.5.13).'),
  zh=("耶稣在哪里说他的门徒是给世界添味道的？",
      "马太福音5章13节：「你们是世上的盐。盐若失了味，怎能叫它再咸呢」（Matt.5.13）。"))
I("paraphrase", "quran", "hard", ["Q017.17.15"],
  en=("Does the Quran say nobody gets punished for somebody else's wrongdoing?",
      'Yes: "No laden soul can bear another\'s load, We never punish until we have sent a messenger" (Q017.17.15).'),
  zh=("《古兰经》是否说没有人会因别人的过错而受罚？",
      "是的：「一个负罪者，不负他人的罪。派遣使者之前，我不惩罚（任何人）」（Q017.17.15）。"))
I("paraphrase", "quran", "hard", ["Q017.17.31"],
  en=("Is there a Quran verse against getting rid of your kids because you're afraid of going broke?",
      '"Slay not your children, fearing a fall to poverty, We shall provide for them and for you. Lo! the slaying of them is great sin" (Q017.17.31).'),
  zh=("《古兰经》有没有经文反对因为怕穷而不要孩子的性命？",
      "「你们不要因为怕贫穷而杀害自己的儿女，我供给他们和你们。杀害他们确是大罪」（Q017.17.31）。"))
I("paraphrase", "quran", "hard", ["Q049.49.6"],
  en=("Does the Quran tell people to fact-check news brought by an untrustworthy person?",
      '"If an evil-liver bring you tidings, verify it, lest ye smite some folk in ignorance and afterward repent of what ye did" (Q049.49.6).'),
  zh=("《古兰经》是否吩咐人要核实不可靠之人带来的消息？",
      "「如果一个恶人报告你们一个消息，你们应当弄清楚，以免你们无知地伤害他人，到头来悔恨自己的行为」（Q049.49.6）。"))
I("paraphrase", "quran", "hard", ["Q024.24.27"],
  en=("What does the Quran say about knocking and greeting before walking into someone else's home?",
      '"Enter not houses other than your own without first announcing your presence and invoking peace upon the folk thereof" (Q024.24.27).'),
  zh=("《古兰经》对进别人家之前先敲门打招呼有什么教导？",
      "「你们不要进他人的家去，直到你们请求许可，并向主人祝安」（Q024.24.27）。"))
I("paraphrase", "quran", "hard", ["Q042.42.38"],
  en=("Does the Quran praise people who make decisions together by talking things over?",
      'Yes, it praises those "whose affairs are a matter of counsel" (Q042.42.38).'),
  zh=("《古兰经》是否称赞通过商量共同做决定的人？",
      "是的，称赞那些「他们的事务，是由协商而决定的」人（Q042.42.38）。"))
I("paraphrase", "quran", "hard", ["Q083.83.1", "Q083.83.2", "Q083.83.3"],
  en=("Which surah opens by condemning sellers who rig their scales?",
      'Surah 83 (al-Mutaffifin): "Woe unto the defrauders" (Q083.83.1), "Those who when they take the measure from mankind demand it full" (Q083.83.2), "But if they measure unto them or weight for them, they cause them loss" (Q083.83.3).'),
  zh=("哪一章开头就谴责在秤上做手脚的商人？",
      "第83章：「伤哉！称量不公的人们」（Q083.83.1），「当他们从别人称量进来的时候，他们称量得很充足」（Q083.83.2），「当他们量给别人或称给别人的时候，他们不称足不量足」（Q083.83.3）。"))
I("paraphrase", "quran", "hard", ["Q002.2.168"],
  en=("Does the Quran tell all people to eat clean, permitted food and not follow the devil's lead?",
      '"O mankind! Eat of that which is lawful and wholesome in the earth, and follow not the footsteps of the devil" (Q002.2.168).'),
  zh=("《古兰经》是否吩咐世人吃干净许可的食物、不要跟着魔鬼走？",
      "「众人啊！你们可以吃大地上所有合法而且佳美的食物，你们不要随从恶魔的步伐」（Q002.2.168）。"))
I("paraphrase", "quran", "hard", ["Q005.5.1"],
  en=("Is there a Quran verse telling believers to keep their contracts and deals?",
      '"O ye who believe! Fulfil your indentures" (Q005.5.1).'),
  zh=("《古兰经》有没有经文吩咐信士遵守合同和约定？",
      "「信道的人们啊！你们当履行各种约言」（Q005.5.1）。"))
I("paraphrase", "quran", "hard", ["Q002.2.83"],
  en=("Which covenant included being good to your parents and talking nicely to everyone?",
      'The covenant with the Children of Israel: "Worship none save Allah (only), and be good to parents and to kindred and to orphans and the needy, and speak kindly to mankind" (Q002.2.83).'),
  zh=("哪个盟约包括孝敬父母、对人说好话？",
      "与以色列后裔缔结的盟约：「你们应当只崇拜真主，并当孝敬父母，和睦亲戚，怜恤孤儿，赈济贫民，对人说善言」（Q002.2.83）。"))

# --- trap (false premise / misattributed quotes) ---
I("trap", "bible", "easy", ["Gen.6.19"],
  en=("How many animals of each kind did Moses take onto the ark?",
      'False premise: the ark was Noah\'s, not Moses\'s. God told Noah, "two of every sort shalt thou bring into the ark, to keep them alive with thee; they shall be male and female" (Gen.6.19).'),
  zh=("摩西把每种动物各带了几只进方舟？",
      "前提错误：造方舟的是挪亚，不是摩西。神吩咐挪亚：「凡有血肉的活物，每样两个，一公一母，你要带进方舟」（Gen.6.19）。"),
  behavior="correct_premise")
I("trap", "bible", "medium", ["Matt.26.15"],
  en=("Judas betrayed Jesus for forty pieces of silver. Which verse says so?",
      'False premise: it was thirty, not forty: "they covenanted with him for thirty pieces of silver" (Matt.26.15).'),
  zh=("犹大以四十块钱出卖了耶稣，是哪节经文？",
      "前提错误：是三十块，不是四十块：「他们就给了他三十块钱」（Matt.26.15）。"),
  behavior="correct_premise")
I("trap", "bible", "hard", ["Luke.8.2"],
  en=("Which verse says Mary Magdalene was a prostitute?",
      'No verse says that; it is a later tradition. Luke 8:2 only describes her as "Mary called Magdalene, out of whom went seven devils" (Luke.8.2).'),
  zh=("哪节经文说抹大拉的马利亚是妓女？",
      "没有经文这样说，这是后世的传统。路加福音8章2节只说「称为抹大拉的马利亚」，曾有七个鬼从她身上赶出来（Luke.8.2）。"),
  behavior="correct_premise")
I("trap", "bible", "medium", ["Luke.2.7", "Luke.2.8"],
  en=("Which verse says Jesus was born on December 25?",
      'No verse gives a date. Luke says only that Mary "laid him in a manger; because there was no room for them in the inn" (Luke.2.7), while "shepherds abiding in the field, keeping watch over their flock by night" (Luke.2.8).'),
  zh=("哪节经文说耶稣生于12月25日？",
      "没有经文记载日期。路加只说马利亚把他「放在马槽里，因为客店里没有地方」（Luke.2.7），当时「有牧羊的人，夜间按着更次看守羊群」（Luke.2.8）。"),
  behavior="correct_premise")
I("trap", "bible", "medium", ["Matt.6.22"],
  en=("Where does the Bible say \"the eyes are the window to the soul\"?",
      'That saying is not in the Bible. The closest verse is Matthew 6:22: "The light of the body is the eye: if therefore thine eye be single, thy whole body shall be full of light" (Matt.6.22).'),
  zh=("圣经哪里说「眼睛是心灵的窗户」？",
      "圣经中没有这句话。最接近的是马太福音6章22节：「眼睛就是身上的灯。你的眼睛若了亮，全身就光明」（Matt.6.22）。"),
  behavior="correct_premise")
I("trap", "bible", "medium", ["Gen.22.2"],
  en=("In which Bible verse does God tell Abraham to sacrifice Ishmael?",
      'False premise: in the Bible the son named is Isaac: "Take now thy son, thine only son Isaac, whom thou lovest ... and offer him there for a burnt offering" (Gen.22.2).'),
  zh=("圣经哪节经文记载神吩咐亚伯拉罕献以实玛利？",
      "前提错误：圣经中点名的是以撒：「你带着你的儿子，就是你独生的儿子，你所爱的以撒，往摩利亚地去」「把他献为燔祭」（Gen.22.2）。"),
  behavior="correct_premise")
I("trap", "bible", "hard", ["Phil.4.5"],
  en=("Which Bible verse says \"Moderation in all things\"?",
      'That proverb is not in the Bible (it is classical Greek). The nearest wording is Philippians 4:5: "Let your moderation be known unto all men. The Lord is at hand" (Phil.4.5).'),
  zh=("圣经哪节经文说「凡事要适度」（Moderation in all things）？",
      "圣经中没有这句格言（它出自古希腊）。英文KJV中最接近的是腓立比书4章5节，和合本译作「当叫众人知道你们谦让的心。主已经近了」（Phil.4.5）。"),
  behavior="correct_premise")
I("trap", "quran", "medium", ["Q018.18.50"],
  en=("The Quran says Iblis was the chief of the angels. Which verse says that?",
      'False premise: the Quran says the angels prostrated "all save Iblis. He was of the jinn, so he rebelled against his Lord\'s command" (Q018.18.50).'),
  zh=("《古兰经》说易卜劣厮是众天神之首，是哪节经文？",
      "前提错误：经文说众天神都叩了头，「但易卜劣厮除外。他本是精灵，所以违背他的主的命令」（Q018.18.50）。"),
  behavior="correct_premise")
I("trap", "quran", "hard", ["Q037.37.142", "Q037.37.144"],
  en=("According to the Quran, how many days was Jonah inside the fish?",
      'The Quran gives no number of days. It says "the fish swallowed him while he was blameworthy" (Q037.37.142) and that, but for his glorifying God, "He would have tarried in its belly till the day when they are raised" (Q037.37.144).'),
  zh=("据《古兰经》，优努斯（约拿）在鱼腹中待了几天？",
      "《古兰经》没有说天数。它说「大鱼就吞了他，同时，他是应受谴责的」（Q037.37.142），若不是他赞颂真主，「他必葬身鱼腹，直到世人复活之日」（Q037.37.144）。"),
  behavior="correct_premise")
I("trap", "quran", "medium", ["Q019.19.16"],
  en=("Which surah of the Quran is named after Jesus?",
      'None is. Surah 19 is named after his mother Mary and says "make mention of Mary in the Scripture" (Q019.19.16).'),
  zh=("《古兰经》哪一章以尔撒（耶稣）命名？",
      "没有。第19章以他的母亲麦尔彦命名，经文说「你应当在这部经典里提及麦尔彦」（Q019.19.16）。"),
  behavior="correct_premise")
I("trap", "bible", "medium", [],
  en=("Which Bible verse says \"Hate the sin, love the sinner\"?",
      "No verse in the Bible (KJV) says this; it is a later paraphrase usually traced to Augustine and Gandhi. The system should say it is not a Bible quotation."),
  zh=("哪节经文说「恨罪人所犯的罪，却爱罪人」？",
      "圣经（和合本）中没有这句话，它是后人的说法（常被归于奥古斯丁和甘地）。系统应说明这不是圣经原文。"),
  behavior="not_found")
I("trap", "bible", "easy", [],
  en=("Where in the Bible does it say \"To thine own self be true\"?",
      "Nowhere: it is a line from Shakespeare's Hamlet, not the Bible. The system should say it is not a Bible quotation."),
  zh=("圣经哪里说「对你自己要忠实」（To thine own self be true）？",
      "圣经中没有这句话，它出自莎士比亚的《哈姆雷特》。系统应说明这不是圣经原文。"),
  behavior="not_found")
I("trap", "quran", "medium", [],
  en=("Which Quran verse says \"Cleanliness is half of faith\"?",
      "No Quran verse says this; it is a hadith (reported saying of the Prophet), not part of the Quran. The system should say it is not in the Quran."),
  zh=("《古兰经》哪节经文说「清洁是信仰的一半」？",
      "《古兰经》中没有这句话，它出自圣训，不是《古兰经》经文。系统应说明这不在《古兰经》中。"),
  behavior="not_found")
I("trap", "bible", "easy", [],
  en=("Quote the Bible verse \"Charity begins at home\".",
      "That proverb is not in the Bible. The system should say so instead of quoting an unrelated verse."),
  zh=("请引用圣经中「慈善从家里开始」这节经文。",
      "圣经中没有这句谚语。系统应说明这一点，而不是引用无关经文。"),
  behavior="not_found")

# --- numbering: references that do not exist ---
I("numbering", "bible", "medium", [],
  en=("What does Genesis 51:1 say?",
      "There is no Genesis 51:1: Genesis has 50 chapters. The system should say the reference does not exist."),
  zh=("创世记51章1节说什么？",
      "没有创世记51章1节：创世记只有50章。系统应说明该经文不存在。"),
  behavior="not_found")
I("numbering", "bible", "medium", [],
  en=("Quote John 22:1.",
      "There is no John 22:1: the Gospel of John has 21 chapters. The system should say the reference does not exist."),
  zh=("请引用约翰福音22章1节。",
      "没有约翰福音22章1节：约翰福音只有21章。系统应说明该经文不存在。"),
  behavior="not_found")
I("numbering", "bible", "hard", [],
  en=("What does Psalm 151 say?",
      "The KJV Book of Psalms has 150 psalms; Psalm 151 is not in this corpus. The system should say so."),
  zh=("诗篇第151篇说什么？",
      "和合本诗篇只有150篇，本语料中没有第151篇。系统应说明这一点。"),
  behavior="not_found")
I("numbering", "bible", "medium", [],
  en=("What does Jude 2:1 say?",
      "There is no Jude 2:1: the Epistle of Jude has only one chapter. The system should say the reference does not exist."),
  zh=("犹大书2章1节说什么？",
      "没有犹大书2章1节：犹大书只有一章。系统应说明该经文不存在。"),
  behavior="not_found")
I("numbering", "quran", "medium", [],
  en=("What is Surah 115 of the Quran about?",
      "There is no Surah 115: the Quran has 114 surahs. The system should say the reference does not exist."),
  zh=("《古兰经》第115章讲什么？",
      "没有第115章：《古兰经》共114章。系统应说明该章不存在。"),
  behavior="not_found")
I("numbering", "quran", "medium", [],
  en=("What does verse 287 of Surah al-Baqarah say?",
      "There is no verse 287: Surah al-Baqarah (Surah 2) has 286 verses. The system should say the reference does not exist."),
  zh=("《黄牛章》第287节说什么？",
      "没有第287节：《黄牛章》（第2章）共286节。系统应说明该经文不存在。"),
  behavior="not_found")

# --- negative (out of scope) ---
NEG2 = [
    ("What does 1 Maccabees say about the rededication of the Temple?", "《马加比一书》怎样记载圣殿的重新献殿？"),
    ("Summarize the Book of Tobit.", "请概述《多俾亚传》。"),
    ("What does the Book of Mormon say about the Nephites?", "《摩尔门经》怎样描述尼腓人？"),
    ("What does the Bhagavad Gita teach about karma yoga?", "《薄伽梵歌》怎样讲业瑜伽？"),
    ("What do the Analects of Confucius say about filial piety?", "《论语》怎样谈孝道？"),
    ("What does the Hadith of Gabriel say about ihsan?", "吉卜利勒圣训对“至善”（伊赫萨尼）怎么说？"),
    ("What does the Talmud say about the Oral Torah?", "《塔木德》怎样论述口传律法？"),
    ("What did Martin Luther write in his Ninety-five Theses?", "马丁·路德在《九十五条论纲》中写了什么？"),
    ("What is the capital of Australia?", "澳大利亚的首都是哪里？"),
    ("How does photosynthesis work?", "光合作用的原理是什么？"),
    ("Write a SQL query that counts the rows in a table.", "写一条统计表中行数的SQL语句。"),
    ("Which Bible verse mentions the Roman Colosseum?", "哪节经文提到罗马斗兽场？"),
    ("Which surah mentions the city of Baghdad?", "哪一章提到巴格达城？"),
    ("What will the weather be in Jerusalem tomorrow?", "明天耶路撒冷的天气怎么样？"),
]
for en_q, zh_q in NEG2:
    I("negative", "none", "easy", [],
      en=(en_q, "The Bible (KJV) and Quran corpora contain no passage on this topic; the system should say so instead of citing unrelated verses."),
      zh=(zh_q, "圣经（和合本）和《古兰经》语料中没有涉及该主题的经文；系统应说明找不到，而不是引用无关经文。"),
      behavior="not_found")
# ============================== NUMBERING (exact ref resolution, versification edge cases) ==============================
I("numbering", "bible", "medium", ["Ps.23.1"],
  en=("What is Psalm 23 verse 1?",
      "\"The LORD is my shepherd; I shall not want\" (Ps.23.1)."),
  zh=("诗篇23篇1节是什么？",
      "「耶和华是我的牧者，我必不致缺乏。」（Ps.23.1）和合本把标题「大卫的诗」并入第1节。"),
  notes="CUV includes the psalm superscription inside v.1")
I("numbering", "bible", "easy", ["Ps.23.4"],
  en=("What does Psalm 23:4 say?",
      "\"Yea, though I walk through the valley of the shadow of death, I will fear no evil: for thou art with me; thy rod and thy staff they comfort me\" (Ps.23.4)."),
  zh=("诗篇23篇4节说什么？",
      "「我虽然行过死荫的幽谷，也不怕遭害，因为你与我同在；你的杖，你的竿，都安慰我。」（Ps.23.4）"))
I("numbering", "bible", "medium", ["Ps.117.1", "Ps.117.2"],
  en=("Quote the whole of Psalm 117, the shortest psalm.",
      "\"O praise the LORD, all ye nations: praise him, all ye people. For his merciful kindness is great toward us: and the truth of the LORD endureth for ever. Praise ye the LORD\" (Ps.117.1-2)."),
  zh=("请引用最短的一篇诗篇——诗篇117篇全文。",
      "「万国啊，你们都当赞美耶和华！万民哪，你们都当颂赞他！因为他向我们大施慈爱；耶和华的诚实存到永远。你们要赞美耶和华！」（Ps.117.1-2）"))
I("numbering", "bible", "medium", ["John.11.35"],
  en=("What is the shortest verse in the English Bible (John 11:35)?",
      "\"Jesus wept\" (John.11.35)."),
  zh=("约翰福音11章35节是什么？",
      "「耶稣哭了。」（John.11.35）"))
I("numbering", "bible", "medium", ["Ps.119.176"],
  en=("What is the last verse of Psalm 119?",
      "Psalm 119:176: \"I have gone astray like a lost sheep; seek thy servant; for I do not forget thy commandments\" (Ps.119.176)."),
  zh=("诗篇119篇的最后一节是什么？",
      "诗篇119篇176节：「我如亡羊走迷了路，求你寻找仆人，因我不忘记你的命令。」（Ps.119.176）"))
I("numbering", "bible", "hard", ["Ps.51.1", "Ps.51.10"],
  en=("What do Psalm 51:1 and 51:10 say?",
      "\"Have mercy upon me, O God, according to thy lovingkindness...\" (Ps.51.1) and \"Create in me a clean heart, O God; and renew a right spirit within me\" (Ps.51.10)."),
  zh=("诗篇51篇1节和10节说什么？",
      "「神啊，求你按你的慈爱怜恤我！按你丰盛的慈悲涂抹我的过犯！」（Ps.51.1，和合本把标题并入第1节）以及「神啊，求你为我造清洁的心，使我里面重新有正直（或译：坚定）的灵。」（Ps.51.10）"),
  notes="Hebrew numbering would shift these by 2; corpus follows KJV/CUV versification")
I("numbering", "bible", "hard", ["Mal.4.5", "Mal.4.6"],
  en=("What do Malachi 4:5-6 say?",
      "God will send Elijah the prophet before the great and dreadful day of the LORD, and he shall turn the heart of the fathers to the children (Mal.4.5-6)."),
  zh=("玛拉基书4章5至6节说什么？",
      "耶和华大而可畏之日未到以前，我必差遣先知以利亚到你们那里去；他必使父亲的心转向儿女，儿女的心转向父亲（Mal.4.5-6）。"),
  notes="Hebrew Bibles number these Mal.3.23-24; corpus uses KJV/CUV numbering")
I("numbering", "bible", "hard", ["3John.1.14"],
  en=("What is the last verse of 3 John?",
      "In the KJV it is 3 John 1:14: \"But I trust I shall shortly see thee... Peace be to thee. Our friends salute thee. Greet the friends by name\" (3John.1.14)."),
  zh=("约翰三书的最后一节是什么？",
      "和合本中是约翰三书15节：「愿你平安。众位朋友都问你安。请你替我按着姓名问众位朋友安。」第14节是「但盼望快快地见你，我们就当面谈论。」（3John.1.14, 3John.1.15）"),
  zh_refs=["3John.1.14", "3John.1.15"],
  notes="KJV has 14 verses; CUV splits v14 into 14-15")
I("numbering", "bible", "hard", ["Rev.13.1"],
  en=("In Revelation, who stands upon the sand of the sea just before the beast rises out of the sea, and in which verse?",
      "In the KJV it is the seer himself, at the start of Revelation 13:1: \"And I stood upon the sand of the sea, and saw a beast rise up out of the sea...\" (Rev.13.1). The KJV has no verse 12:18; other versions (e.g. CUV) put the dragon standing on the sand at 12:18."),
  zh=("启示录中「龙就站在海边的沙上」是哪一节？",
      "和合本是启示录12章18节：「那时龙就站在海边的沙上。」（Rev.12.18）KJV 没有12:18，其13:1开头作“我站在海边的沙上”（经文异读）。"),
  zh_refs=["Rev.12.18"],
  notes="KJV lacks Rev.12.18; CUV has it")
I("numbering", "bible", "hard", ["John.7.53", "John.8.1"],
  en=("What do John 7:53 and 8:1 say?",
      "\"And every man went unto his own house\" (John.7.53); \"Jesus went unto the mount of Olives\" (John.8.1)."),
  zh=("约翰福音7章53节和8章1节说什么？",
      "和合本把这两节合在8章1节：「于是各人都回家去了；耶稣却往橄榄山去」（John.8.1）。语料中和合本没有单独的7:53。"),
  zh_refs=["John.8.1"],
  notes="CUV corpus merges 7:53 into 8:1")
I("numbering", "bible", "medium", ["Gen.1.1", "Rev.22.21"],
  en=("What are the first and last verses of the Bible?",
      "First: \"In the beginning God created the heaven and the earth\" (Gen.1.1). Last: \"The grace of our Lord Jesus Christ be with you all. Amen\" (Rev.22.21)."),
  zh=("圣经的第一节和最后一节是什么？",
      "第一节：「起初，神创造天地。」（Gen.1.1）最后一节：「愿主耶稣的恩惠常与众圣徒同在。阿们！」（Rev.22.21）"))

I("numbering", "quran", "easy", ["Q002.2.255"],
  en=("What is verse 255 of Surah 2 (al-Baqarah)?",
      "Ayat al-Kursi: \"Allah! There is no deity save Him, the Alive, the Eternal...\" (Q002.2.255)."),
  zh=("第2章（黄牛章）第255节是什么？",
      "即宝座经：「真主，除他外绝无应受崇拜的，他是永生不灭的，是维护万物的……」（Q002.2.255）"))
I("numbering", "quran", "medium", ["Q001.1.1", "Q001.1.7"],
  en=("What are the first and last verses of Surah al-Fatiha?",
      "Verse 1 is the basmala: \"In the name of Allah, the Beneficent, the Merciful\" (Q001.1.1); verse 7: \"The path of those whom Thou hast favoured; Not (the path) of those who earn Thine anger nor of those who go astray\" (Q001.1.7)."),
  zh=("《开端》章的第一节和最后一节是什么？",
      "第1节是泰斯米：「奉至仁至慈的真主之名」（Q001.1.1）；第7节：「你所祐助者的路，不是受谴怒者的路，也不是迷误者的路。」（Q001.1.7）"),
  notes="In Hafs numbering the basmala is verse 1 of al-Fatiha only")
I("numbering", "quran", "medium", ["Q002.2.286"],
  en=("What is the last verse of Surah al-Baqarah?",
      "Verse 286: \"Allah tasketh not a soul beyond its scope...\" ending with a prayer for pardon and help against the disbelieving folk (Q002.2.286)."),
  zh=("《黄牛》章的最后一节是什么？",
      "第286节：「真主只依各人的能力而加以责成……」以祈求恕饶和援助结束（Q002.2.286）。"))
I("numbering", "quran", "easy", ["Q108.108.1", "Q108.108.2", "Q108.108.3"],
  en=("Quote the whole of Surah al-Kawthar, the shortest surah.",
      "\"Lo! We have given thee Abundance; So pray unto thy Lord, and sacrifice. Lo! it is thy insulter (and not thou) who is without posterity\" (Q108.108.1-3)."),
  zh=("请引用最短的一章——《多福》章（第108章）全文。",
      "「我确已赐你多福，故你应当为你的主而礼拜，并宰牺牲。怨恨你者，确是绝后的。」（Q108.108.1-3）"))
I("numbering", "quran", "medium", ["Q114.114.1", "Q114.114.6"],
  en=("What are the first and last verses of the final surah of the Quran?",
      "Surah 114 begins \"Say: I seek refuge in the Lord of mankind\" (Q114.114.1) and ends \"Of the jinn and of mankind\" (Q114.114.6)."),
  zh=("《古兰经》最后一章的第一节和最后一节是什么？",
      "第114章开头：「你说：我求庇于世人的主宰」（Q114.114.1），结尾：「他是属于精灵和人类的。」（Q114.114.6）"))
# ============================== GENERATED (data-driven) ITEMS ==============================
# These items are generated at build time from the corpus text itself, so the
# answer is always a verbatim quote of the cited verse(s). Only the ref lists
# below are hand-curated. Each entry is a ref or a list of 1-3 consecutive refs.
#   GEN_LOOKUP : "What does <Book c:v> say?"            -> verse text      (verse_lookup)
#   GEN_QUOTE  : "Which verse says '<fragment>'?"       -> ref + verse text (verse_lookup)
#   GEN_XL     : quote in the OTHER language's text     -> ref + text in the question language (cross_lingual)
# Fragments are the shortest leading clause(s) that are unique within that
# translation; the build fails if no unique fragment exists.

GEN_LOOKUP: list = []
GEN_QUOTE: list = []
GEN_XL: list = []
NAMES: dict = {}
NAME_FIX = {("en", "Rev"): "Revelation", ("zh", "Rev"): "启示录"}          # (translation, book_code) -> book_name, filled by load()

_SPLIT = {"en": re.compile(r"(?<=[,;:.?!])\s+"), "zh": re.compile(r"(?<=[，；：。？！])")}
_MIN = {"en": 28, "zh": 8}


def _as_list(e):
    return e if isinstance(e, list) else [e]


def _span(refs):
    b, c, v = refs[0].split(".")
    if len(refs) == 1:
        return b, int(c), v
    return b, int(c), f"{v}-{refs[-1].split('.')[2]}"


def _cite(refs):
    if len(refs) == 1:
        return refs[0]
    b, c, v = refs[0].split(".")
    return f"{refs[0]}-{refs[-1].split('.')[2]}"


def _human(refs, lang):
    b, c, v = _span(refs)
    tr = LANG_TR[lang][corpus_of(refs[0])]
    name = NAME_FIX.get((lang, b)) or NAMES.get((tr, b), b)
    if lang == "en" and b == "Ps" and len(refs) == 1:
        name = "Psalm"
    if b.startswith("Q"):
        return (f"Surah {c} ({name}), verse{'s' if '-' in v else ''} {v}" if lang == "en"
                else f"《{name}》章（第{c}章）第{v.replace('-', '至')}节")
    if lang == "en":
        return f"{name} {c}:{v}"
    unit = "篇" if b == "Ps" else "章"
    return f"{name}{c}{unit}{v.replace('-', '至')}节"


def _text(idx, refs, lang):
    tr = LANG_TR[lang][corpus_of(refs[0])]
    parts = []
    for r in refs:
        t = idx.get((tr, r))
        if not t or not t.strip():
            raise KeyError(f"generated item: {r} missing/empty in {tr}")
        parts.append(t.strip())
    return (" " if lang == "en" else "").join(parts)


_TEXTS_BY_TR: dict = {}
_QUOTES = {"zh": re.compile(r"[「」『』“”‘’\"]"), "en": re.compile(r"[“”\"]")}
_PAREN = re.compile(r"\s*[（(][^（）()]*[）)]\s*")
_SPEECH_EN = re.compile(r"\b(said|saith|saying|spake|answered|cried)\b", re.I)


def _norm(text, lang):
    """Normalise a verse for quoting: drop quote marks and parenthetical notes."""
    t = _QUOTES[lang].sub("", text)
    t = _PAREN.sub(" " if lang == "en" else "", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([,;:.!?])", r"\1", t)
    t = re.sub(r"([,;:])[,;:]+", r"\1", t)
    return t.lstrip(" ,;:")


def _pool(idx, tr, lang):
    if tr not in _TEXTS_BY_TR:
        _TEXTS_BY_TR[tr] = [_norm(t, lang) for (t2, _r), t in idx.items() if t2 == tr]
    return _TEXTS_BY_TR[tr]


def _unique(pool, frag):
    return sum(1 for t in pool if frag in t) == 1


def _fragment(idx, ref, lang, override=None):
    tr = LANG_TR[lang][corpus_of(ref)]
    pool = _pool(idx, tr, lang)
    text = _norm(idx[(tr, ref)], lang)
    if override:
        if override not in text:
            raise ValueError(f"override fragment {override!r} not in {ref} ({tr})")
        if not _unique(pool, override):
            raise ValueError(f"override fragment {override!r} not unique in {tr}")
        return override
    clauses = [c for c in _SPLIT[lang].split(text) if c.strip()]
    # drop leading speech introductions ("And he said unto them," / "耶稣对他说：")
    while len(clauses) > 1:
        c2 = clauses[0].strip()
        if lang == "zh" and (c2.endswith("说：") or c2.endswith("说:") or c2.endswith("说，")):
            clauses = clauses[1:]
            continue
        if lang == "en" and _SPEECH_EN.search(c2) and len(c2.split()) <= 8:
            clauses = clauses[1:]
            continue
        break
    frag = ""
    for c in clauses:
        frag = (frag + (" " if lang == "en" and frag else "") + c.strip())
        core = frag.rstrip(" ,;:.?!，；：。？！—-")
        if len(core) >= _MIN[lang] and _unique(pool, core):
            return core
    for cand in (frag.rstrip(" ,;:.?!，；：。？！—-"), text.rstrip(" ,;:.?!，；：。？！—-")):
        if cand and _unique(pool, cand):
            return cand
    raise ValueError(f"no unique fragment for {ref} in {tr}")


_Q_LOOKUP = {"en": ["What does {h} say?", "Quote {h}.", "What is written in {h}?"],
             "zh": ["{h}说什么？", "请引用{h}。", "{h}的经文是什么？"]}
_Q_QUOTE = {"en": ['Which verse says "{f}"?', 'Where is "{f}" found?', 'Give the reference for: "{f}".'],
            "zh": ["「{f}」出自哪节经文？", "哪节经文说「{f}」？", "「{f}」是哪一节？"]}
_Q_XL = {"en": ["Which verse reads 「{f}」 in Chinese, and what does it say in English?",
                "Find the English text of the verse that says 「{f}」.",
                "A Chinese reader quotes 「{f}」. Which verse is it, in English?"],
         "zh": ['英文中写作 "{f}" 的是哪节经文？中文怎么说？',
                '请找出英文为 "{f}" 的经文，并给出中文译文。',
                '有人引用英文 "{f}"，这是哪一节？中文经文是什么？']}


def _ans(idx, refs, lang, with_place):
    t = _text(idx, refs, lang)
    cite = _cite(refs)
    if lang == "en":
        return (f"{_human(refs, lang)}: \"{t}\" ({cite})." if with_place else f"\"{t}\" ({cite}).")
    # CUV verses often open/close a speech quote mid-paragraph; drop unbalanced
    # brackets and turn nested ones into 『』 so the answer quote is well formed.
    if t.count("「") > t.count("」") and t.startswith("「"):
        t = t[1:]
    if t.count("」") > t.count("「") and t.endswith("」"):
        t = t[:-1]
    while t.count("「") > t.count("」"):
        i = t.rindex("「"); t = t[:i] + t[i + 1:]
    while t.count("」") > t.count("「"):
        i = t.index("」"); t = t[:i] + t[i + 1:]
    t = t.replace("「", "『").replace("」", "』")
    return (f"{_human(refs, lang)}：「{t}」（{cite}）" if with_place else f"「{t}」（{cite}）")


def expand_generated(idx, errors):
    used = collections.defaultdict(set)    # category -> refs already used
    for it in ITEMS:
        for r in (it["refs"] or []) + (it["en_refs"] or []) + (it["zh_refs"] or []):
            used[it["cat"]].add(r)
    specs = ([("verse_lookup", "L", e) for e in GEN_LOOKUP] + [("verse_lookup", "Q", e) for e in GEN_QUOTE]
             + [("cross_lingual", "X", e) for e in GEN_XL])
    for n, (cat, kind, e) in enumerate(specs):
        ov = {"en": None, "zh": None}
        if isinstance(e, tuple):
            e, ov["en"], ov["zh"] = e
        refs = _as_list(e)
        where = f"generated {kind}:{refs}"
        if any(r in used[cat] for r in refs):
            errors.append(f"{where}: ref already used in another {cat} item")
            continue
        used[cat].update(refs)
        try:
            qa = {}
            for lang in ("en", "zh"):
                k = n % 3
                if kind == "L":
                    q = _Q_LOOKUP[lang][k].format(h=_human(refs, lang)); a = _ans(idx, refs, lang, False)
                elif kind == "Q":
                    q = _Q_QUOTE[lang][k].format(f=_fragment(idx, refs[0], lang, ov[lang])); a = _ans(idx, refs, lang, True)
                else:
                    q = _Q_XL[lang][k].format(f=_fragment(idx, refs[0], OTHER[lang], ov[OTHER[lang]])); a = _ans(idx, refs, lang, True)
                qa[lang] = (q, a)
        except (KeyError, ValueError) as ex:
            errors.append(f"{where}: {ex}")
            continue
        corpus = corpus_of(refs[0])
        diff = {"L": "easy", "Q": "medium", "X": "medium"}[kind]
        ITEMS.append(dict(cat=cat, corpus=corpus, diff=diff, refs=refs, en=qa["en"], zh=qa["zh"],
                          en_refs=None, zh_refs=None, behavior="answer",
                          notes="generated: answer is the verbatim verse text"))
# ---- curated ref lists for generated items ----
GEN_LOOKUP += [
    "Gen.1.27", "Gen.2.7", "Gen.2.24", "Gen.3.19", "Gen.12.1", "Gen.15.6", "Gen.50.20",
    "Exod.3.14", "Exod.15.2", "Exod.20.12", "Lev.11.44", ["Num.6.24", "Num.6.25", "Num.6.26"],
    "Deut.6.4", "Deut.31.6", "Josh.1.9", "Judg.21.25", "Ruth.4.17", "1Sam.15.22", "2Sam.22.2",
    "1Kgs.19.12", "2Chr.7.14", "Neh.8.10", "Esth.4.14", "Job.1.21", "Job.19.25", "Ps.1.1",
    "Ps.19.1", "Ps.27.1", "Ps.37.4", "Ps.90.12", "Ps.103.12", "Ps.121.1", "Ps.139.14",
    "Prov.3.9", "Prov.4.23", "Prov.16.9", "Prov.22.6", "Eccl.12.13", "Song.8.7", "Isa.1.18",
    "Isa.9.6", "Isa.53.5", "Isa.55.8", "Jer.17.9", ["Lam.3.22", "Lam.3.23"], "Ezek.36.26",
    "Dan.12.3", "Hos.6.6", "Joel.2.28", "Amos.5.24", "Hab.2.4", "Zech.4.6", "Mal.3.10",
    "Matt.5.14", "Matt.6.33", "Matt.5.16", "Matt.24.35", "Mark.10.45", "Luke.2.14",
    "Luke.19.10", "John.10.10", "John.11.25", "John.15.13", "Acts.1.8", "Acts.4.12",
    "Rom.12.2", "Rom.10.9", "1Cor.10.31", "2Cor.5.17", "Gal.2.20", "Eph.6.11", "Phil.4.6",
    "Col.3.23", ["1Thess.5.16", "1Thess.5.17", "1Thess.5.18"], "2Tim.3.16", "Heb.13.8",
    "Jas.1.5", "1Pet.5.7", "1John.1.9", "1John.4.8", "Rev.21.4", "Rev.3.20",
    "Ezra.7.10", "2Kgs.2.11", "1Chr.16.34", "Obad.1.15", "Hag.1.5", "Titus.2.11", "Phlm.1.16",
    "2Pet.3.9", "Jude.1.24", "2John.1.6", "2Thess.3.10",
    # Quran
    "Q002.2.2", "Q002.2.21", "Q002.2.30", "Q002.2.45", "Q002.2.115", "Q002.2.177", "Q002.2.197",
    "Q002.2.216", "Q002.2.257", "Q003.3.8", "Q003.3.26", "Q003.3.92", "Q003.3.103", "Q003.3.110",
    "Q003.3.190", "Q004.4.1", "Q004.4.36", "Q006.6.59", "Q006.6.162", "Q007.7.31", "Q007.7.199",
    "Q008.8.2", "Q009.9.51", "Q010.10.57", "Q012.12.87", "Q014.14.24", "Q015.15.9", "Q016.16.97",
    "Q016.16.125", "Q017.17.1", "Q017.17.70", "Q017.17.81", "Q018.18.46", "Q020.20.114",
    "Q021.21.30", "Q021.21.107", "Q023.23.115", "Q024.24.30", "Q029.29.45", "Q030.30.21",
    "Q033.33.21", "Q035.35.15", "Q039.39.10", "Q040.40.60", "Q042.42.11", "Q051.51.56",
    ["Q055.55.26", "Q055.55.27"], "Q057.57.4", ["Q059.59.22", "Q059.59.23", "Q059.59.24"],
    "Q064.64.16", "Q065.65.3", "Q067.67.2", "Q076.76.8", "Q087.87.1", "Q089.89.27",
    "Q095.95.4", ["Q099.99.7", "Q099.99.8"], ["Q103.103.1", "Q103.103.2"], "Q105.105.1",
    "Q110.110.1", "Q113.113.1",
]
GEN_QUOTE += [
    ("Gen.4.9", "Am I my brother’s keeper", None), "Gen.18.14", "Exod.14.14", "Exod.33.14", "Deut.8.3", "Josh.24.15", ("1Sam.3.10", "Speak; for thy servant heareth", "像前三次呼唤说：撒母耳啊！撒母耳啊"),
    "1Sam.17.47", "2Sam.12.7", ("1Kgs.18.21", "How long halt ye between two opinions", "你们心持两意要到几时呢"), "Job.38.4", "Ps.8.4", "Ps.34.8", "Ps.42.1",
    "Ps.118.24", "Ps.127.1", "Ps.133.1", "Ps.150.6", "Prov.9.10", "Prov.11.2", "Prov.18.10",
    "Prov.31.10", "Eccl.11.1", "Isa.6.8", "Isa.7.14", "Isa.26.3", "Isa.43.2", "Jer.1.5",
    ("Jer.31.3", "I have loved thee with an everlasting love", "我以永远的爱爱你"), "Ezek.37.4", "Dan.3.17", "Mic.5.2", "Nah.1.7", "Zeph.3.17", "Matt.4.4",
    "Matt.5.9", ("Matt.16.18", "upon this rock I will build my church", "我要把我的教会建造在这磐石上"), "Matt.22.37", "Mark.8.36", "Mark.16.15", ("Luke.1.37", None, "出于神的话，没有一句不带能力的"),
    "Luke.23.34", "John.8.32", "John.13.34", "John.20.29", "Acts.2.38", "Acts.16.31", "Rom.5.8",
    "Rom.12.21", "2Cor.9.7", "Eph.4.32", "Phil.1.21", "Col.3.2", "1Tim.4.12", "Heb.12.1",
    "Jas.4.8", "1Pet.3.15", "1John.4.18", "Rev.1.8", ("Judg.6.12", "The Lord is with thee, thou mighty man of valour", None), "Ruth.3.11", ("Neh.6.3", "I am doing a great work, so that I cannot come down", "我现在办理大工，不能下去"),
    "Esth.8.17", "2Kgs.6.16", "Joel.2.13", "Amos.3.3", "Hag.2.9", "Jonah.2.9",
    # Quran
    "Q002.2.110", "Q002.2.148", "Q002.2.165", "Q002.2.201", "Q002.2.214", "Q003.3.139",
    "Q003.3.159", "Q003.3.173", "Q004.4.28", "Q004.4.79", "Q006.6.103", "Q007.7.23", "Q008.8.30",
    "Q011.11.6", "Q011.11.88", "Q014.14.34", "Q016.16.18", "Q017.17.9", "Q017.17.85",
    "Q018.18.109", "Q020.20.25", "Q021.21.35", ("Q021.21.87", "Dhu'n-Nun, when he went off in anger", None), "Q023.23.1", "Q025.25.74",
    "Q028.28.77", "Q029.29.69", "Q031.31.17", "Q033.33.56", "Q039.39.9", "Q047.47.7",
    "Q049.49.10", "Q053.53.39", "Q057.57.20", "Q062.62.10", "Q063.63.9", "Q064.64.11",
    "Q065.65.2", "Q066.66.6", "Q067.67.1", ("Q071.71.10", "Seek pardon of your Lord", None), "Q084.84.6", "Q089.89.28",
    "Q091.91.9", "Q092.92.5", "Q096.96.5", "Q100.100.6", "Q101.101.4",
]
GEN_XL += [
    "Gen.1.3", "Exod.20.8", "Ps.23.6", "Ps.100.1", "Prov.29.18", "Prov.15.3", "Isa.11.9",
    "Jer.33.3", "Matt.5.3", "Matt.5.4", "Matt.5.5", "Matt.5.6", "Matt.5.7", "Matt.5.8",
    "Matt.6.34", ("Matt.19.26", "With men this is impossible; but with God all things are possible", "在人这是不能的，在神凡事都能"), "John.1.5", "John.6.35", "John.8.12", "John.10.11", "John.14.27",
    "Rom.1.16", "1Cor.16.14", "Gal.6.9", "Eph.2.10", ("Phil.4.4", None, "你们要靠主常常喜乐"), "Heb.4.12", "Jas.1.22",
    "1John.3.18", "Rev.22.13", "Ps.46.1", "Isa.41.10", "Num.23.19", "Deut.6.5",
    # Quran
    "Q001.1.4", "Q001.1.5", ("Q003.3.31", "If ye love Allah, follow me", None), "Q003.3.200", "Q004.4.86", "Q006.6.164", "Q007.7.56",
    ("Q017.17.36", "follow not that whereof thou hast no knowledge", None), "Q020.20.46", "Q028.28.88", "Q039.39.36", "Q040.40.44", "Q049.49.11",
    "Q055.55.60", "Q059.59.18", "Q065.65.7", "Q073.73.8", "Q094.94.1", "Q097.97.5", "Q113.113.5",
]

# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------
REF_RE = re.compile(r"^(Q\d{3}|[1-3]?[A-Z][A-Za-z]+)\.(\d+)\.(\d+)$")


def find_data_dir(cli: str | None) -> Path:
    cands = [cli, os.environ.get("BIBLE_RAG_DATA"), HERE.parent.parent / "data",
             HERE.parent / "data", Path("/workspace/bible")]
    for c in cands:
        if c and all(resolve(Path(c), t) for t in FILES):
            return Path(c)
    sys.exit("ERROR: could not find corpus data dir (need kjv/cuv/quran_en/quran_zh jsonl). "
             "Pass --data-dir or set BIBLE_RAG_DATA.")


def resolve(root: Path, tr: str) -> Path | None:
    for rel in FILES[tr]:
        p = root / rel
        if p.is_file():
            return p
    return None


def load(root: Path) -> dict:
    idx = {}
    for tr in FILES:
        p = resolve(root, tr)
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                v = json.loads(line)
                NAMES.setdefault((tr, v["book_code"]), v.get("book_name") or v["book_code"])
                idx[(tr, f"{v['book_code']}.{v['chapter']}.{v['verse']}")] = v["text"]
    return idx


def corpus_of(ref: str) -> str:
    return "quran" if ref.startswith("Q") else "bible"


def ctx(idx, ref, lang, errors, where):
    if not REF_RE.match(ref):
        errors.append(f"{where}: malformed ref {ref!r}")
        return None
    tr = LANG_TR[lang][corpus_of(ref)]
    text = idx.get((tr, ref))
    if text is None:
        errors.append(f"{where}: ref {ref} not found in {tr}")
        return None
    if not text.strip():
        errors.append(f"{where}: ref {ref} is empty in {tr}")
        return None
    return {"canon_ref": ref, "translation": tr, "text": text}


def build(idx):
    out = {"en": [], "zh": []}
    errors = []
    for n, it in enumerate(ITEMS):
        where = f"item#{n} ({it['cat']})"
        if it["cat"] not in CATEGORIES:
            errors.append(f"{where}: unknown category")
        for lang in ("en", "zh"):
            qa = it[lang]
            if qa is None:
                continue
            refs = it[f"{lang}_refs"] if it[f"{lang}_refs"] is not None else it["refs"]
            beh = it["behavior"]
            answerable = beh != "not_found"
            if beh == "not_found" and refs:
                errors.append(f"{where}/{lang}: not_found item must have no refs")
            if answerable and not refs:
                errors.append(f"{where}/{lang}: answerable item needs refs")
            if len(refs) > 5:
                errors.append(f"{where}/{lang}: more than 5 refs")
            if len(set(refs)) != len(refs):
                errors.append(f"{where}/{lang}: duplicate refs")
            corpora = {corpus_of(r) for r in refs}
            exp_corpus = it["corpus"]
            if refs and exp_corpus != "both" and corpora != {exp_corpus}:
                errors.append(f"{where}/{lang}: corpus {exp_corpus} but refs are {corpora}")
            if exp_corpus == "both" and corpora != {"bible", "quran"}:
                errors.append(f"{where}/{lang}: corpus both needs refs from both")
            q, a = qa
            if not q.strip() or not a.strip():
                errors.append(f"{where}/{lang}: empty question/answer")
            # every ref must be cited in the answer
            for r in refs:
                book, ch, v = r.split(".")
                if book not in a:
                    errors.append(f"{where}/{lang}: answer does not cite {r}")
            contexts = [c for c in (ctx(idx, r, lang, errors, f"{where}/{lang}") for r in refs) if c]
            rec = {
                "id": None, "lang": lang, "corpus": exp_corpus, "category": it["cat"],
                "difficulty": it["diff"], "question": q, "expected_answer": a,
                "expected_refs": refs, "expected_contexts": contexts,
                "answerable": answerable, "expected_behavior": beh,
            }
            if it["cat"] == "cross_lingual":
                o = OTHER[lang]
                orefs = it[f"{o}_refs"] if it[f"{o}_refs"] is not None else it["refs"]
                rec["parallel_contexts"] = [c for c in (ctx(idx, r, o, errors, f"{where}/{lang}-parallel")
                                                        for r in orefs) if c]
            if it["notes"]:
                rec["notes"] = it["notes"]
            out[lang].append(rec)
    # duplicate questions
    for lang, recs in out.items():
        seen = collections.Counter(r["question"] for r in recs)
        for qq, c in seen.items():
            if c > 1:
                errors.append(f"{lang}: duplicate question {qq!r}")
        for i, r in enumerate(recs, 1):
            r["id"] = f"{lang}-{i:03d}"
    return out, errors


SMOKE_PER_CATEGORY = 3


def smoke_subset(out):
    """Deterministic ~50-item subset for fast CI: SMOKE_PER_CATEGORY items per
    category, evenly spaced through the category, taken in both languages
    (same item number in en and zh), ids preserved."""
    zh_by_num = {r["id"].split("-", 1)[1]: r for r in out["zh"]}
    picked = []
    for cat in CATEGORIES:
        en_cat = [r for r in out["en"] if r["category"] == cat]
        n = len(en_cat)
        if not n:
            continue
        k = min(SMOKE_PER_CATEGORY, n)
        for i in range(k):
            r = en_cat[(i * n) // k + (n // (2 * k))]
            z = zh_by_num[r["id"].split("-", 1)[1]]
            assert z["category"] == cat, (r["id"], z["id"])
            picked.extend([r, z])
    return picked


def stats(out):
    allr = out["en"] + out["zh"]
    print(f"TOTAL items: {len(allr)}")
    for key in ("lang", "corpus", "category", "difficulty", "expected_behavior"):
        c = collections.Counter(r[key] for r in allr)
        print(f"  by {key}: " + ", ".join(f"{k}={v}" for k, v in sorted(c.items())))
    print("  category x lang:")
    for cat in CATEGORIES:
        e = sum(1 for r in out["en"] if r["category"] == cat)
        z = sum(1 for r in out["zh"] if r["category"] == cat)
        print(f"    {cat:<14} en={e:<3} zh={z:<3} total={e + z}")
    b = sum(1 for r in allr if r["corpus"] == "bible")
    q = sum(1 for r in allr if r["corpus"] == "quran")
    both = sum(1 for r in allr if r["corpus"] == "both")
    none = sum(1 for r in allr if r["corpus"] == "none")
    print(f"  bible={b} quran={q} both={both} none={none}  "
          f"(bible share of single-corpus: {b / max(1, b + q):.0%})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir")
    ap.add_argument("--out-dir", default=str(HERE))
    ap.add_argument("--check", action="store_true", help="validate only, do not write files")
    args = ap.parse_args()
    root = find_data_dir(args.data_dir)
    print(f"data dir: {root}")
    idx = load(root)
    gen_errors = []
    expand_generated(idx, gen_errors)
    out, errors = build(idx)
    errors = gen_errors + errors
    if errors:
        print(f"\n{len(errors)} VALIDATION ERROR(S):", file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
        sys.exit(1)
    if not args.check:
        od = Path(args.out_dir)
        od.mkdir(parents=True, exist_ok=True)
        for lang, recs in out.items():
            p = od / f"golden_{lang}.jsonl"
            with open(p, "w", encoding="utf-8") as fh:
                for r in recs:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"wrote {p} ({len(recs)} items)")
        smoke = smoke_subset(out)
        p = od / "golden_smoke.jsonl"
        with open(p, "w", encoding="utf-8") as fh:
            for r in smoke:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"wrote {p} ({len(smoke)} items)")
    stats(out)


if __name__ == "__main__":
    main()
