from os import SEEK_CUR

from .image import BarcodeImage


def compress_gif(data, color_bits=8):
    assert color_bits >= 2, "Gif can't encode 1 bit per pixel"
    length = len(data)
    symbol_length = color_bits + 1
    reset_table = 2 ** color_bits
    end_of_data = reset_table + 1
    init_size = 2 ** color_bits + 2
    table = {}
    output = bytearray()
    bit_buffer = reset_table
    bit_buffer_len = symbol_length
    index = 0
    length = len(data)
    def out(symbol, symbol_length):
        nonlocal bit_buffer, bit_buffer_len
        bit_buffer |= symbol << bit_buffer_len
        bit_buffer_len += symbol_length
        while bit_buffer_len >= 8:
            output.append(bit_buffer & 0xff)
            bit_buffer >>= 8
            bit_buffer_len -= 8
    while index < length:
        sequence_len = 2
        sequence = data[index:index + sequence_len]
        while sequence in table.keys() and index + sequence_len <= length:
            symbol = table[sequence]
            sequence_len += 1
            sequence = data[index:index + sequence_len]
        if sequence_len == 2:
            symbol = data[index]
        out(symbol, symbol_length)
        table[sequence] = len(table) + init_size
        index += sequence_len - 1
        symbol_length = (init_size - 1 + len(table)).bit_length()
        if len(table) == 4095 - init_size:
            # resetting dictionary
            out(reset_table, 12)
            table = {}
            symbol_length = color_bits + 1
    out(end_of_data, symbol_length)
    if bit_buffer_len > 0:
        output.append(bit_buffer)
    return bytes(output)


def decompress_gif(data, color_bits=8):
    assert color_bits >= 2, "Gif can't encode 1 bit per pixel"
    table = [bytes((i,)) for i in range(2 ** color_bits)]
    table.append(None)
    table.append(None)
    reset_table = 2 ** color_bits
    end_of_data = reset_table + 1
    symbol_length = color_bits + 1
    length = len(data)
    bit_buffer = 0
    bit_buffer_len = 0
    index = 0
    def load(bit_length):
        nonlocal bit_buffer, bit_buffer_len, index
        while bit_buffer_len < bit_length and index < length:
            bit_buffer |= data[index] << bit_buffer_len
            bit_buffer_len += 8
            index += 1
        ret = bit_buffer & (2 ** bit_length - 1)
        bit_buffer >>= bit_length
        bit_buffer_len -= bit_length
        return ret
    assert load(symbol_length) == reset_table
    prev_sequence = table[load(symbol_length)]
    if color_bits == 1:
        symbol_length += 1
    output = bytearray()
    while index <= length:
        table_index = load(symbol_length)
        if table_index == reset_table:
            # resetting dictionary...
            output.extend(sequence)
            table = [bytes((i,)) for i in range(2 ** color_bits)]
            table.append((-1,))
            table.append((-1,))
            symbol_length = color_bits + 1
            sequence = table[load(symbol_length)]
        elif table_index == end_of_data:
            output.extend(sequence)
            return bytes(output)
        else:
            if table_index < len(table):
                sequence = table[table_index]
                table_sequence = prev_sequence + sequence[:1]
            else:
                sequence = prev_sequence + prev_sequence[:1]
                table_sequence = sequence
            table.append(table_sequence)
            output.extend(prev_sequence)
        symbol_length = len(table).bit_length()
        prev_sequence = sequence
    return bytes(output)


magic_number1 = b"GIF87a"
magic_number2 = b"GIF89a"


class GifImage:
    def __init__(self, filename, verbose=False):
        self.filename = filename
        self.file = open(filename, "rb")
        self.frames = []
        self.comments = []
        self.verbose = verbose
        self.read_file()

    def read_header(self):
        first_bytes = self.file.read(6)
        if not (first_bytes == magic_number1 or first_bytes == magic_number2):
            raise ValueError("File does not have gif image magic number")

    def read_color_table(self, size=None):
        if size is None:
            size = self.global_color_table_size
        return [tuple(self.file.read(3)) for i in range(2 ** size)]

    def read_gce(self):
        data = self.read_block_data()
        self.has_transparent_color = data[0] & 1
        self.animation_delay = int.from_bytes(data[1:3], "little")
        self.transparent_color_index = data[3]

    def read_anim(self):
        data = self.read_block_data()
        netscape = data[:11]
        if netscape != b"NETSCAPE2.0":
            raise ValueError("Not an animation")
        sub_block_index = data[12]
        self.number_of_repetitions = int.from_bytes(data[12:14], "little")

    def read_descriptor(self):
        self.nw_corner_x = int.from_bytes(self.file.read(2), "little")
        self.nw_corner_y = int.from_bytes(self.file.read(2), "little")
        self.image_width = int.from_bytes(self.file.read(2), "little")
        self.image_height = int.from_bytes(self.file.read(2), "little")
        byte = ord(self.file.read(1))
        local_color_table_present = byte >> 7
        interlace_flag = (byte >> 6) & 1
        sort_flag = (byte >> 5) & 1
        local_color_table_size = byte & 0b111
        b = self.file.read(1)
        if local_color_table_present:
            color_table = self.read_color_table(local_color_table_size)
        else:
            color_table = None
        return color_table

    def read_pixels(self, color_table=None):
        if color_table is None:
            color_table = self.global_color_table
        data = self.read_block_data()
        indexed_pixels = decompress_gif(data, self.color_resolution)
        pixels = []
        if self.frames == [] or not self.has_transparent_color:
            for i in range(self.image_height):
                start = self.image_width * i
                end = self.image_width * (i + 1)
                row = indexed_pixels[start:end]
                pixels.append([color_table[x] for x in row])
        else:
            pixels = [list(row) for row in self.frames[-1]]
            for i in range(self.image_height):
                for j in range(self.image_width):
                    indexed_index = i * self.image_width + j
                    color_index = indexed_pixels[indexed_index]
                    if color_index != self.transparent_color_index:
                        y = i + self.nw_corner_y
                        x = j + self.nw_corner_x
                        pixels[y][x] = color_table[color_index]
        return pixels

    def read_block_data(self):
        data = bytearray()
        part_len = ord(self.file.read(1))
        while part_len != 0:
            data.extend(self.file.read(part_len))
            part_len = ord(self.file.read(1))
        return data

    def read_blocks(self):
        byte1 = self.file.read(1)
        while byte1 != b"" and byte1 != b";":
            if byte1 == b"!":
                byte2 = ord(self.file.read(1))
                if byte2 == 0xff:
                    chunk = self.file.read(12)[1:]
                    if chunk == b"NETSCAPE2.0":
                        self.file.seek(-12, SEEK_CUR)
                        self.read_anim()
                    else:
                        chunk = self.file.read(10)
                        self.file.seek(-10, SEEK_CUR)
                elif byte2 == 0xfe:
                    self.comments.append(self.read_block_data())
                elif byte2 == 0x01:
                    self.read_block_data()
                elif byte2 == 0xf9:
                    self.read_gce()
                else:
                    return
            elif byte1 == b",":
                color_table = self.read_descriptor()
                frame = self.read_pixels(color_table)
                self.frames.append(frame)
            else:
                return
            byte1 = self.file.read(1)
    
    def read_file(self):
        self.read_header()
        self.width = int.from_bytes(self.file.read(2), "little")
        self.height = int.from_bytes(self.file.read(2), "little")
        i = ord(self.file.read(1))
        global_color_table_flag = i >> 7
        self.color_resolution = ((i >> 4) & 0b111) + 1
        sort_flag = (i >> 3) & 1
        self.global_color_table_size = (i & 0b111) + 1
        self.background_color_index = ord(self.file.read(1))
        pixel_aspect_ratio = ord(self.file.read(1))
        if pixel_aspect_ratio != 0:
            self.aspect_ratio = (pixel_aspect_ratio + 15) // 64
        else:
            self.aspect_ratio = 0
        if global_color_table_flag == 1:
            self.global_color_table = self.read_color_table()
        self.read_blocks()
        self.file.close()


class GifBarcodeImage(BarcodeImage):
    @classmethod
    def _write_block_data(cls, image_file, data):
        data_length = len(data)
        prev_index = 0
        index = min(255, data_length)
        while prev_index < data_length:
            image_file.write(
                bytes((index - prev_index,)) + data[prev_index:index]
            )
            prev_index = index
            index = min(index + 255, data_length)
        image_file.write(b"\0")

    def _write_header(self, image_file):
        self.bits_per_pixel = 2  # 1 bit would suffice, but gifs can't do that
        global_color_table_flag = 1
        image_file.write(magic_number2)
        image_file.write(self.image_width.to_bytes(2, "little"))
        image_file.write(self.image_height.to_bytes(2, "little"))
        image_file.write(
            bytes([(global_color_table_flag << 7) | ((self.bits_per_pixel - 1) << 4)])
        )
        # default color index, pixel aspect
        image_file.write(b"\0\0")
        # global color table - white, black
        image_file.write(b"\xff\xff\xff\x00\x00\x00")
        image_file.write(b",")
        image_file.write((0).to_bytes(2, "little"))
        image_file.write((0).to_bytes(2, "little"))
        image_file.write(self.image_width.to_bytes(2, "little"))
        image_file.write(self.image_height.to_bytes(2, "little"))
        image_file.write(b"\0")     # no color table
        image_file.write(bytes([self.bits_per_pixel]))

    def _write_bars(self, image_file):
        linear_label = []
        if self.text_areas is not None:
            label = self.render_label()
            linear_label = []
            for line in label:
                linear_label.extend(line)
        data = []
        for bit in self.data_bits:
            data.extend(bit for _ in range(self.scale))
        compressed = compress_gif(
            tuple(data * self.barcode_height + linear_label),
            self.bits_per_pixel
        )
        self._write_block_data(image_file, compressed)
    
    def _write_squares(self, image_file):
        data = []
        for line in self.data_bits:
            for _ in range(self.scale):
                for bit in line:
                    data.extend(bit for _ in range(self.scale))
        compressed = compress_gif(tuple(data), self.bits_per_pixel)
        self._write_block_data(image_file, compressed)
    
    def _write_text_area(self, image_file):
        # TODO: write table here, not in write bars
        pass

    def _write_finish(self, image_file):
        image_file.write(b";")
