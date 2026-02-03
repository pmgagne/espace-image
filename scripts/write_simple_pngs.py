import zlib, struct, os

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'app', 'static')
os.makedirs(OUT_DIR, exist_ok=True)

def png_chunk(chunk_type, data):
    chunk = struct.pack('!I', len(data)) + chunk_type + data
    crc = zlib.crc32(chunk_type + data) & 0xffffffff
    chunk += struct.pack('!I', crc)
    return chunk


def write_png(path, w, h, bg=(0,0,0), fg=(0,209,255)):
    # Create raw RGBA scanlines with circle in center
    raw = bytearray()
    cx, cy = w/2.0, h/2.0
    r = min(w,h)*0.36
    for y in range(h):
        raw.append(0)  # filter type 0
        for x in range(w):
            dx = x+0.5 - cx
            dy = y+0.5 - cy
            if dx*dx+dy*dy <= r*r:
                raw.extend(bytes(fg)+b'\xff')
            else:
                raw.extend(bytes(bg)+b'\xff')
    # PNG signature
    png = b"\x89PNG\r\n\x1a\n"
    # IHDR
    ihdr = struct.pack('!IIBBBBB', w, h, 8, 6, 0, 0, 0)
    png += png_chunk(b'IHDR', ihdr)
    # IDAT
    comp = zlib.compress(bytes(raw), level=9)
    png += png_chunk(b'IDAT', comp)
    # IEND
    png += png_chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)
    print('Wrote', path)

if __name__ == '__main__':
    write_png(os.path.join(OUT_DIR, 'espaceimage-192.png'), 192, 192, bg=(10,10,10), fg=(0,209,255))
    write_png(os.path.join(OUT_DIR, 'espaceimage-512.png'), 512, 512, bg=(10,10,10), fg=(0,209,255))
