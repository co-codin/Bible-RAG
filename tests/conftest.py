"""Keep unit tests off the real bge-m3 checkpoint (several GB, several seconds)."""

import os

os.environ.setdefault("GUARD_SEMANTIC", "0")
