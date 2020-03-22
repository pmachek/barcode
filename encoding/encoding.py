from abc import ABC, abstractmethod


class BarcodeEncoding(ABC):
    """Linear barcode base class"""
    dimensionality = "linear"

    @classmethod
    def bits(cls, number, bit_length):
        for shift in range(bit_length - 1, -1, -1):
            yield (number >> shift) & 1

    @abstractmethod
    def bars(self, data, **extra):
        raise NotImplementedError

    @abstractmethod
    def label_text_areas(self, data):
        raise NotImplementedError

    @classmethod
    def label_mask(cls, data):
        return None
