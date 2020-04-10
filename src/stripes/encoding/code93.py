from .encoding import BarcodeEncoding


class Code93(BarcodeEncoding):
    """Encoder for Code93 barcodes."""
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

    # bits = partial(bits, length=code_bitlength)

    @classmethod
    def _encode_upper(cls, char):
        """Encodes uppercase character

    :param str char:    string of length one to encode
    :return:            yields character code"""
        yield ord(char) - ord("A") + 10

    @classmethod
    def _encode_lower(cls, char):
        """Encodes lowercase character

    :param str char:    string of length one to encode
    :return:            yields two integers, escape code
                        and character code"""
        yield cls.esc4
        yield ord(char) - ord("a") + 10

    @classmethod
    def _encode_other(cls, char):
        """Encodes non-alphabetic character

    :param str char:    string of length one to encode
    :return:            yields integer of character code, in some
                        cases preceded by escape code"""
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
        """Encodes string to array of codes

    :param str s:       String of characters to encode
    :return:            Array of codes"""
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
        """Encodes string to series of bits, 1 for black bar, 0 for background

    :param str s:           Data to encode
    :return:                Array of bits (0, 1 values)"""
        codes = list(cls.encode(s))
        weight = len(codes)
        checksum1 = 0
        checksum2 = 0
        yield from cls.bits(0, cls.code_bitlength + 1)
        yield from cls.bits(cls.pattern[cls.start], cls.code_bitlength)
        for code in codes:
            yield from cls.bits(cls.pattern[code], cls.code_bitlength)
            checksum1 += weight * code
            checksum2 += (weight + 1) * code
            weight -= 1
        checksum2 += checksum1
        checksum1 %= 47
        checksum2 %= 47
        yield from cls.bits(cls.pattern[checksum1], cls.code_bitlength)
        yield from cls.bits(cls.pattern[checksum2], cls.code_bitlength)
        yield from cls.bits(cls.pattern[cls.stop], cls.code_bitlength)
        yield from cls.bits(1, 1)
        yield from cls.bits(0, cls.code_bitlength + 1)

    @classmethod
    def label_text_areas(cls, data):
        """Returns description of shape of areas where the text label
can be rendered.

    :param str data:        Label text"""
        return [
            {
                "text": data,
                "x_start": 3,
                "y_start": 3,
                "x_end": (len(data) + 6) * cls.code_bitlength - 3,
                "y_end": None
            }
        ]
