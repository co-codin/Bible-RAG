# Bible-RAG frontend

Vite + React + TypeScript single-page UI for Bible-RAG (phase 1: English + Simplified Chinese).

```bash
npm install
npm run dev        # http://localhost:5173, /api is proxied to http://localhost:8000
npm run build      # tsc -b && vite build -> dist/
```

## API modes
- **Live (default)**: unset `VITE_USE_MOCK`, or any value other than `true`. The UI calls
  `POST /answer`, `GET /search` (fallback when generation returns 503), and `GET /verse/{canonRef}`.
  Default base URL is `http://localhost:8000` (CORS is enabled for the Vite origin). Set
  `VITE_API_BASE_URL=` (empty) to call same-origin paths, which Vite proxies to FastAPI.
  A missing `OPENAI_API_KEY` shows a clear 503 message and still lists retrieved passages.
  Verse compare uses the live `/verse` endpoint (no mock fallback).
- **Mock**: `VITE_USE_MOCK=true` (`make fe-mock`). `src/api/mock.ts` returns canned answers; every verse
  text comes from `src/api/mockData.ts`, generated from the real jsonl data by
  `python3 scripts/gen_mock_data.py /path/to/data-root` (expects `bible-rag-data/` and `quran-data/`).
  The mock table may still omit Ma Jian text (`zh: null`) and show a placeholder; the live API
  serves `quran_zh` from the committed corpus (the translation remains copyrighted).

Contract (see `src/api/types.ts`):
- Live answer: `POST /answer` `{query, corpus?, translation?, lang?, mode, limit}` → `{answer, citations, hits, refused, refusal_reason, refusal_message}` (503 if the generation key is missing).
- Live search: `GET /search?query=...&corpus=bible|quran&translation=kjv|cuv|quran_en|quran_zh&mode=hybrid&limit=10`
  → `{query, translation, corpus, mode, limit, hits[{pk, translation, parent_key, canon_refs, chunk_text, score}]}`.
  The client maps hits into the existing `AskResponse` / `Source` shape so the sources list works unchanged.
  Inline citations in `answer` are written as `[[canonRef]]`, e.g. `[[Matt.6.14]]`, `[[Q002.2.153]]`.
- Mock ask (and the planned generation endpoint): `POST /api/ask` body
  `{question, corpus: "all"|"bible"|"quran", lang: "en"|"zh", topK?}` →
  `{answer, sources[{canonRef, corpus, label, translation, text, score}], lang, latencyMs, mode}`.
- `GET /verse/{canonRef}` → `{canon_ref, corpus, book_code, chapter, verse_start, verse_end, book_name{en,zh}, verses[{canon_ref, verse, en, zh}]}`. The client maps this into `VerseRecord`.

`canonRef` = `book_code.chapter.verse` (Bible: OSIS code with KJV numbering; Quran: `Q002.2.153`).

## Layout
- `src/components/AskBox.tsx` – question box, corpus/language filters, example chips
- `src/components/Answer.tsx` – answer with clickable citation pills + scored source list
- `src/components/VerseCompare.tsx` – side-by-side EN / 中文 view for one canonRef
- `src/api/client.ts` – `ask()` / `getVerse()`, mock vs live switch
