"""Process-wide Pillow hardening — import for its side effect.

A tiny user-uploaded file can declare gigapixels and exhaust the worker's RAM on
decode (decompression bomb). Cap pixels well above any real screenshot (~40 MP)
and promote Pillow's bomb WARNING (pixels > cap) to an error so such an image is
rejected on open, not just logged. Pillow already hard-errors above 2x the cap.

Every module that opens user images (`Image.open`) imports this so the guard is
applied in both the API and the worker process.
"""

from __future__ import annotations

import warnings

from PIL import Image

Image.MAX_IMAGE_PIXELS = 40_000_000
warnings.simplefilter("error", Image.DecompressionBombWarning)
