import { mockAsk, mockGetVerse } from './mock'
import type { AskRequest, AskResponse, VerseRecord } from './types'

export type * from './types'

/** Mock mode is the default until the FastAPI backend exists. Set VITE_USE_MOCK=false to hit /api. */
export const USE_MOCK = (import.meta.env.VITE_USE_MOCK ?? 'true') !== 'false'

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

export function ask(req: AskRequest): Promise<AskResponse> {
  if (USE_MOCK) return mockAsk(req)
  return request<AskResponse>('/api/ask', { method: 'POST', body: JSON.stringify(req) })
}

export function getVerse(canonRef: string): Promise<VerseRecord> {
  if (USE_MOCK) return mockGetVerse(canonRef)
  return request<VerseRecord>(`/api/verse/${encodeURIComponent(canonRef)}`)
}
