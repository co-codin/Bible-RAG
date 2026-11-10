import { mockAsk, mockGetVerse, mockVerseSync } from './mock'
import { parseCanonRef } from './refs'
import type { AskRequest, AskResponse, Corpus, Lang, SearchHit, SearchResponse, Source, VerseRecord } from './types'

export type * from './types'

/** Mock mode is the default until you opt into the live API with VITE_USE_MOCK=false. */
export const USE_MOCK = (import.meta.env.VITE_USE_MOCK ?? 'true') !== 'false'

/** Empty string = same origin (Vite proxies /search). Unset = local FastAPI default. */
export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}${body ? `: ${body}` : ''}`)
  }
  return (await res.json()) as T
}

function apiUrl(path: string, params?: URLSearchParams): string {
  const suffix = params && [...params].length ? `?${params}` : ''
  return `${API_BASE}${path}${suffix}`
}

function corpusOf(translation: string): Corpus {
  return translation.startsWith('quran') ? 'quran' : 'bible'
}

/** Backend uses quran_en / quran_zh; the UI labels use pickthall / majian. */
function mapTranslation(translation: string): string {
  if (translation === 'quran_en') return 'pickthall'
  if (translation === 'quran_zh') return 'majian'
  return translation
}

function hitLabel(hit: SearchHit): string {
  const header = hit.chunk_text.split('\n', 1)[0]?.trim() ?? ''
  const refs = hit.canon_refs
  if (!refs.length) return header || hit.pk
  const first = parseCanonRef(refs[0])
  const last = parseCanonRef(refs[refs.length - 1])
  const verses =
    first && last ? (first.verse === last.verse ? `:${first.verse}` : `:${first.verse}–${last.verse}`) : ''
  return header ? `${header}${verses}` : refs.join(', ')
}

function hitsToSources(hits: SearchHit[]): Source[] {
  return hits.map((hit) => ({
    pk: hit.pk,
    canonRef: hit.canon_refs[0] ?? hit.pk,
    corpus: corpusOf(hit.translation),
    label: hitLabel(hit),
    translation: mapTranslation(hit.translation),
    text: hit.chunk_text,
    score: hit.score,
  }))
}

function liveAnswer(lang: Lang, sources: Source[]): string {
  if (!sources.length) {
    return lang === 'zh'
      ? '在所选经典里没有检索到相关经文，所以不作猜测。可以换个问法，或者放宽经典筛选。'
      : 'I could not find passages in the selected corpus that answer this question, so I will not guess. Try another wording or widen the corpus filter.'
  }
  const cites = sources
    .map((s) => `[[${s.canonRef}]]`)
    .filter((marker, i, all) => all.indexOf(marker) === i)
    .join(' ')
  return lang === 'zh'
    ? `已检索到 ${sources.length} 段经文（答案生成尚未接入，先列出检索结果）。${cites}`
    : `Retrieved ${sources.length} passages (answer generation is not wired yet). ${cites}`
}

async function liveSearch(req: AskRequest): Promise<AskResponse> {
  const t0 = performance.now()
  const params = new URLSearchParams({
    query: req.question,
    limit: String(req.topK ?? 10),
    mode: 'hybrid',
  })
  if (req.corpus !== 'all') params.set('corpus', req.corpus)
  const data = await request<SearchResponse>(apiUrl('/search', params))
  const sources = hitsToSources(data.hits)
  return {
    answer: liveAnswer(req.lang, sources),
    sources,
    lang: req.lang,
    latencyMs: Math.round(performance.now() - t0),
    mode: 'live',
  }
}

export function ask(req: AskRequest): Promise<AskResponse> {
  if (USE_MOCK) return mockAsk(req)
  return liveSearch(req)
}

export function getVerse(canonRef: string): Promise<VerseRecord> {
  if (USE_MOCK) return mockGetVerse(canonRef)
  // /verse is not implemented yet; reuse the local mock table when the ref is there.
  const local = mockVerseSync(canonRef)
  if (local) return Promise.resolve(local)
  return request<VerseRecord>(apiUrl(`/verse/${encodeURIComponent(canonRef)}`))
}
