#!/usr/bin/env python3
# Copyright Petr Machek
#
# Library for generating CODE93, CODE128B and CODE128C barcodes
# as bitmaps or svg images
#
from zlib import compress, crc32


class BitmapImage:
    """
    Class for saving barcode images as bitmap (.bmp) files.
    """
    ZERO = 0
    OFFSET = 54
    DIBHEADERSIZE = 40
    COLORPLANES = 1
    BITSPERPIXEL = 24
    COMPRESSION = 0
    PIXELSPERMETER = 2835  # pretty much random value
    BARCODE_WHITE = 0x00FFFFFF
    BARCODE_BLACK = 0x00000000

    @classmethod
    def _unpadded_width(cls, width, indexed):
        """
        Returns size of image row in bytes, without padding

        :param width:           Number of pixels in row
        :param indexed:         Whether indexed palette is used
        """
        bits_per_pixel = 1 if indexed else cls.BITSPERPIXEL
        return (width * bits_per_pixel - 1) // 8 + 1

    @classmethod
    def _alignment(cls, width):
        """
        Computes alignment for image row - number of extra bytes
        to make row byte size divisible by four.

        :param width:           Number of pixels in row
        :return:                Number of alignment bytes
        """
        return -width % 4

    @classmethod
    def _padded_width(cls, width, indexed):
        """
        Returns size of image row in bytes, padding included

        :param width:           Number of pixels in row
        :param indexed:         Whether indexed palette is used
        """
        unpadded = cls._unpadded_width(width, indexed)
        padded = unpadded + cls._alignment(unpadded)
        return padded

    @classmethod
    def _c_int(cls, x):
        return x.to_bytes(4, "little")

    @classmethod
    def _c_smallint(cls, x):
        return x.to_bytes(2, "little")

    @classmethod
    def header(cls, width, height, indexed=False):
        """
        Returns bitmap file header for image of given parameters

        :param width:           Width of image in pixels
        :param height:          Height of image in pixels
        :param indexed:         Whether indexed palette is used
        """
        bits_per_pixel = 1 if indexed else cls.BITSPERPIXEL
        palette_colors = 2 if indexed else 0
        padded_width = cls._padded_width(width, indexed)
        raw_bmp_len = height * padded_width
        offset = cls.OFFSET + 4 * palette_colors
        filesize = offset + raw_bmp_len
        header_bytes = b"".join((
            b"BM",
            cls._c_int(filesize),
            cls._c_int(cls.ZERO),
            cls._c_int(offset),
            cls._c_int(cls.DIBHEADERSIZE),
            cls._c_int(width),
            cls._c_int(height),
            cls._c_smallint(cls.COLORPLANES),
            cls._c_smallint(bits_per_pixel),
            cls._c_int(cls.COMPRESSION),
            cls._c_int(raw_bmp_len),
            cls._c_int(cls.PIXELSPERMETER),
            cls._c_int(cls.PIXELSPERMETER),
            cls._c_int(palette_colors),
            cls._c_int(cls.ZERO)
        ))
        if indexed:
            header_bytes += cls._c_int(cls.BARCODE_WHITE) + \
                            cls._c_int(cls.BARCODE_BLACK)
        return header_bytes

    @classmethod
    def encode_line(cls, bars, bar_width, indexed):
        """
        Encodes single image row

        :param bars:            Array of bits, 0 for white pixel,
                                1 for black
        :param bar_width:       Width of thinnest bar in pixels
        :param indexed:         Whether indexed palette is used
        """
        width = len(bars) * bar_width
        if indexed:
            as_int = 0
            unpadded_width = cls._unpadded_width(width, indexed)
            black = (1 << bar_width) - 1
            for bit in bars:
                as_int = (as_int << bar_width)
                if bit:
                    as_int |= black
            pad_bits = 8 - width % 8
            if pad_bits != 8:
                as_int <<= pad_bits
            translated = as_int.to_bytes(unpadded_width, "big")
        else:
            black = b"\x00\x00\x00" * bar_width
            white = b"\xff\xff\xff" * bar_width
            translated = b"".join(black if bit else white for bit in bars)
        align = cls._alignment(cls._unpadded_width(width, indexed))
        align_bytes = bytes(align)
        line = translated + align_bytes
        return line

    @classmethod
    def save_barcode(cls, image_path, bars, bar_width=None, height=None,
                     indexed=False):
        """
        Saves barcode image to a file

        :param image_path:          Path to image to be created
        :param bars:                Iterable of bits
        :param bar_width:           Width of thinnest bar in pixels,
                                    defaults to 2
        :param height:              Height of image in pixels,
                                    defaults to 50
        :param indexed:             Whether indexed palette is used,
                                    defaults to False
        :return:                    None
        """
        bar_width = bar_width or 2
        height = height or 50
        bars = list(bars)
        width = len(bars) * bar_width
        with open(image_path, "wb") as image_file:
            image_file.write(cls.header(width, height, indexed))
            line = cls.encode_line(bars, bar_width, indexed)
            lines = height * line
            image_file.write(lines)


class SvgImage:
    """
    Class for saving barcode image as .svg file
    """
    SVG_OPEN = """<svg xmlns="http://www.w3.org/2000/svg"
    version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink"
    width="{width}" height="{height}">\n"""
    SVG_CLOSE = "</svg>\n"
    RECTANGLE = '  <rect x="{x}" y="0" width="{width}"' \
                ' height="{height}" fill="{fill}" />\n'

    @classmethod
    def data(cls, bars, bar_width, height):
        """

        :param bars:                Iterable of bits, 1 for black bar, 0 for
                                    background white color
        :param bar_width:           Width of thinnest bar, in pixels
        :param height:              Height of image, in pixels
        :return:                    svg image data
        """
        bars = list(bars)
        width = len(bars) * bar_width
        out = [
            # svg header
            cls.SVG_OPEN.format(width=width, height=height),
            # white background
            cls.RECTANGLE.format(x=0, width=width, height=height, fill="#fff")
        ]
        widths = []
        prev = None

        # Take an iterator of 0 and 1, save offset and length
        # of each run of 1 to generate black rectangles later
        for i, bit in enumerate(bars):
            if prev == 0 and bit == 1:
                start = i
            elif prev == 1 and bit == 0:
                widths.append((start, i - start))
            prev = bit

        for x, width in widths:
            x *= bar_width
            width *= bar_width
            out.append(
                cls.RECTANGLE.format(
                    x=x,
                    width=width,
                    height=height,
                    fill="#000"
                )
            )

        out.append(cls.SVG_CLOSE)
        return b"".join(bytes(line, "ascii") for line in out)

    @classmethod
    def save_barcode(cls, image_filename, bars, bar_width=None, height=None,
                     indexed=False):
        bar_width = bar_width or 2
        height = height or 50
        with open(image_filename, "wb") as image_file:
            image_file.write(cls.data(bars, bar_width, height))


class PngImage:
    HEADER = b"\x89PNG\r\n\x1a\x0a"

    class Chunk:
        def __init__(self, type_):
            self.type = type_
        
        @staticmethod
        def _encode_int(i, size=4):
            return i.to_bytes(size, "big")

        def to_bytes(self):
            payload = b"".join(self.payload)
            length = self._encode_int(len(payload))
            type_and_payload = self.type + payload
            crc = self._encode_int(crc32(type_and_payload))
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
            
        @property
        def payload(self):
            yield self._encode_int(self.width)
            yield self._encode_int(self.height)
            yield self._encode_int(self.bit_depth, 1)
            yield self._encode_int(self.color_type, 1)
            yield self._encode_int(self.compression_method, 1)
            yield self._encode_int(self.filter_method, 1)
            yield self._encode_int(self.interlace_method, 1)
    
    class PlteChunk(Chunk):
        def __init__(self, colors=None):
            super().__init__(b"PLTE")
            self.colors = colors
        
        @property
        def payload(self):
            for color in self.colors:
                yield bytes(color)
    
    class IdatChunk(Chunk):
        def __init__(self):
            super().__init__(b"IDAT")
            self.payload = None

        def encode_line(self, bars, bar_width=1):
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
            
        def payload_from_barcode_line(self, bars, bar_width, height, label=None):
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
            self.payload = (compress(lines),)

    class IendChunk(Chunk):
        def __init__(self):
            super().__init__(b"IEND")
            self.payload = (b"",)
    
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
            data_chunk.payload_from_barcode_line(bars, bar_width, height, label)
            out_file.write(data_chunk.to_bytes())
            out_file.write(cls.IendChunk().to_bytes())
            
