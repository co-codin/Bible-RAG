export type Corpus = 'bible' | 'quran'
export type CorpusFilter = 'all' | Corpus
export type Lang = 'en' | 'zh'

export interface AskRequest {
  question: string
  corpus: CorpusFilter
  lang: Lang
  topK?: number
}

/** One retrieved passage (a child chunk) with its retrieval score. */
export interface Source {
  pk?: string // chunk id from the search API, unique even when windows overlap
  canonRef: string // e.g. "Matt.6.14", "Q002.2.153"
  corpus: Corpus
  label: string // human readable, in the answer language: "Matthew 6:14" / "马太福音 6:14"
  translation: string // kjv | cuv | pickthall | majian
  /** null when the text cannot be shown (e.g. Ma Jian Quran in the public/mock build). */
  text: string | null
  score: number // retrieval score (RRF, cosine, or IP); higher is better
}

/** Live `GET/POST /search` payload. */
export interface SearchHit {
  pk: string
  translation: string
  parent_key: string
  canon_refs: string[]
  chunk_text: string
  score: number
}

export interface SearchResponse {
  query: string
  translation: string | null
  corpus: string | null
  mode: string
  limit: number
  hits: SearchHit[]
}

export interface AskResponse {
  /** Answer text; citations are inline markers like [[Matt.6.14]]. */
  answer: string
  sources: Source[]
  lang: Lang
  latencyMs: number
  mode: 'mock' | 'live'
}

export interface VerseSide {
  translation: string
  text: string
}

export interface VerseRecord {
  canonRef: string
  corpus: Corpus
  bookCode: string
  chapter: number
  verse: number
  bookName: { en: string; zh: string }
  en: VerseSide
  /** null = not available in this build (Quran zh / Ma Jian is copyrighted). */
  zh: VerseSide | null
}
