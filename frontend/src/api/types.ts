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
  refused?: boolean
  refusalReason?: string
  refusalMessage?: string
  /** True when POST /answer returned 503 because the generation key is missing. */
  generationUnavailable?: boolean
}

export interface AnswerApiResponse {
  query: string
  answer: string | null
  citations: string[]
  hits: SearchHit[]
  refused: boolean
  refusal_reason: string | null
  refusal_message: string | null
}

export interface VerseSideOut {
  translation: string
  text: string
  merged_with_previous?: boolean
  note?: string | null
}

export interface VerseItemOut {
  canon_ref: string
  verse: number
  en: VerseSideOut | null
  zh: VerseSideOut | null
}

export interface VerseApiResponse {
  canon_ref: string
  corpus: Corpus
  book_code: string
  chapter: number
  verse_start: number
  verse_end: number
  book_name: { en: string; zh: string }
  verses: VerseItemOut[]
}

export interface VerseSide {
  translation: string
  text: string
  mergedWithPrevious?: boolean
  note?: string
}

export interface VerseRecord {
  canonRef: string
  corpus: Corpus
  bookCode: string
  chapter: number
  verse: number
  verseEnd?: number
  bookName: { en: string; zh: string }
  en: VerseSide
  /** null = not available (mock build may omit Ma Jian; a translation can be missing). */
  zh: VerseSide | null
}
