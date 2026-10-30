import { useCallback, useRef, useState } from 'react'
import { ask, USE_MOCK } from './api/client'
import type { AskResponse } from './api/types'
import AskBox, { type AskParams } from './components/AskBox'
import Answer from './components/Answer'
import VerseCompare from './components/VerseCompare'

type Status = 'idle' | 'loading' | 'done' | 'error'

function LoadingState() {
  return (
    <div className="card loading" aria-busy="true">
      <div className="loading-steps">
        <span className="spinner dark" /> Retrieving passages · reranking · generating answer…
      </div>
      <div className="skeleton w60" />
      <div className="skeleton" />
      <div className="skeleton w90" />
      <div className="skeleton w70" />
    </div>
  )
}

function EmptyState() {
  return (
    <div className="empty">
      <div className="empty-icon" aria-hidden>
        ✦
      </div>
      <h2>Ask the scriptures</h2>
      <p>
        Questions are answered only from retrieved passages of the <strong>Bible</strong> (KJV · 和合本) and the{' '}
        <strong>Quran</strong> (Pickthall · 马坚). Every claim carries a citation — click one to compare the verse in
        English and Chinese side by side.
      </p>
      <div className="empty-stats">
        <div>
          <b>31,102</b>
          <span>Bible verses</span>
        </div>
        <div>
          <b>6,236</b>
          <span>Quran ayahs</span>
        </div>
        <div>
          <b>EN · 中文</b>
          <span>phase 1 languages</span>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [status, setStatus] = useState<Status>('idle')
  const [question, setQuestion] = useState('')
  const [resp, setResp] = useState<AskResponse | null>(null)
  const [error, setError] = useState('')
  const [activeRef, setActiveRef] = useState<string | null>(null)
  const reqId = useRef(0)

  const onAsk = useCallback(async (p: AskParams) => {
    const id = ++reqId.current
    setStatus('loading')
    setQuestion(p.question)
    setActiveRef(null)
    setError('')
    try {
      const r = await ask({ question: p.question, corpus: p.corpus, lang: p.lang, topK: 6 })
      if (id !== reqId.current) return
      setResp(r)
      setStatus('done')
    } catch (e) {
      if (id !== reqId.current) return
      setError(e instanceof Error ? e.message : String(e))
      setStatus('error')
    }
  }, [])

  const closeCompare = useCallback(() => setActiveRef(null), [])

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <img src="/favicon.svg" alt="" width={28} height={28} />
          <span className="brand-name">Bible-RAG</span>
          <span className="brand-sub">multilingual RAG over the Bible &amp; Quran</span>
        </div>
        <div className="topbar-right">
          <span className={`badge ${USE_MOCK ? 'mock' : 'live'}`}>{USE_MOCK ? 'Mock API' : 'Live API'}</span>
          <a href="https://github.com/co-codin/Bible-RAG" target="_blank" rel="noreferrer">
            GitHub
          </a>
        </div>
      </header>

      <main className={`layout ${activeRef ? 'with-compare' : ''}`}>
        <div className="main-col">
          <AskBox loading={status === 'loading'} onAsk={onAsk} />
          {status === 'idle' && <EmptyState />}
          {status === 'loading' && <LoadingState />}
          {status === 'error' && (
            <div className="card error">
              <b>Request failed.</b> {error}
            </div>
          )}
          {status === 'done' && resp && (
            <Answer question={question} response={resp} activeRef={activeRef} onCite={setActiveRef} />
          )}
        </div>
        {activeRef && (
          <div className="side-col">
            <VerseCompare canonRef={activeRef} onClose={closeCompare} />
          </div>
        )}
      </main>

      <footer className="footer">
        Texts: KJV · 和合本 (CUV, 1919) · Pickthall (1930) · 马坚译本 (built locally, not redistributed)
      </footer>
    </div>
  )
}
