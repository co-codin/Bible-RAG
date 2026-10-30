import { MOCK_VERSES } from './mockData'
import { fullLabel, zhTranslationFor } from './refs'
import type { AskRequest, AskResponse, Corpus, Lang, Source, VerseRecord } from './types'

type Topic = 'forgiveness' | 'love' | 'patience'

interface Snippet {
  answer: Record<Lang, string>
  refs: string[] // canon refs, in rank order
}

// Canned answers. Scripture is NEVER written here: verse texts come from mockData.ts
// (generated from the real jsonl files); answers only paraphrase and cite.
const ANSWERS: Record<Topic, Partial<Record<Corpus, Snippet>>> = {
  forgiveness: {
    bible: {
      answer: {
        en: 'The Bible ties receiving forgiveness to extending it: Jesus teaches that the Father forgives those who forgive others [[Matt.6.14]], and warns of the reverse [[Matt.6.15]]. Believers are told to be kind and tenderhearted, forgiving one another as God in Christ forgave them [[Eph.4.32]] [[Col.3.13]]. God himself is described as faithful and just to forgive those who confess their sins [[1John.1.9]].',
        zh: '圣经把"得饶恕"和"饶恕人"连在一起：耶稣教导，你们饶恕人的过犯，天父也必饶恕你们 [[Matt.6.14]]，反之亦然 [[Matt.6.15]]。信徒要以恩慈相待、存怜悯的心，像神在基督里饶恕我们一样彼此饶恕 [[Eph.4.32]] [[Col.3.13]]。经上也说，我们若认罪，神是信实公义的，必要赦免我们的罪 [[1John.1.9]]。',
      },
      refs: ['Matt.6.14', 'Eph.4.32', 'Col.3.13', 'Matt.6.15', '1John.1.9'],
    },
    quran: {
      answer: {
        en: 'The Quran praises those who are patient and forgive, calling it a matter of firm resolve [[Q042.42.43]], and urges people of means to pardon and overlook, since they too hope for God\'s forgiveness [[Q024.24.22]].',
        zh: '古兰经称赞既能忍耐又肯原谅别人的人，认为这是需要坚定意志的美德 [[Q042.42.43]]；也劝富足的人不要因为别人的过错就停止帮助亲属和穷人，而要宽容对方，正如他们自己也希望得到真主的宽恕 [[Q024.24.22]]。',
      },
      refs: ['Q042.42.43', 'Q024.24.22'],
    },
  },
  love: {
    bible: {
      answer: {
        en: 'In the Bible, love is rooted in God\'s own nature: "God is love" [[1John.4.8]], shown most clearly in giving his Son for the world [[John.3.16]]. Paul describes love (KJV "charity") as patient and kind, not envious or boastful [[1Cor.13.4]], and ranks it above faith and hope [[1Cor.13.13]].',
        zh: '圣经里，爱源于神的本性——“神就是爱” [[1John.4.8]]，最清楚的表现是神赐下独生子给世人 [[John.3.16]]。保罗说爱是恒久忍耐、又有恩慈，不嫉妒、不自夸 [[1Cor.13.4]]；信、望、爱三样之中，最大的是爱 [[1Cor.13.13]]。',
      },
      refs: ['1John.4.8', '1Cor.13.4', 'John.3.16', '1Cor.13.13'],
    },
  },
  patience: {
    quran: {
      answer: {
        en: 'The Quran repeatedly links patience with faith. Believers are told to seek help through steadfastness and prayer, for God is with the steadfast [[Q002.2.153]]; they will be tested with fear, hunger and loss, and good news is given to the patient [[Q002.2.155]]. They are urged to endure and outdo others in endurance [[Q003.3.200]], and the steadfast are promised a reward without measure [[Q039.39.10]]. Surah Al-Asr names exhorting one another to endurance among the marks of those who are not lost [[Q103.103.3]].',
        zh: '古兰经多次把忍耐和信仰联系在一起：信徒要靠忍耐和礼拜寻求帮助，因为真主与忍耐的人同在 [[Q002.2.153]]；人会经历恐惧、饥饿和财物、生命的损失等考验，而忍耐的人会得到好消息 [[Q002.2.155]]。信徒被劝勉要坚持到底、比别人更能忍耐 [[Q003.3.200]]，忍耐的人将得到不计其数的回报 [[Q039.39.10]]。第 103 章说，彼此劝勉坚守真理和忍耐的人，不属于亏损的人 [[Q103.103.3]]。',
      },
      refs: ['Q002.2.153', 'Q002.2.155', 'Q003.3.200', 'Q039.39.10', 'Q103.103.3'],
    },
    bible: {
      answer: {
        en: 'In the Bible, patience appears as a mark of love: love "suffereth long" [[1Cor.13.4]].',
        zh: '在圣经里，忍耐是爱的标志之一：爱是恒久忍耐 [[1Cor.13.4]]。',
      },
      refs: ['1Cor.13.4'],
    },
  },
}

const NOT_FOUND: Record<Lang, string> = {
  en: 'I could not find passages in the selected corpus that answer this question, so I will not guess. Try another wording or widen the corpus filter.',
  zh: '在所选经典里没有检索到能回答这个问题的经文，所以不作猜测。可以换个问法，或者放宽经典筛选。',
}

function detectTopic(q: string): Topic | null {
  const s = q.toLowerCase()
  if (/forgiv|pardon|饶恕|宽恕|赦免|原谅/.test(s)) return 'forgiveness'
  if (/patien|steadfast|endur|忍耐|坚忍|耐心/.test(s)) return 'patience'
  if (/love|charity|爱/.test(s)) return 'love'
  return null
}

function toSource(ref: string, lang: Lang, score: number): Source {
  const rec = MOCK_VERSES[ref]
  return {
    canonRef: ref,
    corpus: rec.corpus,
    label: fullLabel(rec, lang),
    translation: lang === 'en' ? rec.en.translation : (rec.zh?.translation ?? zhTranslationFor(rec.corpus)),
    text: lang === 'en' ? rec.en.text : (rec.zh?.text ?? null),
    score,
  }
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

export async function mockAsk(req: AskRequest): Promise<AskResponse> {
  const t0 = performance.now()
  await sleep(700)
  const topic = detectTopic(req.question)
  const corpora: Corpus[] = req.corpus === 'all' ? ['bible', 'quran'] : [req.corpus]
  // If the question names a corpus and the filter is "all", prefer that corpus.
  const q = req.question.toLowerCase()
  const named: Corpus | null = /quran|koran|古兰/.test(q) ? 'quran' : /bible|圣经/.test(q) ? 'bible' : null
  const use = req.corpus === 'all' && named ? [named] : corpora

  const parts: string[] = []
  const refs: string[] = []
  if (topic) {
    for (const c of use) {
      const snip = ANSWERS[topic][c]
      if (!snip) continue
      parts.push(snip.answer[req.lang])
      refs.push(...snip.refs)
    }
  }
  const topK = req.topK ?? 6
  const sources = refs.slice(0, topK).map((r, i) => toSource(r, req.lang, Math.round((0.91 - i * 0.047) * 1000) / 1000))
  return {
    answer: parts.length ? parts.join('\n\n') : NOT_FOUND[req.lang],
    sources,
    lang: req.lang,
    latencyMs: Math.round(performance.now() - t0),
    mode: 'mock',
  }
}

export async function mockGetVerse(canonRef: string): Promise<VerseRecord> {
  await sleep(150)
  const rec = MOCK_VERSES[canonRef]
  if (!rec) throw new Error(`Verse ${canonRef} is not in the mock dataset`)
  return rec
}

export function mockVerseSync(canonRef: string): VerseRecord | undefined {
  return MOCK_VERSES[canonRef]
}
