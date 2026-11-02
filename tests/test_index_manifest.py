import json

import pytest

from bible_rag import index_manifest as im


def test_fingerprint_is_stable_and_param_sensitive():
    p = im.build_params()
    assert im.fingerprint(p) == im.fingerprint(json.loads(json.dumps(p)))
    changed = json.loads(json.dumps(p))
    changed["chunking"]["window"] = 2
    assert im.fingerprint(changed) != im.fingerprint(p)


def test_write_then_check_roundtrip(tmp_path):
    uri = str(tmp_path / "bible_rag.db")
    path = im.write_manifest(uri, {"kjv": 1, "cuv": 2})
    assert path == tmp_path / "manifest.json"
    m = im.check(uri)
    assert m["total"] == 3 and m["dims"]["dense"] == 1024


def test_check_fails_on_mismatch_and_missing(tmp_path):
    uri = str(tmp_path / "bible_rag.db")
    with pytest.raises(im.IndexMismatchError, match="no manifest.json"):
        im.check(uri)
    path = im.write_manifest(uri, {})
    m = json.loads(path.read_text())
    m["params"]["chunking"]["stride"] = 1
    m["fingerprint"] = im.fingerprint(m["params"])
    path.write_text(json.dumps(m))
    with pytest.raises(im.IndexMismatchError, match="chunking.stride"):
        im.check(uri)
