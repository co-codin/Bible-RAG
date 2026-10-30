# Bible-RAG frontend

Vite + React + TypeScript single-page UI for Bible-RAG (phase 1: English + Simplified Chinese).

```bash
npm install
npm run dev        # http://localhost:5173, /api is proxied to http://localhost:8000
npm run build      # tsc -b && vite build -> dist/
```

## API modes
- **Mock (default)**: `VITE_USE_MOCK=true` (or unset). `src/api/mock.ts` returns canned answers; every verse
  text comes from `src/api/mockData.ts`, generated from the real jsonl data by
  `python3 scripts/gen_mock_data.py /path/to/data-root` (expects `bible-rag-data/` and `quran-data/`).
  Quran Chinese (马坚译本) is copyrighted and is never written into the repo: Quran records have `zh: null`
  and the UI shows a placeholder ("马坚译本受版权保护，本地构建后可见").
- **Live**: `VITE_USE_MOCK=false` → `POST /api/ask` and `GET /api/verse/{canonRef}`.

Contract (see `src/api/types.ts`):
- `POST /api/ask` body `{question, corpus: "all"|"bible"|"quran", lang: "en"|"zh", topK?}` →
  `{answer, sources[{canonRef, corpus, label, translation, text, score}], lang, latencyMs, mode}`.
  Inline citations in `answer` are written as `[[canonRef]]`, e.g. `[[Matt.6.14]]`, `[[Q002.2.153]]`.
- `GET /api/verse/{canonRef}` → `{canonRef, corpus, bookCode, chapter, verse, bookName{en,zh}, en{translation,text}, zh{...}}`.

`canonRef` = `book_code.chapter.verse` (Bible: OSIS code with KJV numbering; Quran: `Q002.2.153`).

## Layout
- `src/components/AskBox.tsx` – question box, corpus/language filters, example chips
- `src/components/Answer.tsx` – answer with clickable citation pills + scored source list
- `src/components/VerseCompare.tsx` – side-by-side EN / 中文 view for one canonRef
- `src/api/client.ts` – `ask()` / `getVerse()`, mock vs live switch
