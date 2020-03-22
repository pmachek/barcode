from .image import BarcodeImage


class SvgBarcodeImage(BarcodeImage):
    file_open_mode = "w"

    """Class for saving barcode image as .svg file"""
    SVG_OPEN = '<svg xmlns="http://www.w3.org/2000/svg"\n'\
        '    version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink"\n'\
        '    width="{width}" height="{height}">\n'
    SVG_CLOSE = "</svg>\n"
    RECTANGLE = '    <rect x="{x}" y="{y}" width="{width}"'\
                ' height="{height}" fill="{fill}" />\n'
    TEXT = '    <text x="{x}" y="{y}" width="{width}"'\
           ' height="{height}" font-size="{font_size}"'\
           ' font-family="monospace" color="#000">{text}</text>\n'  #TODO: font size settings
    
    def _write_header(self, image_file):
        image_file.write(
            self.SVG_OPEN.format(
                width=self.image_width,
                height=self.image_height
            )
        )
        image_file.write(
            self.RECTANGLE.format(
                x=0,
                y=0,
                width=self.image_width,
                height=self.image_height,
                fill="#fff"
            )
        )

    def _write_squares(self, image_file):
        # TODO: better square merging, maybe polygon painting
        bits = [[bit for bit in line] for line in self.data_bits]
        size = len(bits)
        for y in range(size):
            x = 0
            while x < size:
                if bits[y][x] == 0:
                    x = x + 1
                    continue
                next_x = x + 1
                while next_x < size and bits[y][next_x]:
                    bits[y][next_x] = 0
                    next_x += 1
                width = next_x - x
                height = 1
                while y + height < size and \
                    all(bits[y + height][t] for t in range(x, next_x)):
                    for t in range(x, next_x):
                        bits[y + height][t] = 0
                    height += 1
                image_file.write(
                    self.RECTANGLE.format(
                        x=x * self.scale,
                        y=y * self.scale,
                        width=width * self.scale,
                        height=height * self.scale,
                        fill="#000"
                    )
                )
                x = next_x

    def _write_text_area(self, image_file):
        # TODO: fix vertical alignment
        for text_area in self.text_areas:
            x = text_area["x_start"] * self.scale
            y = self.barcode_height + \
                (text_area["y_start"] + self.font.height) * self.scale
            width = text_area["x_end"] * self.scale - x
            if text_area.get("y_end") is None:
                height = self.label_height - y
            elif text_area["y_end"] >= 0:
                height = text_area["y_end"] * self.scale - y
            else:
                # text_area["y_end"] < 0
                y_end = self.image_height + text_area["y_end"] * self.scale
                height = y_end - y
            image_file.write(
                self.TEXT.format(
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    font_size=self.font.height * self.scale,
                    text=text_area["text"]
                )
            )
   
    def _write_bars(self, image_file):
        start = None
        prev = None
        for i, bit in enumerate(self.data_bits):
            if prev == 0 and bit == 1:
                start = i
            elif prev == 1 and bit == 0:
                image_file.write(
                    self.RECTANGLE.format(
                        x=start * self.scale,
                        y=0,
                        width=(i - start) * self.scale,
                        height=self.barcode_height,
                        fill="#000"
                    )
                )
                start = None
            prev = bit
        if start is not None:
            # if the barcode ends with black bar (which it typically wont)
            image_file.write(
                self.RECTANGLE.format(
                    x=i * start,
                    y=0,
                    width=(i - start) * self.scale,
                    height=self.barcode_height,
                    fill="#000"
                )
            )


    def _write_finish(self, image_file):
        image_file.write(self.SVG_CLOSE)        

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
                    y=0,
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
