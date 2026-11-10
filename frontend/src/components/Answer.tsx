import { Fragment, type ReactNode } from 'react'
import { isQuranRef, MAJIAN_PLACEHOLDER, shortLabel, TRANSLATION_NAMES } from '../api/refs'
import type { AskResponse, Source } from '../api/types'

interface Props {
  question: string
  response: AskResponse
  activeRef: string | null
  onCite: (canonRef: string) => void
}

const CITE_RE = /\[\[([^\]]+)\]\]/g

function pillLabel(ref: string, sources: Source[], lang: AskResponse['lang']): string {
  if (isQuranRef(ref)) return shortLabel(ref, lang)
  return sources.find((s) => s.canonRef === ref)?.label ?? shortLabel(ref, lang)
}

function renderAnswer(text: string, props: Props): ReactNode[] {
  const out: ReactNode[] = []
  let last = 0
  let i = 0
  for (const m of text.matchAll(CITE_RE)) {
    const ref = m[1]
    if (m.index! > last) out.push(<Fragment key={`t${i}`}>{text.slice(last, m.index)}</Fragment>)
    out.push(
      <button
        key={`c${i}`}
        type="button"
        className={`cite ${isQuranRef(ref) ? 'quran' : 'bible'} ${props.activeRef === ref ? 'active' : ''}`}
        onClick={() => props.onCite(ref)}
        title={`Compare ${ref} in English and Chinese`}
      >
        {pillLabel(ref, props.response.sources, props.response.lang)}
      </button>,
    )
    last = m.index! + m[0].length
    i++
  }
  if (last < text.length) out.push(<Fragment key="tail">{text.slice(last)}</Fragment>)
  return out
}

export default function Answer(props: Props) {
  const { response, question, activeRef, onCite } = props
  const paragraphs = response.answer.split(/\n{2,}/)
  const maxScore = Math.max(...response.sources.map((s) => s.score), 0)
  const scoreText = (score: number) => (score > 0 && score < 0.1 ? score.toFixed(4) : score.toFixed(3))
  const scorePct = (score: number) => (maxScore > 0 ? Math.round((score / maxScore) * 100) : 0)
  return (
    <section className="answer-wrap">
      <article className="card answer">
        <header className="answer-head">
          <div>
            <div className="eyebrow">Answer</div>
            <h2 className="question" lang={response.lang === 'zh' ? 'zh-CN' : 'en'}>
              {question}
            </h2>
          </div>
          <div className="meta">
            {response.mode === 'mock' && <span className="badge mock">mock data</span>}
            <span className="badge">{response.latencyMs} ms</span>
          </div>
        </header>
        {response.generationUnavailable && (
          <div className="notice missing-key" role="status">
            <b>{response.lang === 'zh' ? '尚未配置生成密钥' : 'Generation key not configured'}</b>
            <p>{response.refusalMessage}</p>
          </div>
        )}
        {response.refused && (
          <div className="notice refusal" role="status">
            <b>{response.lang === 'zh' ? '无法回答这个问题' : 'This question was not answered'}</b>
            {response.refusalReason && <span className="badge">{response.refusalReason}</span>}
            <p>{response.refusalMessage || response.answer}</p>
          </div>
        )}
        {!response.refused && !response.generationUnavailable && response.answer && (
          <div className={`answer-body ${response.lang}`} lang={response.lang === 'zh' ? 'zh-CN' : 'en'}>
            {paragraphs.map((p, i) => (
              <p key={i}>{renderAnswer(p, props)}</p>
            ))}
          </div>
        )}
        {response.sources.length === 0 && !response.refused && !response.generationUnavailable && (
          <p className="muted small">No passages passed the relevance threshold, so no answer was generated.</p>
        )}
      </article>

      {response.sources.length > 0 && (
        <section className="card sources">
          <div className="eyebrow">Retrieved sources · top {response.sources.length}</div>
          <ol>
            {response.sources.map((s, i) => (
              <li key={s.pk ?? `${s.canonRef}-${i}`} className={`${s.corpus} ${activeRef === s.canonRef ? 'active' : ''}`}>
                <button type="button" className="source" onClick={() => onCite(s.canonRef)}>
                  <div className="source-top">
                    <span className={`corpus-dot ${s.corpus}`} />
                    <span className="source-label">{s.label}</span>
                    <span className="source-tr">{TRANSLATION_NAMES[s.translation] ?? s.translation}</span>
                    <span className="score" title="retrieval score">
                      <span className={`score-bar ${s.corpus}`}>
                        <span style={{ width: `${scorePct(s.score)}%` }} />
                      </span>
                      {scoreText(s.score)}
                    </span>
                  </div>
                  {s.text != null ? (
                    <p className={`scripture ${response.lang}`} lang={response.lang === 'zh' ? 'zh-CN' : 'en'}>
                      {s.text}
                    </p>
                  ) : (
                    <p className="placeholder">{MAJIAN_PLACEHOLDER}</p>
                  )}
                </button>
              </li>
            ))}
          </ol>
        </section>
      )}
    </section>
  )
}
