#!/usr/bin/env python3
# Copyright Petr Machek
#
# Library for generating CODE93, CODE128B, CODE128C and EAN13 barcodes
# as .bmp, .svg or .png images
#
from functools import partial
from itertools import chain

from image import BitmapImage, SvgImage, PngImage
import font


def bits(num, length):
    """
    Make iterator of integer's bits (1/0 integers).
    Generates 'length' bits, most significant bit comes first.

    :param num:                 Number to encode
    :param length:              Number of bits to iterate through
    :return:                    Iterator of bits
    """
    for i in range(length - 1, -1, -1):
        yield (num >> i) & 1


class Code128:
    """
    Encoder for Code128 (A, B and C variant) barcode.
    """
    # stripe patterns written as a number, 1 bit for black stripe,
    # 0 bit for white background, 11 bits long
    pattern = [
        1740, 1644, 1638, 1176, 1164, 1100, 1224, 1220, 1124, 1608, 1604,
        1572, 1436, 1244, 1230, 1484, 1260, 1254, 1650, 1628, 1614, 1764,
        1652, 1902, 1868, 1836, 1830, 1892, 1844, 1842, 1752, 1734, 1590,
        1304, 1112, 1094, 1416, 1128, 1122, 1672, 1576, 1570, 1464, 1422,
        1134, 1496, 1478, 1142, 1910, 1678, 1582, 1768, 1762, 1774, 1880,
        1862, 1814, 1896, 1890, 1818, 1914, 1602, 1930, 1328, 1292, 1200,
        1158, 1068, 1062, 1424, 1412, 1232, 1218, 1076, 1074, 1554, 1616,
        1978, 1556, 1146, 1340, 1212, 1182, 1508, 1268, 1266, 1956, 1940,
        1938, 1758, 1782, 1974, 1400, 1310, 1118, 1512, 1506, 1960, 1954,
        1502, 1518, 1886, 1966, 1668, 1680, 1692
    ]

    # start pattern, different for every encoding
    start_A = 103
    start_B = 104
    start_C = 105

    # patterns for switching from one encoding to another
    shift_A_to_B = 98
    shift_B_to_A = 98
    switch_A_to_B = 100
    switch_A_to_C = 99
    switch_B_to_A = 101
    switch_B_to_C = 99
    switch_C_to_A = 101
    switch_C_to_B = 102

    # stop pattern, 13 bits long
    stop = 6379

    # bit length of non-control characters
    code_bitlength = 11

    bits = partial(bits, length=code_bitlength)

    @classmethod
    def _enc_A(cls, char):
        code = ord(char)
        if code < 32:
            return code + 64
        elif 32 <= code < 96:
            return code - 32
        else:
            er = "{!r} can't be encoded in code128A alphabet".format(char)
            raise ValueError(er)

    @classmethod
    def _enc_B(cls, char):
        code = ord(char)
        if 32 <= code < 128:
            return code - 32
        else:
            er = "{!r} can't be encoded in code128B alphabet".format(char)
            raise ValueError(er)

    @classmethod
    def _enc_C(cls, two_chars):
        return int(two_chars)

    @classmethod
    def _encode_one(cls, alphabet, s):
        if alphabet == "A":
            return cls._enc_A(s)
        elif alphabet == "B":
            return cls._enc_B(s)
        elif alphabet == "C":
            return cls._enc_C(s)
        raise ValueError("Unknown encoding: {!r}".format(alphabet))

    @classmethod
    def encode_A(cls, s):
        yield cls.start_A
        for char in s:
            yield cls._enc_A(char)

    @classmethod
    def encode_B(cls, s):
        yield cls.start_B
        for char in s:
            yield cls._enc_B(char)

    @classmethod
    def encode_C(cls, s):
        if len(s) & 1 == 1:
            raise ValueError("String length must be even")
        yield cls.start_C
        for i in range(0, len(s), 2):
            two_chars = int(s[i:i + 2])
            yield cls._enc_C(two_chars)

    @classmethod
    def bars(cls, s, encoding=None):
        """
    Encodes string to series of bits, 1 for black bar,
    0 for background according to selected encoding.

    :param s:               data to encode
    :param encoding:        string "A", "B", or "C"
    :return:                Array of bits (0, 1 values)
        """
        encodings = {
            "A": cls.encode_A,
            "B": cls.encode_B,
            "C": cls.encode_C,
        }
        enc = encodings.get(encoding, None)
        if enc is None:
            raise ValueError("Unsupported encoding {!r}".format(encoding))
        codes = enc(s)
        yield from cls.bits(0, length=10)
        checksum = 0
        for i, n in enumerate(codes):
            yield from cls.bits(cls.pattern[n])
            checksum += n * max([1, i])
        checksum %= 103
        yield from cls.bits(cls.pattern[checksum])
        yield from cls.bits(cls.stop, length=13)
        yield from cls.bits(0, length=10)
    
    @classmethod
    def label_text_areas(cls, data, bar_width):
        return [
            {
                "text": data,
                "x_start": None,
                "y_start": 3,
                "x_end": None,
                "y_end": None
            }
        ]


class Code93:
    """
    Encoder for Code93 barcodes.
    """
    # stripe patterns, 1 for black, 0 for background white
    pattern = [
        0b100010100, 0b101001000, 0b101000100, 0b101000010, 0b100101000,
        0b100100100, 0b100100010, 0b101010000, 0b100010010, 0b100001010,
        0b110101000, 0b110100100, 0b110100010, 0b110010100, 0b110010010,
        0b110001010, 0b101101000, 0b101100100, 0b101100010, 0b100110100,
        0b100011010, 0b101011000, 0b101001100, 0b101000110, 0b100101100,
        0b100010110, 0b110110100, 0b110110010, 0b110101100, 0b110100110,
        0b110010110, 0b110011010, 0b101101100, 0b101100110, 0b100110110,
        0b100111010, 0b100101110, 0b111010100, 0b111010010, 0b111001010,
        0b101101110, 0b101110110, 0b110101110, 0b100100110, 0b111011010,
        0b111010110, 0b100110010, 0b101011110
    ]

    # escape codes
    esc1 = 43
    esc2 = 44
    esc3 = 45
    esc4 = 46

    # nonalphabetical characters encoded without escape codes
    enc = {"-": 36, ".": 37, " ": 38, "$": 39, "/": 40, "+": 41, "%": 42}

    # bit patterns symbolizing start and stop
    start = 47
    stop = 47

    code_bitlength = 9

    bits = partial(bits, length=code_bitlength)

    @classmethod
    def _encode_upper(cls, char):
        """
    Encodes uppercase character

    :param char:        string of length one to encode
    :return:            yields character code
        """
        yield ord(char) - ord("A") + 10

    @classmethod
    def _encode_lower(cls, char):
        """
    Encodes lowercase character

    :param char:        string of length one to encode
    :return:            yields two integers, escape code
                        and character code
        """
        yield cls.esc4
        yield ord(char) - ord("a") + 10

    @classmethod
    def _encode_other(cls, char):
        """
    Encodes non-alphabetic character

    :param char:        string of length one to encode
    :return:
        """
        i = ord(char)
        if char in cls.enc:
            yield cls.enc[char]
        elif i > 127:
            raise ValueError(
                "Character {!r} can't be encoded in Code93".format(char)
            )
        elif i == 0:
            yield cls.esc2
            yield 30
        elif i <= 26:
            yield cls.esc1
            yield i + 9
        elif i <= 31:
            yield cls.esc2
            yield i - 17
        elif 33 <= i <= 35 or 38 <= i <= 42 or i == 44 or i == 58:
            yield cls.esc3
            yield i - 23
        elif 59 <= i <= 63:
            yield cls.esc2
            yield i - 44
        elif i == 64:
            yield cls.esc2
            yield 31
        elif 91 <= i <= 95:
            yield cls.esc2
            yield i - 71
        elif i == 96:
            yield cls.esc2
            yield 32
        elif 123 <= i <= 127:
            yield cls.esc2
            yield i - 98
        else:
            raise ValueError("Code93 encoding implementation error!")

    @classmethod
    def encode(cls, s):
        """
    Encodes string to array of codes

    :param s:           String of characters to encode
    :return:            Array of codes
        """
        for char in s:
            if char.isnumeric():
                yield int(char)
            elif char.isupper():
                yield from cls._encode_upper(char)
            elif char.islower():
                yield from cls._encode_lower(char)
            else:
                yield from cls._encode_other(char)

    @classmethod
    def bars(cls, s):
        """
    Encodes string to series of bits, 1 for black bar,
    0 for background

    :param s:               Data to encode
    :return:                Array of bits (0, 1 values)
        """
        codes = list(cls.encode(s))
        weight = len(codes)
        checksum1 = 0
        checksum2 = 0
        yield from cls.bits(0, length=cls.code_bitlength + 1)
        yield from cls.bits(cls.start)
        for code in codes:
            yield from cls.bits(cls.pattern[code])
            checksum1 += weight * code
            checksum2 += (weight + 1) * code
            weight -= 1
        checksum2 += checksum1
        checksum1 %= 47
        checksum2 %= 47
        yield from cls.bits(cls.pattern[checksum1])
        yield from cls.bits(cls.pattern[checksum2])
        yield from cls.bits(cls.stop)
        yield from cls.bits(1, length=1)
        yield from cls.bits(0, length=cls.code_bitlength + 1)

    @classmethod
    def label_text_areas(cls, data, bar_width):
        return [
            {
                "text": data,
                "x_start": None,
                "y_start": 3,
                "x_end": None,
                "y_end": None
            }
        ]


class Ean:
    patterns = (
        # L pattern, G pattern, R pattern
        (0b0001101, 0b0100111, 0b1110010),  # 0
        (0b0011001, 0b0110011, 0b1100110),  # 1
        (0b0010011, 0b0011011, 0b1101100),  # 2
        (0b0111101, 0b0100001, 0b1000010),  # 3
        (0b0100011, 0b0011101, 0b1011100),  # 4
        (0b0110001, 0b0111001, 0b1001110),  # 5
        (0b0101111, 0b0000101, 0b1010000),  # 6
        (0b0111011, 0b0010001, 0b1000100),  # 7
        (0b0110111, 0b0001001, 0b1001000),  # 8
        (0b0001011, 0b0010111, 0b1110100)   # 9
    )

    code_length = 7
    bits = partial(bits, length=code_length)

    # EAN13 constants
    quiet_zone_left_ean13 = 13
    quiet_zone_right_ean13 = 8
    # LG pattern chosen by first digit. 0 bit for L, 1 bit for G
    lg_pattern_ean13 = (
        0b000000, 0b001011, 0b001101, 0b001110, 0b010011,
        0b011001, 0b011100, 0b010101, 0b010110, 0b011010
    )

    # EAN8 constants
    # TODO: Check standard for quiet zone widths
    quiet_zone_left_ean8 = 8
    quiet_zone_right_ean8 = 8

    @classmethod
    def check_digit(cls, number_sequence, validate=True):
        last_digit = None
        length = len(number_sequence)
        if length == 13 or length == 8:
            last_digit = int(number_sequence[-1])
            number_sequence = number_sequence[:length - 1]
            length -= 1
        weight = 3
        checksum = 0
        for number in (int(char) for char in reversed(number_sequence)):
            if number < 0 or number > 9:
                raise ValueError("EAN can contain only numbers 0-9")
            checksum += weight * number
            if weight == 3:
                weight = 1
            else:
                weight = 3
        check = -checksum % 10
        if last_digit is not None and validate and check != last_digit:
            raise ValueError("Supplied check digit is invalid")
        return check
    
    @classmethod
    def with_check_digit(cls, number_sequence):
        if len(number_sequence) in (13, 8):
            return number_sequence
        if len(number_sequence) in (12, 7):
            return number_sequence + str(cls.check_digit(number_sequence))
        raise ValueError("Invalid EAN code length. Expected 12, 13, 7 or 8 digits")

    @classmethod
    def bars(cls, number_sequence):
        length = len(number_sequence)
        if length == 12 or length == 13:
            yield from cls.ean13_bars(number_sequence)
        elif length == 7 or length == 8:
            yield from cls.ean8_bars(number_sequence)
        else:
            raise ValueError("Invalid EAN length: {}. ".format(length))

    @classmethod
    def ean13_bars(cls, number_sequence):
        check_digit = cls.check_digit(number_sequence)
        it = iter(number_sequence)
        first_digit = int(next(it))
        lg_pattern = cls.lg_pattern_ean13[first_digit]

        yield from bits(0, cls.quiet_zone_left_ean13)
        # barcode start
        yield from bits(0b101, 3)

        for i, number in zip(range(11), (int(char) for char in it)):
            if i < 6:
                lgr_index = (lg_pattern >> (5 - i)) & 1
            else:
                lgr_index = 2
            yield from cls.bits(cls.patterns[number][lgr_index])
            if i == 5:
                # middle separator, between first 6 and last 6 digits
                yield from bits(0b01010, 5)

        yield from cls.bits(cls.patterns[check_digit][2])        
        yield from bits(0b101, 3)
        yield from bits(0, cls.quiet_zone_right_ean13)
    
    @classmethod
    def ean8_bars(cls, number_sequence):
        if isinstance(number_sequence, str):
            number_sequence = [ord(c) - ord('0') for c in number_sequence]
        check_digit = cls.check_digit(number_sequence)
        
        yield from bits(0, cls.quiet_zone_left_ean8)
        yield from bits(0b101, 3)
        
        for i, number in zip(range(7), number_sequence):
            lgr_index = 0 if i < 4 else 2
            yield from cls.bits(cls.patterns[number][lgr_index])
            if i == 3:
                yield from bits(0b01010, 5)

        yield from cls.bits(cls.patterns[check_digit][2])
        yield from bits(0b101, 3)
        yield from bits(0, cls.quiet_zone_left_ean8)
    
    @classmethod
    def label_text_areas(cls, number_sequence, bar_width):
        number_sequence = cls.with_check_digit(number_sequence)
        if len(number_sequence) == 8:
            return cls.label_text_areas_ean8(number_sequence)
        if len(number_sequence) == 13:
            return cls.label_text_areas_ean13(number_sequence)
        raise ValueError("Number sequence must be 7, 8, 12 or 13 characters long")

    @classmethod
    def label_mask_ean13(cls, number_sequence, bar_width):
        # TODO: Do not use bar width, let other layer figure it out
        for _ in range(6 * bar_width):  # separator bars height
            yield chain(
                bits(0, bar_width * cls.quiet_zone_left_ean13),
                bits((1 << bar_width) - 1, bar_width),
                bits(0, bar_width),
                bits((1 << bar_width) - 1, bar_width),
                bits(0, bar_width * cls.code_length * 6),
                bits(0, bar_width),
                bits((1 << bar_width) - 1, bar_width),
                bits(0, bar_width),
                bits((1 << bar_width) - 1, bar_width),
                bits(0, bar_width),
                bits(0, bar_width * cls.code_length * 6),
                bits((1 << bar_width) - 1, bar_width),
                bits(0, bar_width),
                bits((1 << bar_width) - 1, bar_width),
            )

    @classmethod
    def label_text_areas_ean13(cls, number_sequence):
        return [
            {
                "text": number_sequence[0],
                "x_start": 1,
                "y_start": 3,
                "x_end": 11,
                "y_end": None
            },
            {
                "text": number_sequence[1:7],
                "x_start": 16,
                "y_start": 3,
                "x_end": 56,
                "y_end": None
            },
            {
                "text": number_sequence[7:],
                "x_start": 62,
                "y_start": 3,
                "x_end": 104,
                "y_end": None
            }
        ]
    
    @classmethod
    def label_text_areas_ean8(cls, number_sequence):
        return [
            {

            }
        ]


def pick_save_handler(image_filename):
    extension = image_filename.rsplit(".", 1)[-1].lower()
    if extension == "bmp":
        return BitmapImage.save_barcode
    elif extension == "png":
        return PngImage.save_barcode
    elif extension == "svg":
        return SvgImage.save_barcode
    else:
        raise ValueError("No save method found for given file extension")


def numeric_barcode(image_filename, number, align=6, save_fn=None):
    save_fn = save_fn or pick_save_handler(image_filename)
    s = "{:0{fill}}".format(number, fill=align)
    bars = Code128.bars(s, "C")
    save_fn(image_filename, bars)


def text_barcode(image_filename, text, save_fn=None):
    save_fn = save_fn or pick_save_handler(image_filename)
    bars = Code128.bars(text, "B")
    save_fn(image_filename, bars)


def barcode(image_filename, data, save_fn=None):
    save_fn = save_fn or pick_save_handler(image_filename)
    bars = Code128.bars(data, "B")
    save_fn(image_filename, bars)


def _test_code128c():
    for i in range(10):
        c = 0
        for j in range(10):
            c += (100**j) * (10*i + j)
        filename = "_code128C_{}.bmp".format(i)
        numeric_barcode(filename, c, 20)
        filename2 = "_code128C_{}.svg".format(i)
        numeric_barcode(filename2, c, 20)


def _test_code93():
    for i in range(32):
        lower = 4 * i
        upper = 4 * (i + 1)
        data = "".join(chr(j) for j in range(lower, upper))
        filename = "_code93_{}.bmp".format(i)
        bars = Code93.bars(data)
        BitmapImage.save_barcode(filename, bars)
        # previous bars iterator was exhausted
        bars = Code93.bars(data)
        filename2 = "_code93_{}.svg".format(i)
        SvgImage.save_barcode(filename2, bars)
        bars = Code93.bars(data)
        filename3 = "_code93_{}.png".format(i)
        PngImage.save_barcode(filename3, bars)


def _test_ean():
    data = "012345678910"
    bars = Ean.bars(data)
    filename = "_ean_{}.png".format(data)
    bars = list(bars)
    canvas = [
        [0 for i in range(len(bars) * 2)]
        for y in range(25)
    ]
    font.font5x7.render_text_areas(
        Ean.label_text_areas(data, 2),
        canvas
    )
    # TODO: mix label and label mask somewhere else
    label_mask = Ean.label_mask_ean13(data, 2)
    for v, line in enumerate(label_mask):
        for h, bit in enumerate(line):
            canvas[v][h] |= bit
    PngImage.save_barcode(filename, bars, label=canvas)


def _test_all():
    #_test_code128c()
    #_test_code93()
    _test_ean()


if __name__ == "__main__":
    _test_all()
