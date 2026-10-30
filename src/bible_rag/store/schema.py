"""Milvus collections for Bible-RAG.

passages: one row per verse/ayah (lookup by filters, not semantic search)
chunks:   retrieval units with bge-m3 dense + sparse vectors (hybrid search)
"""
from pymilvus import DataType, MilvusClient

DENSE_DIM = 1024  # bge-m3

PASSAGES = "passages"
CHUNKS = "chunks"


def create_passages(client: MilvusClient) -> None:
    schema = client.create_schema(auto_id=False)
    schema.add_field("pk", DataType.VARCHAR, is_primary=True, max_length=64)  # e.g. kjv:Matt.6.14
    schema.add_field("corpus", DataType.VARCHAR, max_length=8)
    schema.add_field("translation", DataType.VARCHAR, max_length=16)
    schema.add_field("book_code", DataType.VARCHAR, max_length=8)
    schema.add_field("book_name", DataType.VARCHAR, max_length=64)
    schema.add_field("chapter", DataType.INT16)
    schema.add_field("verse", DataType.INT16)
    schema.add_field("canon_ref", DataType.VARCHAR, max_length=32)
    schema.add_field("text", DataType.VARCHAR, max_length=4096)
    # Milvus requires a vector field; tiny placeholder, never searched.
    schema.add_field("_placeholder", DataType.FLOAT_VECTOR, dim=2)

    index = client.prepare_index_params()
    index.add_index("_placeholder", index_type="FLAT", metric_type="L2")
    index.add_index("canon_ref", index_type="INVERTED")
    index.add_index("translation", index_type="INVERTED")
    index.add_index("book_code", index_type="INVERTED")

    client.create_collection(PASSAGES, schema=schema, index_params=index)


def create_chunks(client: MilvusClient) -> None:
    schema = client.create_schema(auto_id=False)
    schema.add_field("pk", DataType.VARCHAR, is_primary=True, max_length=64)  # e.g. cuv:Matt.6.14-15
    schema.add_field("corpus", DataType.VARCHAR, max_length=8)
    schema.add_field("translation", DataType.VARCHAR, max_length=16)
    schema.add_field("parent_key", DataType.VARCHAR, max_length=32)  # e.g. cuv:Matt.6
    schema.add_field("canon_refs", DataType.ARRAY, element_type=DataType.VARCHAR, max_capacity=8, max_length=32)
    schema.add_field("context_prefix", DataType.VARCHAR, max_length=1024)
    schema.add_field("chunk_text", DataType.VARCHAR, max_length=8192)
    schema.add_field("dense", DataType.FLOAT_VECTOR, dim=DENSE_DIM)
    schema.add_field("sparse", DataType.SPARSE_FLOAT_VECTOR)

    index = client.prepare_index_params()
    index.add_index("dense", index_type="HNSW", metric_type="COSINE", params={"M": 16, "efConstruction": 200})
    index.add_index("sparse", index_type="SPARSE_INVERTED_INDEX", metric_type="IP")
    index.add_index("translation", index_type="INVERTED")
    index.add_index("corpus", index_type="INVERTED")

    client.create_collection(CHUNKS, schema=schema, index_params=index)


def init(uri: str = "http://localhost:19530", drop: bool = False) -> None:
    client = MilvusClient(uri=uri)
    for name, create in ((PASSAGES, create_passages), (CHUNKS, create_chunks)):
        if client.has_collection(name):
            if not drop:
                continue
            client.drop_collection(name)
        create(client)


if __name__ == "__main__":
    init()
