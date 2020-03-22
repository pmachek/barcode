import argparse

from encoding.code93 import Code93
from encoding.code128 import Code128
from encoding.ean import Ean

from font import font5x7

from qrcode.qrcode import QRCode

from image.svg import SvgBarcodeImage
from image.png import PngBarcodeImage
from image.bmp import BmpBarcodeImage


parser = argparse.ArgumentParser(
    description="Generate an image of barcode",
)
parser.add_argument(
    '--file-type',
    type=str,
    default="png",
    choices=["svg", "png", "bmp"],
    help="Generated image filetype."
)
parser.add_argument(
    "--barcode-type",
    type=str,
    default="qr",
    choices=["code128", "code93", "ean", "qr", "qrcode"],
    help="Type of barcode used."
)
parser.add_argument(
    "--scale",
    type=lambda x: int(x) > 0 and int(x),
    default=None,
    help="Bar width for 1D barcodes and elementary module "\
         "size for 2D barcode (in pixels)."
)
parser.add_argument(
    # TODO: Consider encoding type to choose the right default
    "--barcode-height",
    type=lambda x: int(x) > 0 and int(x),
    default=50,
    help="Barcode height. Does not include text areas. Ignored for "\
         "2D barcodes as their height is determined by --scale."
)
parser.add_argument(
    "--label",
    type=str,
    default=None,
    help="Text label appearing under linear barcode. "\
         "Not supported for 2D barcodes."
)
parser.add_argument(
    "--label-height",
    type=lambda x: int(x) > 0 and int(x),
    default=None,
    help="Label height."
)
parser.add_argument(
    "content",
    type=str,
    help="Content of barcode."
)
parser.add_argument(
    "out",
    type=str,
    help="Output path."
)


def main(cmd_args=None):
    encoding_classes = {
        "code128": Code128,
        "code93": Code93,
        "ean": Ean,
        "qr": QRCode,
        "qrcode": QRCode
    }
    image_classes = {
        "svg": SvgBarcodeImage,
        "png": PngBarcodeImage,
        "bmp": BmpBarcodeImage
    }
    if cmd_args is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(cmd_args)
    
    encoding = encoding_classes.get(args.barcode_type)
    if encoding is None:
        raise ValueError(
            "Unknown barcode encoding {!r}".format(args.barcode_type)
        )
    scale = args.scale or (2 if encoding.dimensionality == "linear" else 16)
    barcode_height = args.barcode_height  # TODO: take default height from barcode type
    image_class = image_classes.get(args.file_type)
    if image_class is None:
        raise ValueError(
            "Unknown image file type {!r}".format(args.file_type)
        )

    data = None
    if encoding.dimensionality == "linear":
        data = encoding.bars(args.content)
    elif encoding.dimensionality == "2D":
        data = encoding.image_bits(args.content)
    else:
        raise NotImplementedError
    image = image_class(
        data_bits=data,
        barcode_height=args.barcode_height,
        scale=scale,
        barcode_type=encoding.dimensionality,
    )
    if args.label is not None:
        # TODO: support for 2D barcode label
        font = font5x7
        label_height = args.label_height or (scale * (font.height + 6))
        text_areas = encoding.label_text_areas(args.label)
        text_mask = encoding.label_mask(args.label)  # TODO: support label masks
        image.set_label(label_height, text_areas, text_mask, font)
    with open(args.out, image.file_open_mode) as image_file:
        image.write(image_file)


if __name__ == "__main__":
    main()
