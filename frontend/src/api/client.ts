import { mockAsk, mockGetVerse } from './mock'
import { parseCanonRef } from './refs'
import type {
  AnswerApiResponse,
  AskRequest,
  AskResponse,
  Corpus,
  Lang,
  SearchHit,
  SearchResponse,
  Source,
  VerseApiResponse,
  VerseRecord,
  VerseSide,
  VerseSideOut,
} from './types'

export type * from './types'

/** Live API is the default. Mock mode only when VITE_USE_MOCK is explicitly 'true'. */
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

/** Empty string = same origin (Vite proxies /search, /answer, /verse). Unset = local FastAPI default. */
export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  detail: string
  constructor(status: number, statusText: string, detail: string) {
    super(`${status} ${statusText}${detail ? `: ${detail}` : ''}`)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new ApiError(res.status, res.statusText, body)
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

export function noKeyMessage(lang: Lang): string {
  return lang === 'zh'
    ? '生成答案需要设置 OPENAI_API_KEY。检索结果仍可查看；配置密钥后即可生成引用经文的回答。'
    : 'Answer generation needs OPENAI_API_KEY. Retrieved passages are shown below; add a key to generate a cited answer.'
}

function searchParams(req: AskRequest): URLSearchParams {
  const params = new URLSearchParams({
    query: req.question,
    limit: String(req.topK ?? 10),
    mode: 'hybrid',
  })
  if (req.corpus !== 'all') params.set('corpus', req.corpus)
  return params
}

async function liveSearchHits(req: AskRequest): Promise<Source[]> {
  const data = await request<SearchResponse>(apiUrl('/search', searchParams(req)))
  return hitsToSources(data.hits)
}

async function liveAsk(req: AskRequest): Promise<AskResponse> {
  const t0 = performance.now()
  const payload: Record<string, string | number> = {
    query: req.question,
    limit: req.topK ?? 10,
    mode: 'hybrid',
    lang: req.lang,
  }
  if (req.corpus !== 'all') payload.corpus = req.corpus

  const res = await fetch(apiUrl('/answer'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const latencyMs = () => Math.round(performance.now() - t0)

  if (res.status === 503) {
    let sources: Source[] = []
    try {
      sources = await liveSearchHits(req)
    } catch {
      sources = []
    }
    return {
      answer: '',
      sources,
      lang: req.lang,
      latencyMs: latencyMs(),
      mode: 'live',
      generationUnavailable: true,
      refusalMessage: noKeyMessage(req.lang),
    }
  }

  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new ApiError(res.status, res.statusText, body)
  }

  const data = (await res.json()) as AnswerApiResponse
  const sources = hitsToSources(data.hits ?? [])
  if (data.refused) {
    return {
      answer: data.refusal_message ?? '',
      sources,
      lang: req.lang,
      latencyMs: latencyMs(),
      mode: 'live',
      refused: true,
      refusalReason: data.refusal_reason ?? undefined,
      refusalMessage: data.refusal_message ?? undefined,
    }
  }
  return {
    answer: data.answer ?? '',
    sources,
    lang: req.lang,
    latencyMs: latencyMs(),
    mode: 'live',
  }
}

export function ask(req: AskRequest): Promise<AskResponse> {
  if (USE_MOCK) return mockAsk(req)
  return liveAsk(req)
}

function mapSide(side: VerseSideOut | null, fallback?: VerseSideOut | null): VerseSide | null {
  const src = side ?? fallback ?? null
  if (!src) return null
  return {
    translation: mapTranslation(src.translation),
    text: src.text,
    mergedWithPrevious: src.merged_with_previous || undefined,
    note: src.note || undefined,
  }
}

function joinSide(verses: VerseApiResponse['verses'], lang: 'en' | 'zh'): VerseSide | null {
  const parts: { verse: number; side: VerseSideOut }[] = []
  for (const item of verses) {
    const side = lang === 'en' ? item.en : item.zh
    if (side) parts.push({ verse: item.verse, side })
  }
  if (!parts.length) return null
  if (parts.length === 1) return mapSide(parts[0].side)
  const text = parts
    .map(({ verse, side }) => `${verse}. ${side.text}`.trim())
    .join('\n')
  const first = parts[0].side
  return {
    translation: mapTranslation(first.translation),
    text,
    mergedWithPrevious: parts.some((p) => p.side.merged_with_previous),
    note: parts.find((p) => p.side.note)?.side.note || undefined,
  }
}

function mapVerseResponse(data: VerseApiResponse): VerseRecord {
  const en = joinSide(data.verses, 'en')
  const zh = joinSide(data.verses, 'zh')
  if (!en) {
    throw new Error(`Verse ${data.canon_ref} has no English text`)
  }
  return {
    canonRef: data.canon_ref,
    corpus: data.corpus,
    bookCode: data.book_code,
    chapter: data.chapter,
    verse: data.verse_start,
    verseEnd: data.verse_end !== data.verse_start ? data.verse_end : undefined,
    bookName: data.book_name,
    en,
    zh,
  }
}

export function getVerse(canonRef: string): Promise<VerseRecord> {
  if (USE_MOCK) return mockGetVerse(canonRef)
  return request<VerseApiResponse>(apiUrl(`/verse/${encodeURIComponent(canonRef)}`)).then(mapVerseResponse)
}
