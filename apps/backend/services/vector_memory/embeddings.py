import hashlib
import math
from typing import List


def embed_text(text: str, dims: int = 1536) -> List[float]:
    """
    Deterministic lightweight embedding fallback.
    Uses SHA256 hashing to create a fixed-size vector.
    """
    if not text:
        return [0.0] * dims

    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = [b for b in digest]
    vector = []
    for i in range(dims):
        vector.append(values[i % len(values)] / 255.0)

    # Normalize
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]
