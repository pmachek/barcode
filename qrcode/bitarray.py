def BitArray(b=None, endian="big"):
    if endian == "big":
        return BigEndianBitArray(b)
    elif endian == "little":
        return LittleEndianBitArray(b)


class BigEndianBitArray:
    def __init__(self, b=None):
        self.byte_array = bytearray(b) if b is not None else bytearray()
        self.buffer = 0
        self.buffer_len = 0

    def __bool__(self):
        return self.buffer or any(self.byte_array)

    def __len__(self):
        return 8 * len(self.byte_array) + self.buffer_len

    def __str__(self):
        i = 0
        i = i.from_bytes(self.byte_array, "big")
        if self.buffer_len > 0:
            i = (i << self.buffer_len) | self.buffer
        bits = bin(i)[2:]
        leading_zeroes = len(self) - len(bits)
        if leading_zeroes > 0:
            bits = leading_zeroes * "0" + bits
        return "BitArray({})".format(bits)

    def __getitem__(self, item):
        if isinstance(item, slice):
            if item.step != None and item.step != 0:
                raise ValueError("Non-zero slice step not supported")
            start_byte, start_bit = self._index(item.start)
            end_byte, end_bit = self._index(item.stop)
            start = self.byte_array[start_byte] >> start_bit
            end = self.byte_array[end_byte] & (0xFF >> (8 - start_bit))
            middle = start.from_bytes(self.byte_array[start_byte:end_byte],
                                      "big")
            end_shift = 8 * (end_byte - start_byte) + start_bit
            whole = start | (middle << start_bit) | (end << end_shift)
            return whole
        elif isinstance(item, int):
            byte_index, bit_index = self._index(item)
            if byte_index == len(self.byte_array):
                bit_index = 7 - bit_index
                return (self.buffer >> bit_index) & 1
            b = self.byte_array[byte_index]
            bit = (b >> bit_index) & 1
            return bit
        else:
            raise TypeError("Unsupported type of index")

    def __setitem__(self, index, bit):
        byte_index, bit_index = self._index(index)
        if byte_index == len(self.byte_array):
            bit_index = 7 - bit_index
            bit ^= (self.buffer >> bit_index) & 1
            self.buffer ^= bit << bit_index
            return
        b = self.byte_array[byte_index]
        b ^= bit << bit_index
        self.byte_array[byte_index] = b

    def __iter__(self):
        for byte in self.byte_array:
            for shift in range(7, -1, -1):
                yield (byte >> shift) & 1
        for shift in range(self.buffer_len - 1, -1, -1):
            yield (self.buffer >> shift) & 1

    def _index(self, index):
        l = len(self)
        if index < 0:
            index += l
        if index >= len(self) or index < 0:
            raise IndexError("BitArray index out of range")
        byte_index = index // 8
        bit_index = 7 - index % 8
        return (byte_index, bit_index)

    def extend(self, number, encode_len=None):
        if encode_len == None:
            encode_len = encode_len.bit_length()
        number |= self.buffer << encode_len
        encode_len += self.buffer_len
        self.buffer_len = encode_len % 8
        self.buffer = number & (0xff >> (8 - self.buffer_len))
        number >>= self.buffer_len
        encode_len -= self.buffer_len
        encode_bytes = encode_len // 8
        if encode_bytes > 0:
            self.byte_array.extend(number.to_bytes(encode_bytes, "big"))
        
    def to_bytes(self):
        if self.buffer_len > 0:
            b = self.buffer << (8 - self.buffer_len)
            return bytes(self.byte_array) + bytes((b,))
        else:
            return bytes(self.byte_array)

    def to_int(self):
        a = 0
        n = a.from_bytes(self.byte_array, "big")
        n <<= self.buffer_len
        n |= self.buffer
        return n


class LittleEndianBitArray:
    def __init__(self, b=None):
        self.byte_array = bytearray(b) if b != None else bytearray()
        self.last_byte_len = 0

    def __bool__(self):
        return any(self.byte_array)

    def __len__(self):
        length = 8 * (len(self.byte_array) - 1)
        length += self.last_byte_len if self.last_byte_len > 0 else 8
        return length

    def __str__(self):
        i = 0
        i = i.from_bytes(self.byte_array, "little")
        bits = bin(i)[2:]
        leading_zeroes = 8 - len(bits) % 8
        if leading_zeroes != 8:
            bits = leading_zeroes * "0" + bits
        trailing_zeroes = len(self) - len(bits)
        if trailing_zeroes > 0:
            whole_bytes = trailing_zeroes // 8
            if whole_bytes > 0:
                bits += 8 * whole_bytes * "0"
            space_len = 8 - trailing_zeroes % 8
            if space_len != 8:
                bits += "#" * space_len + (trailing_zeroes % 8) * "0"
        return "BitArray({})".format(bits)

    def __getitem__(self, item):
        if isinstance(item, slice):
            if item.step != None and item.step != 0:
                raise NotImplementedError("Non-zero slice step not supported")
            start = max((0, item.start))
            stop = min((len(self), item.stop))
            start_byte, start_bit = self._index(start)
            end_byte, end_bit = self._index(stop, check_bounds=False)
            number_bytes = self.byte_array[start_byte:end_byte + 1]
            number_bytes[-1] &= 0xFF >> (8 - end_bit)
            n = end_bit.from_bytes(number_bytes, "little")
            n >>= start_bit
            return n
        elif isinstance(item, int):
            byte_index, bit_index = self._index(item)
            b = self.byte_array[byte_index]
            bit = (b >> bit_index) & 1
            return bit
        else:
            raise TypeError("Unsupported type of index")

    def __setitem__(self, index, bit):
        byte_index, bit_index = self._index(index)
        bit ^= (self.byte_array[byte_index] >> bit_index) & 1
        self.byte_array[byte_index] ^= bit << bit_index

    def __iter__(self):
        for i in range(len(self.byte_array) - 1):
            byte = self.byte_array[i]
            for shift in range(8):
                yield (byte >> shift) & 1
        last_byte = self.byte_array[-1]
        for i in range(self.last_byte_len):
            yield (last_byte >> shift) & 1

    def _index(self, index, check_bounds=True):
        l = len(self)
        if index < 0:
            index += l
        if check_bounds and (index >= len(self) or index < 0):
            raise IndexError("BitArray index out of range")
        byte_index = index // 8
        bit_index = index % 8
        return (byte_index, bit_index)

    def extend(self, number, encode_len=None):
        if encode_len == None:
            encode_len = number.bit_length()
        if len(self.byte_array) > 0 and self.last_byte_len > 0:
            number = (number << self.last_byte_len) | self.byte_array[-1]
            encode_len += self.last_byte_len
            encode_bytes = (encode_len - 1) // 8 + 1
            b = number.to_bytes(encode_bytes, "little")
            self.byte_array[-1] = b[0]
            self.byte_array.extend(b[1:])
            self.last_byte_len = encode_len % 8
        else:
            byte_length = (encode_len - 1) // 8 + 1
            self.last_byte_len = encode_len % 8
            self.byte_array.extend(number.to_bytes(byte_length, "little"))
    
    def to_bytes(self):
        return bytes(self.byte_array)

    def to_int(self):
        a = 0
        n = a.from_bytes(self.byte_array, "little")
        return n


class BitArray2:
    def __init__(self):
        self.length = 0
        self.n = 0

    def __len__(self):
        return self.length

    def __getitem__(self, index):
        return (self.n >> self.length - index - 1) & 1

    def __setitem__(self, index, bit):
        bit ^= self[index]
        self.n ^= bit << self.length - index - 1

    def extend(self, number, bit_len):
        n_len = number.bit_length()
        if n_len > bit_len:
            raise ValueError("Bit length greater then indicated")
        self.length += bit_len
        self.n <<= bit_len
        self.n |= number

    def to_bytes(self):
        shift = 8 - self.length % 8
        if shift == 8:
            shift = 0
        n = self.n << shift
        length = (self.length - 1) // 8 + 1
        return n.to_bytes(length, "big")


def test(b):
    b.extend(10, 11)
    b.extend(297, 9)
    print("length:", len(b))
    print("bit sequence:", end=" ")
    for bit in b:
        print(bit, end="")
    print()
    print("BitArray:", b)
    print("As int:", bin(b.to_int()))
    for start, end in ((2, 10), (9, 18)):
        print("slice from", start, "to", end, b[start:end])


if __name__ == "__main__":
    for endian in ("little",):
        test(BitArray(endian=endian))
