"""Input and output guardrails for the generation pipeline.

Input: length limit, prompt-injection patterns, an off-topic check
(questions that are not about Bible or Quran text are refused politely),
and a cheap bge-m3 dense similarity check against in-domain / out-of-domain
prototypes. Hard rule refusals always stand; the semantic layer can allow a
cue-less but clearly in-domain question, or refuse a cued but clearly
out-of-domain one. No LLM is used on this path.

Output: every cited canon_ref must be among the retrieved refs (unknown refs
are stripped; if none remain, the answer is refused), a basic tone check, and
a requirement that a substantive answer cite at least one retrieved ref.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from bible_rag.api.schemas import MAX_QUERY_LEN
from bible_rag.generation.topic import (
    DenseEmbedder,
    TopicChecker,
    TopicDecision,
    get_checker,
)
from bible_rag.retrieval.hybrid import Hit

REPO_ROOT = Path(__file__).resolve().parents[3]

# --- language & messages ----------------------------------------------------


def detect_lang(text: str) -> str:
    return "zh" if re.search(r"[\u4e00-\u9fff]", text) else "en"


REFUSAL_MESSAGES: dict[str, dict[str, str]] = {
    "too_long": {
        "en": "Your question is too long. Please shorten it and try again.",
        "zh": "问题过长，请缩短后再试。",
    },
    "injection": {
        "en": (
            "I can only answer questions about the Bible or the Quran, "
            "and I cannot follow instructions that try to override that."
        ),
        "zh": "我只能回答与圣经或古兰经有关的问题，不能执行试图覆盖这一限制的指令。",
    },
    "off_topic": {
        "en": (
            "I can only answer questions about the text of the Bible or the Quran. "
            "Please ask about a passage, teaching, or story from those scriptures."
        ),
        "zh": "我只能回答与圣经或古兰经经文有关的问题。请就其中的经文、教导或记载提问。",
    },
    "uncited_ref": {
        "en": "The draft answer cited verses that were not in the retrieved passages, so it was not shown.",
        "zh": "草稿答案引用了检索结果中没有的经文，因此未展示。",
    },
    "no_citation": {
        "en": "The draft answer did not cite any retrieved verse, so it was not shown.",
        "zh": "草稿答案没有引用检索到的经文，因此未展示。",
    },
    "tone": {
        "en": "The draft answer did not meet the tone requirements, so it was not shown.",
        "zh": "草稿答案不符合语气要求，因此未展示。",
    },
}

NOT_FOUND: dict[str, str] = {
    "en": (
        "I could not find passages in the selected corpus that answer this question, "
        "so I will not guess. Try another wording or widen the corpus filter."
    ),
    "zh": "在所选经典里没有检索到能回答这个问题的经文，所以不作猜测。可以换个问法，或者放宽经典筛选。",
}


def refusal_message(reason: str, lang: str) -> str:
    table = REFUSAL_MESSAGES.get(reason, REFUSAL_MESSAGES["off_topic"])
    return table.get(lang, table["en"])


@dataclass(frozen=True)
class GuardDecision:
    ok: bool
    reason: str | None = None
    message: str | None = None
    answer: str | None = None
    citations: list[str] = field(default_factory=list)


# --- input: injection -------------------------------------------------------

# Patterns target instruction-override attempts, not ordinary words like "ignore"
# in a scripture question ("you are now in Christ" is intentionally not matched).
_INJECTION = re.compile(
    r"""
    (
        ignore\s+(all\s+|any\s+|the\s+)?(previous|prior|above|preceding|your)\s+
            (instructions|instruction|prompts|prompt|rules|rule)
        | ignore\s+your\s+(instructions|prompt|rules|programming)
        | disregard\s+(all\s+|any\s+|the\s+)?(previous|prior|above|your)\s+
            (instructions|prompt|rules)
        | override\s+(your\s+)?(system|previous|prior|safety)\s+(prompt|instructions|rules)
        | reveal\s+(me\s+)?(your\s+)?(system\s+)?(prompt|instructions|hidden\s+rules)
        | (system|hidden)\s+prompt
        | jailbreak
        | \bdo\s+anything\s+now\b
        | \bdeveloper\s+mode\b
        | pretend\s+you\s+(are|have)\s+no\s+(rules|limits|restrictions)
        | 忽略\s*(以上|之前|上面|先前|全部|所有)?\s*(的)?\s*(指令|提示|提示词|规则|设定)
        | 无视\s*(以上|之前|上面)?\s*(的)?\s*(指令|提示|规则)
        | 你现在是
        | (揭示|透露|显示|打印)\s*(你的)?\s*(系统)?\s*(提示词|提示|指令)
        | 越狱
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# --- input: off-topic -------------------------------------------------------

_OTHER_CANON = re.compile(
    r"""
    (
        book\s+of\s+mormon | bhagavad\s+gita | \btalmud\b | \bhadith\b
        | analects | \bavesta\b | \bbuddha\b | four\s+noble\s+truths
        | \bconfucius\b | \bkaran\b | \bvedas?\b | upanishad
        | ninety[- ]five\s+theses | \bquran\s+of\s+the\s+latter
        | book\s+of\s+tobit | \btobit\b | book\s+of\s+judith
        | \b[12]\s*maccabees | wisdom\s+of\s+solomon | \becclesiasticus
        | \bsirach\b | book\s+of\s+baruch
        | 摩门(\s*经)? | 摩尔门 | 薄伽梵歌 | 塔木德 | 圣训 | 论语 | 佛陀 | 阿维斯塔
        | 四谛 | 孔子 | 吠陀
        | 多俾亚 | 多比传 | 友弟德 | 玛加比 | 馬加比 | 德训篇 | 智慧篇 | 巴录书 | 巴錄書
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

_BIBLE_OR_QURAN = re.compile(
    r"""
    (
        \bbible\b | \bbiblical\b | \bscripture[s]?\b | \bkjv\b | \bcuv\b
        | chinese\s+union | \bquran\b | \bkoran\b | qur['’]an
        | 圣经 | 和合本 | 古兰经 | 古蘭經 | 古兰 | 古蘭
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


# English book names that are also ordinary words or given names. Only treat
# them as scripture cues when a chapter number follows or "book of" is used.
_AMBIGUOUS_EN_BOOKS = frozenset(
    {
        "Job",
        "Numbers",
        "Judges",
        "Ruth",
        "Esther",
        "Mark",
        "Luke",
        "John",
        "Acts",
        "James",
        "Jude",
        "Titus",
        "Daniel",
        "Amos",
        "Joel",
        "Jonah",
        "Micah",
        "Nahum",
        "Matthew",
        "Joshua",
        "Ezra",
        "Timothy",
        "Peter",
        "Samuel",
        "Kings",
        "Chronicles",
    }
)


def _load_name_terms() -> list[str]:
    """Book and surah names. Latin terms use word boundaries; OSIS codes only
    count when a chapter number follows, so short codes like 'Am' or 'Job'
    cannot mark an ordinary sentence as on-topic."""
    terms: list[str] = []
    books = REPO_ROOT / "data" / "bible" / "books.json"
    if books.exists():
        data = json.loads(books.read_text(encoding="utf-8"))
        for entry in data.values():
            osis = (entry.get("osis") or "").strip()
            if osis:
                terms.append(rf"\b{re.escape(osis)}\.?\s*\d+")
            en = (entry.get("en") or "").strip()
            if en:
                escaped = re.escape(en)
                terms.append(rf"\bbook of {escaped}\b")
                terms.append(rf"\b{escaped}\.?\s*\d+")
                if en not in _AMBIGUOUS_EN_BOOKS:
                    terms.append(rf"\b{escaped}\b")
            zh = (entry.get("zh") or "").strip()
            if zh:
                terms.append(re.escape(zh))
                for suffix in ("福音", "记", "书"):
                    if zh.endswith(suffix) and len(zh) > len(suffix):
                        terms.append(re.escape(zh[: -len(suffix)]))
    surahs = REPO_ROOT / "data" / "quran" / "surahs.json"
    if surahs.exists():
        for entry in json.loads(surahs.read_text(encoding="utf-8")):
            code = (entry.get("code") or "").strip()
            if code:
                terms.append(rf"\b{re.escape(code)}\b")
            for key in ("translit", "en"):
                value = (entry.get(key) or "").strip()
                if value and len(value) >= 5:
                    terms.append(rf"\b{re.escape(value)}\b")
            zh = (entry.get("zh") or "").strip()
            if zh:
                terms.append(re.escape(zh))
    return terms


_NAME_TERMS = _load_name_terms()
_NAME_RE = re.compile("|".join(_NAME_TERMS), re.IGNORECASE) if _NAME_TERMS else None

_SCRIPTURE_CUE = re.compile(
    r"""
    (
        \bverse[s]?\b | \bchapter[s]?\b | \bpsalm[s]?\b | \bproverb[s]?\b
        | \bgospel\b | \bepistle\b | \btestament\b | \btorah\b | \bpentateuch\b
        | \bsurah[s]?\b | \bsura\b | \bayah\b | \bayat\b | \bcanon_ref\b
        | book\s+of | gospel\s+of
        | give\s+the\s+reference | finish\s+the\s+quotation | \bcite\s+it\b
        | where\s+is\s+[“"'] | 哪一节 | 哪节 | 出自哪里 | 出自哪 | 下文是什么
        | \bthe\s+ark\b | \blydia\b | \banak\b | \bgog\b | \bmagog\b
        | dhu'?l-?qarneyn | dhul[- ]qarnayn | \bbabylon
        | 路得 | 以斯帖 | 方舟 | 巴比伦 | 挪亚 | 叶哈雅 | 宰凯里雅
        | \b(jesus|christ|moses|abraham|isaac|jacob|israel|david|solomon
            | isaiah|jeremiah|elijah|elisha|samuel|noah|adam|eve|mary
            | joseph|paul|peter|john|matthew|luke|timothy|pharaoh
            | muhammad|allah|yahweh|jehovah|messiah|apostle[s]?|disciple[s]?
            | prophet[s]?|commandment[s]?|beatitude[s]?|resurrection|crucifixion
            | covenant|baptism|passover|sabbath)\b
        | 经文 | 诗篇 | 箴言 | 福音 | 旧约 | 新约 | 律法 | 诫命
        | 苏勒 | 素蕾 | 章节 | 耶酥 | 耶稣 | 基督 | 摩西 | 亚伯拉罕
        | 大卫 | 所罗门 | 穆罕默德 | 真主 | 上帝 | 耶和华 | 先知
        | 门徒 | 使徒 | 复活 | 约书亚 | 保罗 | 彼得
        | \bQ\d{1,3}\b | \b[1-3]?[A-Z][a-z]{1,5}\.\d+\.\d+\b
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _has_scripture_cue(text: str) -> bool:
    if _BIBLE_OR_QURAN.search(text) or _SCRIPTURE_CUE.search(text):
        return True
    return bool(_NAME_RE and _NAME_RE.search(text))


def _hard_rules(stripped: str, *, max_len: int, lang: str) -> GuardDecision | None:
    """Refusals that the semantic layer must not override."""
    if not stripped:
        return GuardDecision(False, "too_long", refusal_message("too_long", lang))
    if len(stripped) > max_len:
        return GuardDecision(False, "too_long", refusal_message("too_long", lang))
    if _INJECTION.search(stripped):
        return GuardDecision(False, "injection", refusal_message("injection", lang))
    # Other-canon questions are off-topic unless they also ask about the Bible or Quran.
    if _OTHER_CANON.search(stripped) and not _BIBLE_OR_QURAN.search(stripped):
        return GuardDecision(False, "off_topic", refusal_message("off_topic", lang))
    return None


def check_input(
    query: str,
    *,
    max_len: int = MAX_QUERY_LEN,
    embedder: DenseEmbedder | None = None,
    checker: TopicChecker | None = None,
    use_semantic: bool | None = None,
) -> GuardDecision:
    """Length, injection, and other-canon rules, then an optional bge-m3 topic check.

    Hard rule refusals always stand. If a topic checker is available:
    clearly in-domain questions are allowed even without a scripture cue;
    clearly out-of-domain questions are refused even with a cue; the
    ambiguous band keeps the cue-based rule (no cue -> refuse, else allow).
    """
    lang = detect_lang(query)
    stripped = query.strip()
    hard = _hard_rules(stripped, max_len=max_len, lang=lang)
    if hard is not None:
        return hard
    has_cue = _has_scripture_cue(stripped)

    topic: TopicDecision | None = None
    if use_semantic is False:
        topic = None
    else:
        active = checker
        if active is None:
            active = get_checker(embedder)
        if active is not None:
            topic = active.decide(stripped)

    if topic is not None and topic.clearly_in:
        return GuardDecision(True)
    if topic is not None and topic.clearly_out:
        return GuardDecision(False, "off_topic", refusal_message("off_topic", lang))
    if not has_cue:
        return GuardDecision(False, "off_topic", refusal_message("off_topic", lang))
    return GuardDecision(True)


# --- output: citations & tone ----------------------------------------------

# [[Matt.6.14]]  (Matt.6.14)  （Q002.2.255）  and a bare Matt.6.14 / Q002.2.255
_CITE_BRACKETS = re.compile(r"\[\[([^\]]+)\]\]")
_CITE_PARENS = re.compile(r"[（(]([^）)]+)[）)]")
_BARE_REF = re.compile(r"\b((?:[1-3]?[A-Za-z][A-Za-z]+|Q\d{1,3})\.\d+\.\d+)\b")
_QURAN_SHORT = re.compile(r"\bQ(\d{1,3})[:.](\d+)\b", re.IGNORECASE)

_TONE = re.compile(
    r"""
    (
        \b(idiot|stupid|dumbass|kill\s+yourself|hate\s+you)\b
        | \bfuck|\bshit\b|\bdamn\s+you
        | my\s+(system\s+)?(prompt|instructions)\s+(are|is|say)
        | as\s+an\s+ai\s+(i\s+was|programmed|my\s+instructions)
        | 操你 | 去死 | 傻逼 | 我的(系统)?(提示词|指令)是
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

_NOT_FOUND_ANSWER = re.compile(
    r"""
    (
        could\s+not\s+find
        | i\s+will\s+not\s+guess
        | not\s+(found|in\s+the\s+(bible|quran|scriptures|retrieved))
        | no\s+(relevant\s+)?(passage|verse|ayah)
        | 没有检索到 | 找不到 | 没有找到 | 不作猜测 | 无法在.{0,12}(圣经|古兰经)
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def normalize_ref(ref: str) -> str:
    value = ref.strip().strip("[]()（）").strip()
    # Q002.2.255 already canonical; Q2.2.255 -> Q002.2.255
    m = re.fullmatch(r"Q(\d{1,3})\.(\d+)\.(\d+)", value, re.IGNORECASE)
    if m:
        return f"Q{int(m.group(1)):03d}.{int(m.group(2))}.{int(m.group(3))}"
    # Q2:255 or Q2.255 (surah number == chapter)
    m = re.fullmatch(r"Q(\d{1,3})[:.](\d+)", value, re.IGNORECASE)
    if m:
        surah, verse = int(m.group(1)), int(m.group(2))
        return f"Q{surah:03d}.{surah}.{verse}"
    return value


def retrieved_refs(hits: list[Hit]) -> set[str]:
    return {normalize_ref(ref) for hit in hits for ref in hit.canon_refs}


def extract_citations(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        # A parenthetical may be a whole sentence; only keep if it looks like a ref.
        cand = raw.strip()
        if not (
            re.fullmatch(r"(?:[1-3]?[A-Za-z][A-Za-z]+|Q\d{1,3})\.\d+\.\d+", cand)
            or re.fullmatch(r"Q\d{1,3}[:.]\d+", cand, re.IGNORECASE)
        ):
            return
        key = normalize_ref(cand)
        if key not in seen:
            seen.add(key)
            found.append(key)

    for match in _CITE_BRACKETS.finditer(text):
        add(match.group(1))
    for match in _CITE_PARENS.finditer(text):
        add(match.group(1))
    for match in _BARE_REF.finditer(text):
        add(match.group(1))
    for match in _QURAN_SHORT.finditer(text):
        add(f"Q{match.group(1)}:{match.group(2)}")
    return found


def _strip_unallowed(text: str, allowed: set[str]) -> str:
    def keep_bracket(match: re.Match[str]) -> str:
        key = normalize_ref(match.group(1))
        return match.group(0) if key in allowed else ""

    def keep_paren(match: re.Match[str]) -> str:
        raw = match.group(1).strip()
        if not re.fullmatch(r"(?:[1-3]?[A-Za-z][A-Za-z]+|Q\d{1,3})\.\d+\.\d+", raw):
            return match.group(0)
        return match.group(0) if normalize_ref(raw) in allowed else ""

    out = _CITE_BRACKETS.sub(keep_bracket, text)
    out = _CITE_PARENS.sub(keep_paren, out)
    out = _BARE_REF.sub(lambda m: m.group(0) if normalize_ref(m.group(1)) in allowed else "", out)
    return re.sub(r"[ \t]{2,}", " ", out).strip()


def check_output(answer: str, hits: list[Hit], *, lang: str = "en") -> GuardDecision:
    text = (answer or "").strip()
    if _TONE.search(text):
        return GuardDecision(False, "tone", refusal_message("tone", lang))
    allowed = retrieved_refs(hits)
    cited = extract_citations(text)
    unknown = [ref for ref in cited if ref not in allowed]
    if unknown:
        stripped = _strip_unallowed(text, allowed)
        remaining = [ref for ref in extract_citations(stripped) if ref in allowed]
        if not remaining:
            return GuardDecision(False, "uncited_ref", refusal_message("uncited_ref", lang))
        return GuardDecision(True, answer=stripped, citations=remaining)
    if not cited:
        if _NOT_FOUND_ANSWER.search(text) or not hits:
            return GuardDecision(True, answer=text, citations=[])
        return GuardDecision(False, "no_citation", refusal_message("no_citation", lang))
    return GuardDecision(True, answer=text, citations=cited)
