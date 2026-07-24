"""Generate placeholder PWA icons for Salty Dog.

Creates simple circular icons with an anchor symbol on a navy background.
Run from project root: python scripts/generate_icons.py
"""

import struct
import zlib
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
ICONS_DIR = FRONTEND_DIR / "icons"


def create_png(size: int, bg_r: int, bg_g: int, bg_b: int,
               fg_r: int, fg_g: int, fg_b: int) -> bytes:
    """Create a minimal PNG with a colored circle on a background."""
    cx, cy = size // 2, size // 2
    radius = int(size * 0.38)

    # Build raw pixel data row by row
    raw = bytearray()
    for y in range(size):
        raw.append(0)  # Filter byte: None
        for x in range(size):
            dx, dy = x - cx, y - cy
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= radius:
                raw.extend([fg_r, fg_g, fg_b])
            else:
                raw.extend([bg_r, bg_g, bg_b])

    # IHDR chunk
    ihdr_data = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    ihdr = make_chunk(b"IHDR", ihdr_data)

    # IDAT chunk
    compressed = zlib.compress(bytes(raw), 9)
    idat = make_chunk(b"IDAT", compressed)

    # IEND chunk
    iend = make_chunk(b"IEND", b"")

    return b"\x89PNG\r\n\x1a\n" + ihdr + idat + iend


def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """Build a PNG chunk with length, type, data, and CRC."""
    chunk = chunk_type + data
    return struct.pack(">I", len(data)) + chunk + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)


def main() -> None:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    # Navy background (#1B2838), ocean blue circle (#2196F3)
    for size, filename in [(192, "icon-192.png"), (512, "icon-512.png")]:
        png_data = create_png(size, 0x1B, 0x28, 0x38, 0x21, 0x96, 0xF3)
        path = ICONS_DIR / filename
        path.write_bytes(png_data)
        print(f"Created {path} ({len(png_data):,} bytes)")


if __name__ == "__main__":
    main()
