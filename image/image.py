#!/usr/bin/env python3
# Copyright Petr Machek
#
# Library for generating CODE93, CODE128B and CODE128C barcodes
# as bitmaps or svg images
#
from abc import ABC, abstractmethod


class BarcodeImage(ABC):
    file_open_mode = "wb"

    """Abstract class representing image of a 1D or 2D barcode

    Barcode can optionally contain a label, usually containing
    the same information as the barcode.
    """
    def __init__(self, data_bits, barcode_height=None, label_height=0,
                 scale=None, barcode_type="linear", text_areas=None,
                 text_mask=None, font=None):
        assert barcode_type in ("linear", "2D")
        if barcode_type == "linear":
            self.data_bits = list(data_bits)
            self.scale = scale or 2
            self.barcode_height = barcode_height
        else:
            # barcode_type == "2D"
            self.data_bits = [list(line) for line in data_bits]
            self.scale = scale or 8
            # height can't be chosen, its given by scale and content
            self.barcode_height = None
        self.barcode_type = barcode_type
        self.label_height = label_height
        self.text_areas = None
        self.text_mask = None
        self.font = None

    @property
    def image_height(self):
        """Total image height in pixels"""
        if self.barcode_type == "linear":
            return self.barcode_height + self.label_height
        # self.barcode_type == "2D"
        return len(self.data_bits) * self.scale  + self.label_height

    @property
    def image_width(self):
        """Total image width in pixels"""
        if self.barcode_type == "linear":
            return len(self.data_bits) * self.scale
        # self.barcode_type == "2D"
        return len(self.data_bits[0]) * self.scale

    def set_label(self, label_height, text_areas, text_mask, font):
        # TODO: sanity check
        self.label_height = label_height
        self.text_areas = text_areas
        self.text_mask = text_mask
        self.font = font

    def render_label(self):
        label = [
            [0] * (self.image_width)
            for _ in range(self.label_height)
        ]
        self.font.render_text_areas(
            self.text_areas,
            label,
            self.scale
        )
        # render mask into label
        if self.text_mask is not None:
            y = 0
            for mask_line in self.text_mask:
                mask_line_list = list(mask_line)
                for _ in range(self.scale):
                    label_line = label[y]
                    y += 1
                    for i, bit in enumerate(mask_line_list):
                        for j in range(self.scale):
                            label_line[self.scale * i + j] |= bit
        return label

    @abstractmethod
    def _write_header(self, image_file):
        pass

    @abstractmethod
    def _write_bars(self, image_file):
        pass

    @abstractmethod
    def _write_squares(self, image_file):
        pass

    @abstractmethod
    def _write_text_area(self, image_file):
        pass

    @abstractmethod
    def _write_finish(self, image_file):
        pass

    def write(self, image_file):
        self._write_header(image_file)
        if self.barcode_type == "linear":
            self._write_bars(image_file)
        elif self.barcode_type == "2D":
            self._write_squares(image_file)
        else:
            raise ValueError(
                "Unknown barcode type {!r}".format(self.barcode_type)
            )
        if self.text_areas is not None:
            self._write_text_area(image_file)
        self._write_finish(image_file)           
