from zlib import compress, crc32
from abc import ABC, abstractmethod

from .image import BarcodeImage


class PngBarcodeImage(BarcodeImage):
    HEADER = b"\x89PNG\r\n\x1a\x0a"

    class Chunk(ABC):
        def __init__(self, type_):
            self.type = type_
        
        @staticmethod
        def encode_int(i, size=4):
            return i.to_bytes(size, "big")

        @abstractmethod
        def payload(self):
            """Return iterable of bytes that make the content of chunk"""
            pass

        def to_bytes(self):
            payload_bytes = b"".join(self.payload())
            length = self.encode_int(len(payload_bytes))
            type_and_payload = self.type + payload_bytes
            crc = self.encode_int(crc32(type_and_payload))
            return length + type_and_payload + crc
    
    class IhdrChunk(Chunk):
        GREYSCALE = 0
        TRUECOLOUR = 2
        INDEXED_COLOUR = 3
        GREYSCALE_WITH_ALPHA = 4
        TRUECOLOUR_WITH_ALPHA = 6
        NO_INTERLACE = 0
        ADAM7_INTERLACE = 1
        
        def __init__(self, width, height, bit_depth, color_type,
                     interlace_method=NO_INTERLACE):
            assert color_type in (self.GREYSCALE, self.TRUECOLOUR,
                                  self.INDEXED_COLOUR,
                                  self.GREYSCALE_WITH_ALPHA,
                                  self.TRUECOLOUR_WITH_ALPHA)
            assert interlace_method in (self.NO_INTERLACE, self.ADAM7_INTERLACE)
            super().__init__(b"IHDR")
            self.width = width
            self.height = height
            self.bit_depth = bit_depth
            self.color_type = color_type
            self.compression_method = 0  # only deflate
            self.filter_method = 0  # only adaptive filtering with 5 basic types
            self.interlace_method = interlace_method
            
        def payload(self):
            yield self.encode_int(self.width)
            yield self.encode_int(self.height)
            yield self.encode_int(self.bit_depth, 1)
            yield self.encode_int(self.color_type, 1)
            yield self.encode_int(self.compression_method, 1)
            yield self.encode_int(self.filter_method, 1)
            yield self.encode_int(self.interlace_method, 1)
    
    class PlteChunk(Chunk):
        def __init__(self, colors=None):
            super().__init__(b"PLTE")
            self.colors = colors
        
        def payload(self):
            for color in self.colors:
                yield bytes(color)
    
    class IdatChunk(Chunk):
        def __init__(self):
            super().__init__(b"IDAT")
            self._payload = bytearray()

        @classmethod
        def encode_line(cls, bars, bar_width=1):
            black_bar = 0
            white_bar = (1 << bar_width) - 1
            value = 0
            length = 0
            arr = bytearray()
            for bar in bars:
                value <<= bar_width
                value |= black_bar if bar else white_bar
                length += bar_width
                if length >= 4096:
                    length &= 4095
                    out = value >> length
                    value &= (1 << length) - 1
                    arr.extend(out.to_bytes(512, "big"))
            padding = -length % 8
            if padding:
                value <<= padding
                length += padding
            arr.extend(value.to_bytes(length // 8, "big"))
            return arr

        def add_line(self, filter_code, line, prev_line=None, bar_width=1):
            self._payload.append(filter_code)
            raw_line = self.encode_line(line, bar_width)
            if filter_code == 0:
                self._payload.extend(raw_line)
            elif filter_code == 1:
                next_it = iter(line)
                self._payload.append(next(next_it))
                self._payload.extend(
                    (raw - prev) & 255
                    for raw, prev in zip(next_it, raw_line)
                )
            elif filter_code == 2:
                filtered_line = bytes(
                    (raw - prev) & 255
                    for raw, prev in zip(raw_line, prev_line)
                )
                self._payload.extend(filtered_line)
            else:
                raise NotImplementedError()
            return raw_line

        def set_payload_from_barcode_line(
            self, bars, bar_width, height, label=None
        ):
            lines = bytearray(1)
            prev_line = self.encode_line(bars, bar_width)
            lines.extend(prev_line)
            rep_line = bytes((2,)) + bytes(len(prev_line))
            lines.extend(rep_line * (height - 1))
            if label is not None:
                for line in label:
                    filter_code = 0 if sum(line) < 0.1 * len(line) else 2
                    lines.append(filter_code)
                    if filter_code == 0:
                        prev_line = self.encode_line(line)
                        lines.extend(prev_line)
                    elif filter_code == 2:
                        raw_line = self.encode_line(line)
                        filtered_line = bytes(
                            (raw - prev) & 255
                            for raw, prev in zip(raw_line, prev_line)
                        )
                        lines.extend(filtered_line)
                        prev_line = raw_line
            self._payload = lines

        def set_payload_from_squares(self, squares, scale, label=None):
            lines = bytearray()
            for line in squares:
                lines.append(0)
                encoded_line = self.encode_line(line, scale)
                lines.extend(encoded_line)
                rep_line = bytes((2,)) + bytes(len(encoded_line))
                lines.extend(rep_line * (scale - 1))
            self._payload = lines
        
        def payload(self):
            yield compress(self._payload)

    class IendChunk(Chunk):
        def __init__(self):
            super().__init__(b"IEND")
        
        def payload(self):
            yield b""
    
    @classmethod
    def save_barcode(cls, image_filename, bars, bar_width=None, height=None,
                     indexed=False, label=None):
        bars = list(bars)
        bar_width = bar_width or 2
        height = height or 50
        width = bar_width * len(bars)
        bit_depth = 1
        with open(image_filename, "wb") as out_file:
            out_file.write(cls.HEADER)
            out_file.write(
                cls.IhdrChunk(
                    width,
                    height if label is None else height + len(label),
                    bit_depth,
                    cls.IhdrChunk.GREYSCALE
                ).to_bytes()
            )
            data_chunk = cls.IdatChunk()
            data_chunk.set_payload_from_barcode_line(
                bars, bar_width, height, label
            )
            out_file.write(data_chunk.to_bytes())
            out_file.write(cls.IendChunk().to_bytes())

    def _write_header(self, image_file):
        image_file.write(self.HEADER)
        ihdr = self.IhdrChunk(
            self.image_width,
            self.image_height,
            1,  # color bit depth
            self.IhdrChunk.GREYSCALE
        )
        image_file.write(ihdr.to_bytes())
    
    def _write_bars(self, image_file):
        self.idat = self.IdatChunk()
        self.idat.set_payload_from_barcode_line(
            self.data_bits,
            self.scale,
            self.barcode_height
        )

    def _write_squares(self, image_file):
        self.idat = self.IdatChunk()
        self.idat.set_payload_from_squares(self.data_bits, self.scale)

    def _write_text_area(self, image_file):
        if self.text_areas is None:
            return
        label = self.render_label()
        prev_line = None
        line = None
        for line in label:
            filter_code = 0
            if prev_line is not None and sum(line) < len(line) / 10:
                filter_code = 2

            prev_line = self.idat.add_line(
                filter_code,
                line,
                prev_line,
                bar_width=1
            )

    def _write_finish(self, image_file):
        image_file.write(self.idat.to_bytes())
        image_file.write(self.IendChunk().to_bytes())
