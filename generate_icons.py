"""Generate PWA icons for web/public/ using only Python stdlib."""
import struct
import zlib
from pathlib import Path


def _png(width: int, height: int, bg=(11, 22, 34), fg=(45, 126, 181)) -> bytes:
    """Solid bg with a simple bar-chart symbol in fg color."""
    pixels = []
    cx, cy = width // 2, height // 2
    pad = width // 8

    # Bar chart: 3 bars of different heights
    bar_w = max(1, width // 10)
    bars = [
        (cx - bar_w * 3, int(height * 0.55), int(height * 0.85)),
        (cx - bar_w,     int(height * 0.30), int(height * 0.85)),
        (cx + bar_w,     int(height * 0.45), int(height * 0.85)),
    ]

    for y in range(height):
        row = [0]  # filter byte
        for x in range(width):
            in_bar = any(bx <= x < bx + bar_w and y1 <= y < y2 for bx, y1, y2 in bars)
            color = fg if in_bar else bg
            row += list(color)
        pixels.append(bytes(row))

    raw = zlib.compress(b''.join(pixels))

    def chunk(tag: bytes, data: bytes) -> bytes:
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', raw) + chunk(b'IEND', b'')


def main() -> None:
    out = Path(__file__).resolve().parent / 'web' / 'public'
    out.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        path = out / f'icon-{size}.png'
        path.write_bytes(_png(size, size))
        print(f'Generated {path}')


if __name__ == '__main__':
    main()
