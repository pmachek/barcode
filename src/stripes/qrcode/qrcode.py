# module state:
# implemented:
#       - QR codes version 1 through 40
#       - selecting optimal encoding
#       - byte, alphanumeric and numeric QR codes
# not implemented:
#       - kanji
#       - ECI QR codes
#       - splitting content of QR code into multiple QR codes

from itertools import zip_longest, chain

from .reedsolomon import ReedSolomonEncoder
from .bitarray import BitArray
from .galoisfield import modulo_gf2


capacities = (
    (152, 128, 104, 72), (272, 224, 176, 128),          # 1, 2
    (440, 352, 272, 208), (640, 512, 384, 288),         # 3, 4
    (864, 688, 496, 368), (1088, 864, 608, 480),        # 5, 6
    (1248, 992, 704, 528), (1552, 1232, 880, 688),      # 7, 8
    (1856, 1456, 1056, 800), (2192, 1728, 1232, 976),   # 9, 10
    (2592, 2032, 1440, 1120), (2960, 2320, 1648, 1264), # 11, 12
    (3424, 2672, 1952, 1440), (3688, 2920, 2088, 1576), # 13, 14
    (4184, 3320, 2360, 1784), (4712, 3624, 2600, 2024), # 15, 16
    (5176, 4056, 2936, 2264), (5768, 4504, 3176, 2504), # 17, 18
    (6360, 5016, 3560, 2728), (6888, 5352, 3880, 3080), # 19, 20
    (7456, 5172, 4096, 3248), (8048, 6256, 4544, 3536), # 21, 22
    (8752, 6880, 4912, 3712), (9392, 7312, 5312, 4112), # 23, 24
    (10208, 8000, 5744, 4304), (10960, 8496, 6032, 4768),   # 25, 26
    (11744, 9024, 6464, 5024), (12248, 9544, 6968, 5288),   # 27, 28
    (13048, 10136, 7288, 5608), (13880, 10984, 7880, 5960), # 29, 30
    (14744, 11640, 8264, 6344), (15640, 12328, 8920, 6760), # 31, 32
    (16568, 13048, 9368, 7208), (17528, 13800, 9848, 7688), # 33, 34
    (18448, 14496, 10288, 7888), (19472, 15312, 10832, 8432), # 35, 36
    (20528, 15936, 11408, 8768), (21616, 16816, 12016, 9136), # 37, 38
    (22496, 17728, 12656, 9776), (23648, 18672, 13328, 10208) # 39, 40
)

alignments = (
    (6, 18),          # 2
    (6, 22),          # 3
    (6, 26),          # 4
    (6, 30),          # 5
    (6, 34),          # 6
    (6, 22, 38),      # 7
    (6, 24, 42),      # 8
    (6, 26, 46),      # 9
    (6, 28, 50),      # 10
    (6, 30, 54),      # 11
    (6, 32, 58),      # 12
    (6, 34, 62),      # 13
    (6, 26, 46, 66),  # 14
    (6, 26, 48, 70),  # 15
    (6, 26, 50, 74),  # 16
    (6, 30, 54, 78),  # 17
    (6, 30, 56, 82),  # 18
    (6, 30, 58, 86),  # 19
    (6, 34, 62, 90),  # 20
    (6, 28, 50, 72, 94),              # 21
    (6, 26, 50, 74, 98),              # 22
    (6, 30, 54, 78, 102),             # 23
    (6, 28, 54, 80, 106),             # 24
    (6, 32, 58, 84, 110),             # 25
    (6, 30, 58, 86, 114),             # 26
    (6, 34, 62, 90, 118),             # 27
    (6, 26, 50, 74, 98, 122),         # 28
    (6, 30, 54, 78, 102, 126),        # 29
    (6, 26, 52, 78, 104, 130),        # 30
    (6, 30, 56, 82, 108, 134),        # 31
    (6, 34, 60, 86, 112, 138),        # 32
    (6, 30, 58, 86, 114, 142),        # 33
    (6, 34, 62, 90, 118, 146),        # 34
    (6, 30, 54, 78, 102, 126, 150),   # 35
    (6, 24, 50, 76, 102, 128, 154),   # 36
    (6, 28, 54, 80, 106, 132, 158),   # 37
    (6, 32, 58, 84, 110, 136, 162),   # 38
    (6, 26, 54, 82, 110, 138, 166),   # 39
    (6, 30, 58, 86, 114, 142, 170)    # 40
)

blocks = (
    ((7, 1, 19), (10, 1, 16), (13, 1, 13), (17, 1, 9)),         # 1
    ((10, 1, 34), (16, 1, 28), (22, 1, 22), (28, 1, 16)),       # 2
    ((15, 1, 55), (26, 1, 44), (18, 2, 17), (22, 2, 13)),       # 3
    ((20, 1, 80), (18, 2, 32), (26, 2, 24), (16, 4, 9)),        # 4
    ((26, 1, 108), (24, 2, 43), (18, 2, 15, 2, 16), (22, 2, 11, 2, 12)), # 5
    ((18, 2, 68), (16, 4, 27), (24, 4, 19), (28, 4, 15)),                # 6
    ((20, 2, 78), (18, 4, 31), (18, 2, 14, 4, 15), (26, 4, 13, 1, 14)),  # 7
    ((24, 2, 97), (22, 2, 38, 2, 39),
     (22, 4, 18, 2, 19), (26, 4, 14, 2, 15)), # 8
    ((30, 2, 116), (22, 3, 36, 2, 37),
     (20, 4, 16, 4, 17), (24, 4, 12, 4, 13)), # 9
    ((18, 2, 68, 2, 69), (26, 4, 43, 1, 44),
     (24, 6, 19, 2, 20), (28, 6, 15, 2, 16)), # 10
    ((20, 4, 81), (30, 1, 50, 4, 51),
     (28, 4, 22, 4, 23), (24, 3, 12, 8, 13)), # 11
    ((24, 2, 92, 2, 93), (22, 6, 36, 2, 37),
     (26, 4, 20, 6, 21), (28, 7, 14, 4, 15)), # 12
    ((26, 4, 107), (22, 8, 37, 1, 38),
     (24, 8, 20, 4, 21), (22, 12, 11, 4, 12)),    # 13
    ((30, 3, 115, 1, 116), (24, 4, 40, 5, 41),
     (20, 11, 16, 5, 17), (24, 11, 12, 5, 13)),   # 14
    ((22, 5, 87, 1, 88), (24, 5, 41, 5, 42),
     (30, 5, 24, 7, 25), (24, 11, 12, 7, 13)),    # 15
    ((24, 5, 98, 1, 99), (28, 7, 45, 3, 46),
     (24, 15, 19, 2, 20), (30, 3, 15, 13, 16)),   # 16
    ((28, 1, 107, 5, 108), (28, 10, 46, 1, 47),
     (28, 1, 22, 15, 23), (28, 2, 14, 17, 15)),   # 17
    ((30, 5, 120, 1, 121), (26, 9, 43, 4, 44),
     (28, 17, 22, 1, 23), (28, 2, 14, 19, 15)),   # 18
    ((28, 3, 113, 4, 114), (26, 3, 44, 11, 45),
     (26, 17, 21, 4, 22), (26, 9, 13, 16, 14)),   # 19
    ((28, 3, 107, 5, 108), (26, 3, 41, 13, 42),
     (30, 15, 24, 5, 25), (28, 15, 15, 10, 16)),  # 20
    ((28, 4, 116, 4, 117), (26, 17, 42),
     (28, 17, 22, 6, 23), (30, 19, 16, 6, 17)),   # 21
    ((28, 2, 111, 7, 112), (28, 17, 46),
     (30, 7, 24, 16, 25), (24, 34, 13)),          # 22
    ((30, 4, 121, 5, 122), (28, 4, 47, 14, 48),
     (30, 11, 24, 14, 25), (30, 16, 15, 14, 16)), # 23
    ((30, 6, 117, 4, 118), (28, 6, 45, 14, 46),
     (30, 11, 24, 16, 25), (30, 30, 16, 2, 17)),  # 24
    ((26, 8, 106, 4, 107), (28, 8, 47, 13, 48),
     (30, 7, 24, 22, 25), (30, 22, 15, 13, 16)),  # 25
    ((28, 10, 114, 2, 115), (28, 19, 46, 4, 47),
     (28, 28, 22, 6, 23), (30, 33, 16, 4, 17)),   # 26
    ((30, 8, 122, 4, 123), (28, 22, 45, 3, 46),
     (30, 8, 23, 26, 24), (30, 12, 15, 28, 16)),  # 27
    ((30, 3, 117, 10, 118), (28, 3, 45, 23, 46),
     (30, 4, 24, 31, 25), (30, 11, 15, 31, 16)),  # 28
    ((30, 7, 116, 7, 117), (28, 21, 45, 7, 46),
     (30, 1, 23, 37, 24), (30, 19, 15, 26, 16)),  # 29
    ((30, 5, 115, 10, 116), (28, 19, 47, 10, 48),
     (30, 15, 24, 25, 25), (30, 23, 15, 25, 16)), # 30
    ((30, 13, 115, 3, 116), (28, 2, 46, 29, 47),
     (30, 42, 24, 1, 25), (30, 23, 15, 28, 16)),  # 31
    ((30, 17, 115), (28, 10, 46, 23, 47),
     (30, 10, 24, 35, 25), (30, 19, 15, 35, 16)), # 32
    ((30, 17, 115, 1, 116), (28, 14, 46, 21, 47),
     (30, 29, 24, 19, 25), (30, 11, 15, 46, 16)), # 33
    ((30, 13, 115, 6, 116), (28, 14, 46, 23, 47),
     (30, 44, 24, 7, 25), (30, 59, 16, 1, 17)),   # 34
    ((30, 12, 121, 7, 122), (28, 12, 47, 26, 48),
     (30, 39, 24, 14, 25), (30, 22, 15, 41, 16)), # 35
    ((30, 6, 121, 14, 122), (28, 6, 47, 34, 48),
     (30, 46, 24, 10, 25), (30, 2, 15, 64, 16)),  # 36
    ((30, 17, 122, 4, 123), (28, 29, 46, 14, 47),
     (30, 49, 24, 10, 25), (30, 24, 15, 46, 16)), # 37
    ((30, 4, 122, 18, 123), (28, 13, 46, 32, 47),
     (30, 48, 24, 14, 25), (30, 42, 15, 32, 16)), # 38
    ((30, 20, 117, 4, 118), (28, 40, 47, 7, 48),
     (30, 43, 24, 22, 25), (30, 10, 15, 67, 16)), # 39
    ((30, 19, 118, 6, 119), (28, 18, 47, 31, 48),
     (30, 34, 24, 34, 25), (30, 20, 15, 61, 16))  # 40
)

mask_functions = [
    lambda row, col: (row ^ col) & 1,
    lambda row, col: row & 1,
    lambda row, col: col % 3,
    lambda row, col: (row + col) % 3,
    lambda row, col: (row // 2 ^ col // 3) & 1,
    lambda row, col: (row * col) % 6,
    lambda row, col: ((row * col) % 2 + (row * col) % 3) & 1,
    lambda row, col: ((row + col) & 1 + (row * col) % 3) & 1
]

MARGIN_WIDTH = 4
DATA_BLACK = 1
DATA_WHITE = 0
FORMAT_BLACK = -1
FORMAT_WHITE = -2

alphanumeric_special = " $%*+-./:"
alphanumeric_symbols = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"

encodings = {
    "numeric": 0b0001,
    "alphanumeric": 0b0010,
    "byte": 0b0100,
    "kanji": 0b1000,
    "ECI": 0b0111
}

ec_level_code = {
    "L": 0b01,
    "M": 0b00,
    "Q": 0b11,
    "H": 0b10
}

ec_level_index = {
    "L": 0,
    "M": 1,
    "Q": 2,
    "H": 3
}


def select_encoding(s):
    if s.isnumeric():
        return "numeric"
    if all(x in alphanumeric_symbols for x in s):
        return "alphanumeric"
    try:
        s.encode("iso 8859-1")
    except UnicodeEncodeError:
        # Maybe test for unicode? 
        pass
    else:
        return "byte"
    # TODO: implement kanji detection and encoding


def encode_alnum_char(c):
    o = ord(c)
    if o >= 48 and o <= 57:
        return o - 48
    if o >= 65 and o <= 90:
        return o - 55
    try:
        return 36 + alphanumeric_special.index(c)
    except ValueError:
        raise ValueError("Symbol is not in QRCode alphanumeric alphabet")


def encoding_length(encoding, data_length):
    if encoding == "numeric":
        remainder = data_length % 3
        data_bitlength = 10 * (data_length // 3)
        if remainder == 1:
            data_bitlength += 4
        elif remainder == 2:
            data_bitlength += 7
    elif encoding == "alphanumeric":
        remainder = data_length % 2
        data_bitlength = 11 * (data_length // 2)
        if remainder == 1:
            data_bitlength += 6
    elif encoding == "byte":
        data_bitlength = 8 * data_length
    elif encoding == "kanji":
        data_bitlength = 13 * data_length
    else:
        raise ValueError("Unknown encoding: " + repr(encoding))
    return data_bitlength


def encode(data, ec_level):
    encoding = select_encoding(data)
    length = len(data)
    bits = BitArray()
    bits.extend(encodings[encoding], 4)
    enc_length = encoding_length(encoding, length)
    version, capacity, length_len = version_info(enc_length, ec_level, encoding)
    bits.extend(length, length_len)
    if encoding == "numeric":
        for i in range(0, length - 2, 3):
            group = int(data[i:i + 3])
            bits.extend(group, 10)
        remainder = length % 3
        if remainder == 1:
            bits.extend(int(data[-1:]), 4)
        elif remainder == 2:
            bits.extend(int(data[-2:]), 7)
    elif encoding == "alphanumeric":
        even = length & 1 == 0
        ln = length if even else length - 1
        for i in range(0, ln, 2):
            encoded = 45 * encode_alnum_char(data[i])
            encoded += encode_alnum_char(data[i + 1])
            bits.extend(encoded, 11)
        if not even:
            encoded = encode_alnum_char(data[length - 1])
            bits.extend(encoded, 6)
    elif encoding == "byte":
        if isinstance(data, str):
            data = data.encode("iso 8859-1")
        for char in data:
            bits.extend(char, 8)
    elif encoding == "kanji":
        raise ValueError("Kanji not supported yet")
    else:
        raise ValueError("Unknown encoding {!r}".format(encoding))
    zeroes = min((4, capacity - enc_length))
    bits.extend(0, zeroes)
    encoded = bits.to_bytes()
    expected_length = capacities[version - 1][ec_level_index[ec_level]] // 8
    pad_bytes = expected_length - len(encoded)
    if pad_bytes > 0:
        encoded += bytes(17 if i & 1 else 236 for i in range(pad_bytes))
    return (encoded, encoding, version)


def version_info(bit_length, ec_level, encoding):
    ec_index = ec_level_index[ec_level]
    length_bitlen_v10 = {
        "numeric": 10,
        "alphanumeric": 9,
        "byte": 8,
        "kanji": 8
    }
    length_bitlen_v27 = {
        "numeric": 12,
        "alphanumeric": 11,
        "byte": 16,
        "kanji": 10
    }
    length_bitlen_v40 = {
        "numeric": 14,
        "alphanumeric": 13,
        "byte": 16,
        "kanji": 12
    }
    max_capacity = capacities[-1][ec_index] - length_bitlen_v40[encoding]
    if max_capacity < bit_length:
        raise ValueError("Data too long to be encoded to QR code")
    version = 1
    version_selected = False
    while not version_selected:
        version_capacity = capacities[version - 1][ec_index]
        if version < 10:
            length_bitlen = length_bitlen_v10[encoding]
        elif version < 27:
            length_bitlen = length_bitlen_v27[encoding]
        else:
            length_bitlen = length_bitlen_v40[encoding]
        true_capacity = version_capacity - length_bitlen - 4
        if true_capacity >= bit_length:
            version_selected = True
        else:
            version += 1
    capacity = capacities[version - 1][ec_index]
    return (version, capacity, length_bitlen)


def correction_encode(encoded_data, version, ec_level):
    ec_index = ec_level_index[ec_level]
    format_ = blocks[version - 1][ec_index]
    groups = (len(format_) - 1) // 2
    #encoded_len = len(encoded_data)
    #expected_len = sum(format_[2*g+1] * format_[2*g+2] for g in range(groups))
    ec_blocks = []
    data_blocks = []
    group_start_index = 0
    ec_len = format_[0]
    for group in range(groups):
        ec_blocks.append([])
        data_blocks.append([])
        block_count = format_[2 * group + 1]
        block_len = format_[2 * group + 2]
        rse = ReedSolomonEncoder(block_len, block_len + ec_len)
        for block_index in range(block_count):
            i = group_start_index + block_index * block_len
            i2 = group_start_index + (block_index + 1) * block_len
            enc_block = encoded_data[i:i2]
            ec_block = rse.encode_block(enc_block)
            ec_blocks[group].append(ec_block)
            data_blocks[group].append(enc_block)
        group_start_index += block_count * block_len
    return (data_blocks, ec_blocks)


def groups_iterator(groups):
    blocks = (block for group in groups for block in group)
    for vals in zip_longest(*blocks):
        for val in vals:
            if val != None:
                yield val


def interleave_blocks(groups):
    interleaved = bytes(groups_iterator(groups))
    return interleaved


def qr_bits(data, ec_level):
    encoded_data, encoding, version = encode(data, ec_level)
    data_groups, ec_groups = correction_encode(encoded_data, version, ec_level)
    ec_data = interleave_blocks(data_groups) + interleave_blocks(ec_groups)
    ec_bits = BitArray(ec_data)
    return (ec_bits, version)


def format_string(ec_level, mask):
    ec_code = ec_level_code[ec_level]
    format_bits = (ec_code << 13) | (mask << 10)
    format_ec_bits = modulo_gf2(format_bits, 0b10100110111)
    format_s = format_bits | format_ec_bits
    format_s ^= 0b101010000010010
    return format_s


def version_string(version):
    version_bits = version << 12
    version_ec_bits = modulo_gf2(version_bits, 0b1111100100101)
    version_s = version_bits | version_ec_bits
    return version_s


class QRCode:
    dimensionality = "2D"

    def __init__(self, data, ec_level=None):
        if ec_level == None:
            ec_level = "Q"
        self.ec_level = ec_level
        self.bits, self.version = qr_bits(data, ec_level)
        self.width = 17 + 4 * self.version
        self.matrix = [
            [DATA_WHITE for i in range(self.width)]
            for j in range(self.width)
        ]
        self.mark_finder_patterns()
        self.mark_timing_pattern()
        self.mark_alignment_patterns()
        self.mark_dark_module()
        self.reserve_format_information_area()
        self.reserve_version_information_area()
        self.mark_bits()
        self.mask_index = self.optimal_mask()
        self.mark_format_string()
        self.mark_version_information()

    def mark_rectangle(self, x, y, width, height, color_code):
        x2 = x + width
        y2 = y + height
        for i in range(y, y2):
            for j in range(x, x2):
                self.matrix[i][j] = color_code

    def mark_finder_pattern(self, xindex, yindex):
        self.mark_rectangle(xindex, yindex, 7, 1, FORMAT_BLACK)
        self.mark_rectangle(xindex, yindex, 1, 7, FORMAT_BLACK)
        self.mark_rectangle(xindex + 6, yindex, 1, 7, FORMAT_BLACK)
        self.mark_rectangle(xindex, yindex + 6, 7, 1, FORMAT_BLACK)
        self.mark_rectangle(xindex + 2, yindex + 2, 3, 3, FORMAT_BLACK)
        xindex2 = xindex + 1
        yindex2 = yindex + 1
        self.mark_rectangle(xindex2, yindex2, 5, 1, FORMAT_WHITE)
        self.mark_rectangle(xindex2, yindex2, 1, 5, FORMAT_WHITE)
        self.mark_rectangle(xindex2 + 4, yindex2, 1, 5, FORMAT_WHITE)
        self.mark_rectangle(xindex2, yindex2 + 4, 5, 1, FORMAT_WHITE)

    def mark_finder_patterns(self):
        self.mark_finder_pattern(0, 0)
        self.mark_finder_pattern(0, self.width - 7)
        self.mark_finder_pattern(self.width - 7, 0)
        self.mark_rectangle(7, 0, 1, 8, FORMAT_WHITE)
        self.mark_rectangle(0, 7, 8, 1, FORMAT_WHITE)
        self.mark_rectangle(self.width - 8, 7, 8, 1, FORMAT_WHITE)
        self.mark_rectangle(self.width - 8, 0, 1, 8, FORMAT_WHITE)
        self.mark_rectangle(0, self.width - 8, 8, 1, FORMAT_WHITE)
        self.mark_rectangle(7, self.width - 8, 1, 8, FORMAT_WHITE)

    def mark_timing_pattern(self):
        for i in range(8, self.width - 8):
            if i & 1:
                color_code = FORMAT_WHITE
            else:
                color_code = FORMAT_BLACK
            self.matrix[i][6] = color_code
            self.matrix[6][i] = color_code

    def mark_alignment_pattern(self, xindex, yindex):
        xindex -= 2
        yindex -= 2
        for i in range(4):
            self.matrix[yindex][xindex + i + 1] = FORMAT_BLACK
            self.matrix[yindex + i + 1][xindex + 4] = FORMAT_BLACK
            self.matrix[yindex + 4][xindex + i] = FORMAT_BLACK
            self.matrix[yindex + i][xindex] = FORMAT_BLACK
        for i in range(2):
            self.matrix[yindex + 1][xindex + i + 2] = FORMAT_WHITE
            self.matrix[yindex + i + 2][xindex + 3] = FORMAT_WHITE
            self.matrix[yindex + 3][xindex + i + 1] = FORMAT_WHITE
            self.matrix[yindex + i + 1][xindex + 1] = FORMAT_WHITE
        self.matrix[yindex + 2][xindex + 2] = FORMAT_BLACK

    def mark_alignment_patterns(self):
        if self.version == 1:
            return
        positions = alignments[self.version - 2][1:]
        for y in positions:
            for x in positions:
                self.mark_alignment_pattern(x, y)
        for i in positions[:-1]:
            self.mark_alignment_pattern(6, i)
            self.mark_alignment_pattern(i, 6)

    def mark_dark_module(self):
        self.matrix[-8][8] = FORMAT_BLACK

    def reserve_format_information_area(self):
        self.mark_rectangle(8, 0, 1, 6, FORMAT_WHITE)
        self.mark_rectangle(0, 8, 6, 1, FORMAT_WHITE)
        self.mark_rectangle(7, 7, 2, 2, FORMAT_WHITE)
        self.mark_rectangle(-8, 8, 8, 1, FORMAT_WHITE)
        self.mark_rectangle(8, -7, 1, 7, FORMAT_WHITE)

    def reserve_version_information_area(self):
        if self.version >= 7:
            self.mark_rectangle(0, -11, 6, 3, FORMAT_WHITE)
            self.mark_rectangle(-11, 0, 3, 6, FORMAT_WHITE)

    def data_position_generator(self):
        i = self.width - 1
        while i > 2:
            x1 = i
            x2 = i - 1
            for y in range(self.width - 1, -1, -1):
                x = x1
                if self.matrix[y][x] != FORMAT_BLACK and \
                   self.matrix[y][x] != FORMAT_WHITE:
                    yield (x, y)
                x = x2
                if self.matrix[y][x] != FORMAT_BLACK and \
                   self.matrix[y][x] != FORMAT_WHITE:
                    yield (x, y)
            if i == 8:
                i = 7
            x1 = i - 2
            x2 = i - 3
            for y in range(self.width):
                x = x1
                if self.matrix[y][x] != FORMAT_BLACK and \
                   self.matrix[y][x] != FORMAT_WHITE:
                    yield (x, y)
                x = x2
                if self.matrix[y][x] != FORMAT_BLACK and \
                   self.matrix[y][x] != FORMAT_WHITE:
                    yield (x, y)
            i -= 4

    def mark_bits(self):
        for xy, bit in zip(self.data_position_generator(), self.bits):
            x, y = xy
            if bit:
                self.matrix[y][x] = DATA_BLACK
            else:
                self.matrix[y][x] = DATA_WHITE

    def mark_format_string(self):
        format_s = format_string(self.ec_level, self.mask_index)
        for i in range(6):
            bit = (format_s >> i) & 1
            if bit:
                self.matrix[i][8] = FORMAT_BLACK
                self.matrix[8][-i - 1] = FORMAT_BLACK
        if (format_s >> 6) & 1:
            self.matrix[7][8] = FORMAT_BLACK
            self.matrix[8][-7] = FORMAT_BLACK
        if (format_s >> 7) & 1:
            self.matrix[8][8] = FORMAT_BLACK
            self.matrix[8][-8] = FORMAT_BLACK
        if (format_s >> 8) & 1:
            self.matrix[8][7] = FORMAT_BLACK
            self.matrix[-7][8] = FORMAT_BLACK
        for i in range(6):
            bit = (format_s >> (i + 9)) & 1
            if bit:
                self.matrix[8][5 - i] = FORMAT_BLACK
                self.matrix[i - 6][8] = FORMAT_BLACK

    def mark_version_information(self):
        if self.version >= 7:
            base_x = 0
            base_y = self.width - 11
            version_s = version_string(self.version)
            bit_index = 0
            for x in range(base_x, base_x + 6):
                for y in range(base_y, base_y + 3):
                    bit = (version_s >> bit_index) & 1
                    self.matrix[y][x] = bit
                    bit_index += 1
            base_x = self.width - 11
            base_y = 0
            bit_index = 0
            for y in range(base_y, base_y + 6):
                for x in range(base_x, base_x + 3):
                    bit = (version_s >> bit_index) & 1
                    self.matrix[y][x] = bit
                    bit_index += 1

    def mask(self, matrix, index):
        fn = mask_functions[index]
        for x, y in self.data_position_generator():
            if fn(y, x) == 0:
                if matrix[y][x] == DATA_WHITE:
                    matrix[y][x] = DATA_BLACK
                else:
                    matrix[y][x] = DATA_WHITE

    def optimal_mask(self):
        best_matrix = None
        best_penalty_score = 10 ** 9 # arbitrary big number
        best_mask_index = None
        for mask_index in range(8):
            matrix_copy = [list(row) for row in self.matrix]
            self.mask(matrix_copy, mask_index)
            penalty_score = self.penalty(matrix_copy)
            if penalty_score < best_penalty_score:
                best_penalty_score = penalty_score
                best_matrix = matrix_copy
                best_mask_index = mask_index
        self.matrix = best_matrix
        return best_mask_index

    def penalty(self, matrix):
        penalty_score = 0
        # condition one:
        dark = 1
        light = 0
        col = lambda x: dark if x == DATA_BLACK or x == FORMAT_BLACK else light
        colors = [[col(matrix[x][y]) for x in range(self.width)]
                   for y in range(self.width)]
        for row in colors:
            last = None
            consecutive = 0
            for color in row:
                if color == last:
                    consecutive += 1
                else:
                    if consecutive > 4:
                        penalty_score += consecutive - 2
                    consecutive = 0
                last = color
        for x in range(self.width):
            last = None
            consecutive = 0
            for y in range(self.width):
                color = colors[y][x]
                if color == last:
                    consecutive += 1
                else:
                    if consecutive > 4:
                        penalty_score += consecutive - 2
                    consecutive = 0
                last = col
        # condition two:
        for y in range(self.width - 1):
            for x in range(self.width - 1):
                if colors[y][x] == colors[y][x + 1] == \
                   colors[y + 1][x] == colors[y + 1][x + 1]:
                    penalty_score += 3
        # condition three:
        pattern = [dark, light, dark, dark, dark, light, dark]
        four_white = lambda row, i: all(map(lambda x: x == light, row[i - 4:i]))
        matches_pattern = lambda row, i: all(map(lambda z: z[0] == z[1],
                                                 zip(row[i:], pattern)))
        for row in colors:
            for i in range(4, self.width - 7):
                match = matches_pattern(row, i)
                if match:
                    if four_white(row, i):
                        penalty_score += 40
                    elif i + 11 < self.width and four_white(row, i + 7):
                        penalty_score += 40
        # condition four:
        total = self.width ** 2
        dark_modules = 0
        for row in colors:
            dark_modules += sum(map(lambda x: x == dark, row))
        percentage = dark_modules // total
        lower_limit = int(20 * percentage) - 10
        upper_limit = lower_limit + 1
        penalty_score += 10 * max(lower_limit, upper_limit)
        return penalty_score

    def _image_bits(self):
        # TODO: simplify
        return [
            list(
                chain(
                    (DATA_WHITE for _ in range(MARGIN_WIDTH)),
                    (int(bit == DATA_BLACK or bit == FORMAT_BLACK) for bit in line),
                    (DATA_WHITE for _ in range(MARGIN_WIDTH))
                )
            )
            for line in chain(
                (
                    (DATA_WHITE for _ in range(len(self.matrix)))
                    for _ in range(MARGIN_WIDTH)
                ),
                self.matrix,
                (
                    (DATA_WHITE for _ in range(len(self.matrix)))
                    for _ in range(MARGIN_WIDTH)
                )
            )
        ]

    @classmethod
    def image_bits(self, data, ec_level=None):
        qr = QRCode(data, ec_level)
        return qr._image_bits()


def _unit_test():
    enc = encode("HELLO WORLD", "Q")
    expected1 = (0b00100000010110110000101101111000110100010111001011011100010011010100001101000000111011000001000111101100).to_bytes(length=13, byteorder="big")
    computed1 = enc[0]
    test1 = computed1 == expected1
    print("test1 passed:", test1)
    if not test1:
        print("enc[0]:", enc[0])
        print("expected1:", expected1)
    group1 = [
        [67,85,70,134,87,38,85,194,119,50,6,18,6,103,38],
        [246,246,66,7,118,134,242,7,38,86,22,198,199,146,6]
    ]
    group2 = [
        [182,230,247,119,50,7,118,134,87,38,82,6,134,151,50,7],
        [70,247,118,86,194,6,151,50,16,236,17,236,17,236,17,236]
    ]
    groups = [group1, group2]
    ec_group1 = [
        [213,199,11,45,115,247,241,223,229,248,154,117,154,111,86,161,111,39],
        [87,204,96,60,202,182,124,157,200,134,27,129,209,17,163,163,120,133]
    ]
    ec_group2 = [
        [148,116,177,212,76,133,75,242,238,76,195,230,189,10,108,240,192,141],
        [235,159,5,173,24,147,59,33,106,40,255,172,82,2,131,32,178,236]
    ]
    ec_groups = [ec_group1, ec_group2]
    expected2 = [
        67, 246, 182, 70, 85, 246, 230, 247, 70, 66, 247, 118,
        134, 7, 119, 86, 87, 118, 50, 194, 38, 134, 7, 6, 85,
        242, 118, 151, 194, 7, 134, 50, 119, 38, 87, 16, 50,
        86, 38, 236, 6, 22, 82, 17, 18, 198, 6, 236, 6, 199,
        134, 17, 103, 146, 151, 236, 38, 6, 50, 17, 7, 236
    ]
    expected2 = bytes(expected2)
    computed2 = interleave_blocks(groups)
    test2 = computed2 == expected2
    print("test2 passed:", test2)
    if not test2:
        print("expected:", expected2)
    final = [67, 246, 182, 70, 85, 246, 230, 247, 70, 66, 247, 118, 134, 7,
             119, 86, 87, 118, 50, 194, 38, 134, 7, 6, 85, 242, 118, 151,
             194, 7, 134, 50, 119, 38, 87, 16, 50, 86, 38, 236, 6, 22, 82,
             17, 18, 198, 6, 236, 6, 199, 134, 17, 103, 146, 151, 236, 38,
             6, 50, 17, 7, 236, 213, 87, 148, 235, 199, 204, 116, 159, 11,
             96, 177, 5, 45, 60, 212, 173, 115, 202, 76, 24, 247, 182, 133,
             147, 241, 124, 75, 59, 223, 157, 242, 33, 229, 200, 238, 106,
             248, 134, 76, 40, 154, 27, 195, 255, 117, 129, 230, 172, 154,
             209, 189, 82, 111, 17, 10, 2, 86, 163, 108, 131, 161, 163, 240,
             32, 111, 120, 192, 178, 39, 133, 141, 236]
    expected3 = interleave_blocks(ec_groups)
    enc = bytes(group1[0] + group1[1] + group2[0] + group2[1])
    corr = correction_encode(enc, 5, "Q")
    computed3 = interleave_blocks(corr[1])
    test3 = computed3 == expected3
    print("test3 passed:", test3)
    if not test3:
        print("expected:", expected3)
        print("len(expected):", len(expected3))
        print("computed:", computed3)
        print("len(computed):", len(computed3))


if __name__ == "__main__":
    _unit_test()
