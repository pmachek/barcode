from itertools import chain

from .encoding import BarcodeEncoding


class Ean(BarcodeEncoding):
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

    code_bitlength = 7
    #bits = partial(bits, length=code_length)

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

        yield from cls.bits(0, cls.quiet_zone_left_ean13)
        # barcode start
        yield from cls.bits(0b101, 3)

        for i, number in zip(range(11), (int(char) for char in it)):
            if i < 6:
                lgr_index = (lg_pattern >> (5 - i)) & 1
            else:
                lgr_index = 2
            yield from cls.bits(
                cls.patterns[number][lgr_index],
                cls.code_bitlength
            )
            if i == 5:
                # middle separator, between first 6 and last 6 digits
                yield from cls.bits(0b01010, 5)

        yield from cls.bits(cls.patterns[check_digit][2], cls.code_bitlength)
        yield from cls.bits(0b101, 3)
        yield from cls.bits(0, cls.quiet_zone_right_ean13)
    
    @classmethod
    def ean8_bars(cls, number_sequence):
        if isinstance(number_sequence, str):
            number_sequence = [ord(c) - ord('0') for c in number_sequence]
        check_digit = cls.check_digit(number_sequence)
        
        yield from cls.bits(0, cls.quiet_zone_left_ean8)
        yield from cls.bits(0b101, 3)
        
        for i, number in zip(range(7), number_sequence):
            lgr_index = 0 if i < 4 else 2
            yield from cls.bits(
                cls.patterns[number][lgr_index],
                cls.code_bitlength
            )
            if i == 3:
                yield from cls.bits(0b01010, 5)

        yield from cls.bits(cls.patterns[check_digit][2], cls.code_bitlength)
        yield from cls.bits(0b101, 3)
        yield from cls.bits(0, cls.quiet_zone_left_ean8)
    
    @classmethod
    def label_text_areas(cls, number_sequence):
        number_sequence = cls.with_check_digit(number_sequence)
        if len(number_sequence) == 8:
            return cls.label_text_areas_ean8(number_sequence)
        if len(number_sequence) == 13:
            return cls.label_text_areas_ean13(number_sequence)
        raise ValueError("Number sequence must be 7, 8, 12 or 13 characters long")

    @classmethod
    def label_mask_ean13(cls):
        for _ in range(6):
            yield chain(
                (0 for _ in range(cls.quiet_zone_left_ean13)),
                (1, 0, 1),
                (0 for _ in range(cls.code_bitlength * 6)),
                (0, 1, 0, 1, 0),
                (0 for _ in range(cls.code_bitlength * 6)),
                (1, 0, 1)
            )
    
    @classmethod
    def label_mask_ean8(cls):
        for _ in range(6):
            yield chain(
                (0 for _ in range(cls.quiet_zone_left_ean8)),
                (1, 0, 1),
                (0 for _ in range(cls.code_bitlength * 4)),
                (0, 1, 0, 1, 0),
                (0 for _ in range(cls.code_bitlength * 4)),
                (1, 0, 1)
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
                "text": number_sequence[:4],
                "x_start": cls.quiet_zone_left_ean8 + 3,
                "y_start": 3,
                "x_end": cls.quiet_zone_left_ean8 + 32,
                "y_end": None
            },
            {
                "text": number_sequence[4:],
                "x_start": cls.quiet_zone_left_ean8 + 36,
                "y_start": 3,
                "x_end": cls.quiet_zone_left_ean8 + 64,
                "y_end": None
            }
        ]

    @classmethod
    def label_mask(cls, number_sequence):
        number_sequence = cls.with_check_digit(number_sequence)
        if len(number_sequence) == 8:
            yield from cls.label_mask_ean8()
        else:
            yield from cls.label_mask_ean13()
