import { useEffect, useState } from 'react'
import { getVerse } from '../api/client'
import { fullLabel, MAJIAN_PLACEHOLDER, TRANSLATION_NAMES, zhTranslationFor } from '../api/refs'
import type { VerseRecord } from '../api/types'

interface Props {
  canonRef: string
  onClose: () => void
}

type State = { status: 'loading' } | { status: 'ok'; rec: VerseRecord } | { status: 'error'; msg: string }

export default function VerseCompare({ canonRef, onClose }: Props) {
  const [state, setState] = useState<State>({ status: 'loading' })

  useEffect(() => {
    let alive = true
    setState({ status: 'loading' })
    getVerse(canonRef)
      .then((rec) => alive && setState({ status: 'ok', rec }))
      .catch((e: unknown) => alive && setState({ status: 'error', msg: e instanceof Error ? e.message : String(e) }))
    return () => {
      alive = false
    }
  }, [canonRef])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <aside className="card compare" aria-label="Verse comparison">
      <header className="compare-head">
        <div>
          <div className="eyebrow">Verse compare</div>
          <h3>
            {state.status === 'ok' ? fullLabel(state.rec, 'en') : canonRef}
            {state.status === 'ok' && <span className="zh-title">{fullLabel(state.rec, 'zh')}</span>}
          </h3>
          <code className="canon">canon_ref = {canonRef}</code>
        </div>
        <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
          ×
        </button>
      </header>

      {state.status === 'loading' && (
        <div className="compare-grid">
          {[0, 1].map((i) => (
            <div key={i} className="compare-col">
              <div className="skeleton w40" />
              <div className="skeleton" />
              <div className="skeleton w80" />
            </div>
          ))}
        </div>
      )}
      {state.status === 'error' && <p className="error">Could not load verse: {state.msg}</p>}
      {state.status === 'ok' && (
        <div className="compare-grid">
          <div className="compare-col" lang="en">
            <div className="col-head">
              <span className="lang-tag">EN</span>
              {TRANSLATION_NAMES[state.rec.en.translation] ?? state.rec.en.translation}
            </div>
            <blockquote className="scripture en big">
              <sup>{state.rec.verse}</sup>
              {state.rec.en.text}
            </blockquote>
          </div>
          <div className="compare-col" lang="zh-CN">
            <div className="col-head">
              <span className="lang-tag">中</span>
              {(() => {
                const t = state.rec.zh?.translation ?? zhTranslationFor(state.rec.corpus)
                return TRANSLATION_NAMES[t] ?? t
              })()}
            </div>
            {state.rec.zh ? (
              <blockquote className="scripture zh big">
                <sup>{state.rec.verse}</sup>
                {state.rec.zh.text}
              </blockquote>
            ) : (
              <p className="placeholder">{MAJIAN_PLACEHOLDER}</p>
            )}
          </div>
        </div>
      )}
      <p className="muted small foot">
        {state.status === 'ok' && state.rec.corpus === 'quran'
          ? 'Aligned by canon_ref (standard surah:ayah numbering).'
          : 'Aligned by canon_ref (KJV numbering).'}{' '}
        Russian will be added in phase 2.
      </p>
    </aside>
  )
}
