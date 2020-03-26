from .encoding import BarcodeEncoding


class Code128(BarcodeEncoding):
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

    @classmethod
    def _enc_A(cls, char):
        """Encode single character from A alphabet
        
        :param str char:    A character
        :return:           Character code integer"""
        code = ord(char)
        if code < 32:
            return code + 64
        elif 32 <= code < 96:
            return code - 32
        else:
            raise ValueError(
                "{!r} can't be encoded in code128A alphabet".format(char)
            )

    @classmethod
    def _enc_B(cls, char):
        """Encode single character from B alphabet

        :param str char:    A character
        :return:           Character code integer"""
        code = ord(char)
        if 32 <= code < 128:
            return code - 32
        else:
            raise ValueError(
                "{!r} can't be encoded in code128B alphabet".format(char)
            )

    @classmethod
    def _enc_C(cls, two_chars):
        """Encode pair of integer digit characters into C alphabet code

        :param str char:    Two digit characters
        :return:            Character code integer
        """
        return int(two_chars)

    @classmethod
    def _encode_one(cls, alphabet, s):
        """Encode a character or pair of digits into character code
of chosen alphabet

        :param str alphabet: "A", "B" or "C" alphabet
        :param str s:        Character or pair of digits
        :return:             Character code (integer)"""
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
    def bars(cls, s, encoding="B"):
        """Encodes string to series of bits, 1 for black bar,
0 for background according to selected encoding.

    :param s:               data to encode
    :param encoding:        string "A", "B", or "C"
    :return:                Yields bits of barcode (0/1)"""
        encodings = {
            "A": cls.encode_A,
            "B": cls.encode_B,
            "C": cls.encode_C,
        }
        enc = encodings.get(encoding, None)
        if enc is None:
            raise ValueError("Unsupported encoding {!r}".format(encoding))
        codes = enc(s)
        yield from cls.bits(0, 10)
        checksum = 0
        for i, n in enumerate(codes):
            yield from cls.bits(cls.pattern[n], cls.code_bitlength)
            checksum += n * max([1, i])
        checksum %= 103
        yield from cls.bits(cls.pattern[checksum], cls.code_bitlength)
        yield from cls.bits(cls.stop, 13)
        yield from cls.bits(0, 10)
    
    @classmethod
    def label_text_areas(cls, data, bar_width):
        return [
            {
                "text": data,
                "x_start": 3,
                "y_start": 3,
                "x_end": (len(data) + 1) * cls.code_bitlength + 27,
                "y_end": None
            }
        ]
