"""bge-m3 encoder: one forward pass gives both a dense and a sparse vector.

dense  -> 1024-dim float vector (semantic match)
sparse -> {token_id: weight} lexical weights (keyword match, like BM25 but learned)

Milvus stores both in one row, and hybrid search fuses them with RRF.
"""

from __future__ import annotations

import os

DENSE_DIM = 1024
MODEL_NAME = "BAAI/bge-m3"
# Pinned Hugging Face commit, so the vectors in a shipped index match the query encoder.
MODEL_REVISION = os.environ.get("BGE_M3_REVISION", "5617a9f61b028005a4858fdac845db406aefb181")


class BGEM3:
    def __init__(
        self, model_name: str = MODEL_NAME, device: str | None = None, max_length: int = 512
    ):
        import torch
        from FlagEmbedding import BGEM3FlagModel
        from huggingface_hub import snapshot_download

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cpu":
            torch.set_num_threads(int(os.environ.get("TORCH_THREADS", os.cpu_count() or 4)))
        self.device = device
        self.max_length = max_length
        # fp16 halves memory and is ~2x faster on GPU; on CPU it is slower or unsupported.
        path = snapshot_download(model_name, revision=MODEL_REVISION)  # cached after first run
        self.model = BGEM3FlagModel(path, use_fp16=(device == "cuda"), devices=[device])

    def encode(
        self, texts: list[str], batch_size: int = 32
    ) -> tuple[list[list[float]], list[dict[int, float]]]:
        out = self.model.encode(
            texts,
            batch_size=batch_size,
            max_length=self.max_length,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )
        dense = [v.tolist() for v in out["dense_vecs"]]
        sparse = [to_milvus_sparse(w) for w in out["lexical_weights"]]
        return dense, sparse


def to_milvus_sparse(weights: dict) -> dict[int, float]:
    """FlagEmbedding returns {'123': np.float16(0.2), ...}; Milvus wants {123: 0.2}."""
    sp = {int(k): float(v) for k, v in weights.items() if float(v) > 0}
    return sp or {0: 1e-6}  # Milvus rejects an empty sparse row
