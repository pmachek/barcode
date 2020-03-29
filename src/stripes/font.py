import re
from os import path


def repeat(it, coeff):
    for value in it:
        for _ in range(coeff):
            yield value


class Font:
    def __init__(self, filename):
        self.characters = self.load_models(filename)
        sample_char = [[]]
        for character in self.characters.values():
            sample_char = character
            break
        self.height = len(sample_char)
        self.width = len(sample_char[0])
        self.space = 1
    
    def load_models(self, filename):
        result = {}
        with open(filename, 'r') as in_file:
            lines = iter(in_file)
            first_line = next(lines).lower()
            if not re.match(r"characters \d+x\d+$", first_line):
                raise RuntimeError(
                    "Font resource file must start with character dimension "
                    "definition in format 'characters WIDTHxHEIGHT'. "
                    "for example 'characters 3x5'"
                )
            width, height = (int(val) for val in first_line[11:].split("x"))
            char = None
            pixels = []
            for line in lines:
                line = line.rstrip()
                if char is None and not line:
                    continue
                if char is None:
                    char = line
                    if len(char) > 1:
                        raise RuntimeError(
                             "Expected line with single character"
                        )
                else:
                    pixels.append([
                        i < len(line) and not line[i] == ' '
                        for i in range(width)
                    ])
                    if len(pixels) == height:
                        result[char] = pixels
                        char = None
                        pixels = []          
            return result

    def render_text(self, text, canvas, x_offset=0, y_offset=0, size_coeff=1):
        x = x_offset
        y = y_offset
        for char in text:
            char_model = self.characters.get(char)
            if char_model is None:
                raise ValueError(
                    "Font can't render character {!r}.".format(char)
                )
            for v, line in enumerate(repeat(char_model, size_coeff), y):
                for h, value in enumerate(repeat(line, size_coeff), x):
                    try:
                        canvas[v][h] |= value
                    except IndexError:
                        print("len(canvas), v:", len(canvas), v)
                        print("len(canvas[0]), h:", len(canvas[0]), h)
                        raise ValueError

            x += (self.width + self.space) * size_coeff
    
    def render_text_areas(self, label_text_areas, canvas, bar_width=2):
        max_size_coeff = 10000  # how many times can be the font upsized
        for area in label_text_areas:
            end = area["x_end"]
            if area["x_start"] is not None:
                area_width = bar_width * (end - area["x_start"])
                text_width = \
                    len(area["text"]) * (self.width + self.space) - self.space
                size_coeff = area_width // text_width
                max_size_coeff = min(max_size_coeff, size_coeff)
                if area.get("y_end"):
                    area_height = bar_width * (area["y_end"] - area["y_start"])
                    size_coeff = area_height // self.height
                    max_size_coeff = min(max_size_coeff, size_coeff)
        for area in label_text_areas:
            area_width = bar_width * (area["x_end"] - area["x_start"])
            text_width = \
                len(area["text"]) * (self.width + self.space) - self.space
            text_width *= max_size_coeff
            x_align = (area_width - text_width) // 2
            y_align = 0
            if area.get("y_end"):
                area_height = bar_width * (area["y_end"] - area["y_start"])
                y_align = (area_height - max_size_coeff * self.height) // 2
            self.render_text(
                area['text'],
                canvas,
                area['x_start'] * bar_width + x_align,
                area['y_start'] * bar_width + y_align,
                max_size_coeff
            )


data_dir = path.abspath(path.join(path.dirname(__file__), "data"))

font3x5 = Font(path.join(data_dir, "font3x5.txt"))
font5x7 = Font(path.join(data_dir, "font5x7.txt"))
