# Decisions log

- **Python, not Go**, for the main app: DeepEval and bge-m3 tooling are Python-native. Go stays optional (`go-embed-worker/`).
- **Quran added** alongside the Bible; `corpus` column distinguishes them.
- **Translations**: Bible KJV (EN), CUV Simplified (ZH), Synodal (RU). Quran Pickthall 1930 (EN, PD), Ma Jian (ZH, copyrighted → not committed), Sablukov 1878 (RU, PD).
- **Phase 1 = EN + ZH only.** KJV and CUV share numbering, so no `verse_map` yet. Note: KJV 31,102 vs CUV 31,103 verses — ingest must report mismatches.
- **Native numbering + `canon_ref`**: precompute `canon_ref` at ingest time instead of joining at query time (scripture is read-only).
- **Russian later**: Synodal Psalms use LXX numbering (KJV Ps 23 = RU Ps 22), plus differences in Numbers, Job, Romans → needs `verse_map`.
- **Frontend first**, using a mock API client, then wire to FastAPI.
- **Milvus instead of Postgres/pgvector** (2026-10-30): native dense + sparse hybrid search with RRF; bge-m3 outputs both, which also solves Chinese keyword search (no zhparser). Two collections: `chunks` (dense + sparse, searched) and `passages` (one row per verse, filter lookups by `canon_ref` / `parent_key`; tiny placeholder vector because Milvus requires one).
