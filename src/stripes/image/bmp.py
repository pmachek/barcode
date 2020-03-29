from .image import BarcodeImage


class BmpBarcodeImage(BarcodeImage):
    @classmethod
    def _unpadded_width(cls, width, bits_per_pixel):
        """Returns size of image row in bytes, without padding

        :param int width:           Number of pixels in row
        :param int bits_per_pixel:  Pixel size in bits
        :return:                    Size of row in bytes without padding"""
        return (width * bits_per_pixel - 1) // 8 + 1

    @classmethod
    def _width_alignment(cls, width):
        """Computes alignment for image row - number of extra bytes
to make row byte size divisible by four.

        :param int width:       Number of pixels in row
        :return:                Number of alignment bytes"""
        return -width % 4

    @classmethod
    def _padded_width(cls, width, bits_per_pixel):
        """Returns size of image row in bytes, padding included

        :param int width:           Number of pixels in row
        :param int bits_per_pixel:  Pixel size in bits
        :return:                    Size of row in bytes including padding"""
        unpadded = cls._unpadded_width(width, bits_per_pixel)
        padded = unpadded + cls._width_alignment(unpadded)
        return padded
    
    @classmethod
    def header(cls, width, height, bits_per_pixel, indexed=True):
        """Returns bitmap file header for image of given parameters

        :param int width:           Width of image in pixels
        :param int height:          Height of image in pixels
        :param int bits_per_pixel:  Pixel size in bits
        :param bool indexed:        Whether indexed palette is used
        :return:                    Bitmap header bytes"""
        palette_colors = 1 << bits_per_pixel if indexed else 0
        padded_width = cls._padded_width(width, bits_per_pixel)
        raw_bmp_size = height * padded_width
        offset = 54 + 4 * palette_colors  # pixel data offset
        file_size = offset + raw_bmp_size
        header_bytes = b"".join((
            b"BM",
            file_size.to_bytes(4, "little"),
            (0).to_bytes(4, "little"),
            offset.to_bytes(4, "little"),
            (40).to_bytes(4, "little"),  # dib header size
            width.to_bytes(4, "little"),
            # pixel rows are stored in reversed order unless height is negative
            (-height & 0xFFFFFFFF).to_bytes(4, "little"),
            (1).to_bytes(2, "little"),  # color planes
            bits_per_pixel.to_bytes(2, "little"),
            (0).to_bytes(4, "little"),
            raw_bmp_size.to_bytes(4, "little"),
            (2835).to_bytes(4, "little"),  # pixels per meter
            (2835).to_bytes(4, "little"),  # pixels per meter
            palette_colors.to_bytes(4, "little"),
            (0).to_bytes(4, "little")
        ))
        if indexed:
            header_bytes += (0).to_bytes(4, "little") + \
                            (0xFFFFFF).to_bytes(4, "little")
        return header_bytes
    
    # TODO: Support more bit depths
    @classmethod
    def encode_line(cls, bars, scale, bits_per_pixel):
        """Encodes single image row

        :param Iterable[int] bars:  Array of bits, 0 for white pixel,
                                    1 for black
        :param int bar_width:       Width of thinnest bar in pixels
        :param bool indexed:        Whether indexed palette is used
        :return:                    Bytes of image line, including padding
        """
        width = len(bars) * scale
        if (scale * bits_per_pixel) % 8:
            as_int = 0
            unpadded_width = cls._unpadded_width(width, bits_per_pixel)
            bar_bitlength = bits_per_pixel * scale
            white = (1 << bar_bitlength) - 1
            for bit in bars:
                as_int <<= bar_bitlength
                if not bit:
                    as_int |= white
            pad_bits = -width % 8
            as_int <<= pad_bits
            translated = as_int.to_bytes(unpadded_width, "big")
        else:
            black = b"\x00" * ((scale * bits_per_pixel) // 8)
            white = b"\xff" * ((scale * bits_per_pixel) // 8)
            translated = b"".join(black if bit else white for bit in bars)
        align = cls._width_alignment(
            cls._unpadded_width(width, bits_per_pixel)
        )
        align_bytes = bytes(align)
        line = translated + align_bytes
        return line
    
    def _write_header(self, image_file):
        image_file.write(
            self.header(self.image_width, self.image_height, 1)
        )
    
    def _write_bars(self, image_file):
        line = self.encode_line(self.data_bits, self.scale, 1)
        for _ in range(self.barcode_height):
            image_file.write(line)
    
    def _write_squares(self, image_file):
        for raw_line in self.data_bits:
            line = self.encode_line(raw_line, self.scale, 1)
            for _ in range(self.scale):
                image_file.write(line)

    def _write_text_area(self, image_file):
        label = self.render_label()
        for raw_line in label:
            line = self.encode_line(raw_line, 1, 1)
            image_file.write(line)

    def _write_finish(self, image_file):
        # Nothing to do here
        pass
