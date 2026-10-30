import type { Lang, VerseRecord } from './types'

/** Parse "Matt.6.14" / "Q002.2.153" into parts. */
export function parseCanonRef(ref: string): { book: string; chapter: number; verse: number } | null {
  const m = /^([1-3]?[A-Za-z0-9]+?)\.(\d+)\.(\d+)$/.exec(ref)
  if (!m) return null
  return { book: m[1], chapter: Number(m[2]), verse: Number(m[3]) }
}

export function isQuranRef(ref: string): boolean {
  return /^Q\d{3}\./.test(ref)
}

/** Short pill label: "Matthew 6:14" or "Q2:153" (falls back to the raw ref). */
export function shortLabel(ref: string, lang: Lang, rec?: VerseRecord): string {
  const p = parseCanonRef(ref)
  if (!p) return ref
  if (isQuranRef(ref)) return `Q${p.chapter}:${p.verse}`
  const book = rec ? rec.bookName[lang] : p.book
  return `${book} ${p.chapter}:${p.verse}`
}

/** Full label for a verse header. */
export function fullLabel(rec: VerseRecord, lang: Lang): string {
  return `${rec.bookName[lang]} ${rec.chapter}:${rec.verse}`
}

export const TRANSLATION_NAMES: Record<string, string> = {
  kjv: 'King James Version',
  cuv: '和合本 (CUV)',
  pickthall: 'Pickthall (1930)',
  majian: '马坚译本',
}

/** Shown wherever Chinese Quran (Ma Jian) text would appear but is not shipped. */
export const MAJIAN_PLACEHOLDER =
  '马坚译本受版权保护，本地构建后可见 / Ma Jian translation is copyrighted; available after local build'

/** Translation code used for the Chinese side when the record has none. */
export function zhTranslationFor(corpus: 'bible' | 'quran'): string {
  return corpus === 'quran' ? 'majian' : 'cuv'
}
