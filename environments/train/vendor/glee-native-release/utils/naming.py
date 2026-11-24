                                                 

from __future__ import annotations

import re
from pathlib import Path

_SLUG_PATTERN = re.compile(r"\W+")


def slugify_name(name: str | Path | None, default: str = "") -> str:
    pass                                                                         
    if name is None:
        return default
    text = str(name)
    if not text:
        return default
    slug = _SLUG_PATTERN.sub("", text)
    return slug or default
