import { useState, type FormEvent, type KeyboardEvent } from 'react'
import type { CorpusFilter, Lang } from '../api/types'

export interface AskParams {
  question: string
  corpus: CorpusFilter
  lang: Lang
}

interface Props {
  loading: boolean
  initial?: Partial<AskParams>
  onAsk: (p: AskParams) => void
}

export const EXAMPLES: { text: string; corpus: CorpusFilter; lang: Lang }[] = [
  { text: 'What does the Bible say about forgiveness?', corpus: 'bible', lang: 'en' },
  { text: '圣经里怎么讲爱？', corpus: 'bible', lang: 'zh' },
  { text: 'What does the Quran say about patience?', corpus: 'quran', lang: 'en' },
  { text: '古兰经怎么讲坚忍？', corpus: 'quran', lang: 'zh' },
]

const CORPORA: { value: CorpusFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'bible', label: 'Bible' },
  { value: 'quran', label: 'Quran' },
]
const LANGS: { value: Lang; label: string }[] = [
  { value: 'en', label: 'English' },
  { value: 'zh', label: '中文' },
]

function Segmented<T extends string>(props: {
  label: string
  value: T
  options: { value: T; label: string }[]
  onChange: (v: T) => void
}) {
  return (
    <div className="seg-group">
      <span className="seg-label">{props.label}</span>
      <div className="segmented" role="radiogroup" aria-label={props.label}>
        {props.options.map((o) => (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={props.value === o.value}
            className={props.value === o.value ? 'active' : ''}
            onClick={() => props.onChange(o.value)}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function AskBox({ loading, initial, onAsk }: Props) {
  const [question, setQuestion] = useState(initial?.question ?? '')
  const [corpus, setCorpus] = useState<CorpusFilter>(initial?.corpus ?? 'all')
  const [lang, setLang] = useState<Lang>(initial?.lang ?? 'en')

  const submit = (e?: FormEvent) => {
    e?.preventDefault()
    const q = question.trim()
    if (!q || loading) return
    onAsk({ question: q, corpus, lang })
  }

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      submit()
    }
  }

  const pick = (ex: (typeof EXAMPLES)[number]) => {
    setQuestion(ex.text)
    setCorpus(ex.corpus)
    setLang(ex.lang)
    onAsk({ question: ex.text, corpus: ex.corpus, lang: ex.lang })
  }

  return (
    <form className="card askbox" onSubmit={submit}>
      <div className="ask-input-row">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={onKey}
          placeholder="Ask a question about the Bible or the Quran…  / 用中文提问也可以"
          rows={2}
          aria-label="Question"
        />
        <button className="ask-btn" type="submit" disabled={loading || !question.trim()}>
          {loading ? <span className="spinner" aria-hidden /> : null}
          {loading ? 'Searching' : 'Ask'}
        </button>
      </div>
      <div className="filters">
        <Segmented label="Corpus" value={corpus} options={CORPORA} onChange={setCorpus} />
        <Segmented label="Answer in" value={lang} options={LANGS} onChange={setLang} />
        <span className="hint">Enter to ask · Shift+Enter for a new line</span>
      </div>
      <div className="examples">
        <span className="seg-label">Try</span>
        {EXAMPLES.map((ex) => (
          <button key={ex.text} type="button" className="chip" onClick={() => pick(ex)} disabled={loading}>
            {ex.text}
          </button>
        ))}
      </div>
    </form>
  )
}
