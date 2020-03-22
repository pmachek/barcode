from font import font5x7

from image.png import PngBarcodeImage
from image.svg import SvgBarcodeImage
from image.bmp import BmpBarcodeImage

from barcode import main as barcode_main


def test_png_barcode():
    bits = [0,0,0,0,1,0,1,0,1,0,1,0,0,0,0]
    bits.extend(0 for _ in range(40))
    img = PngBarcodeImage(data_bits=bits, label_height=30, barcode_height=20)
    img.text_areas = [{
        "text": "012",
        "x_start": 3,
        "y_start": 3,
        "x_end": 21,
        "y_end": 12
    }]
    img.font = font5x7
    with open("test_png_barcode_image.png", "wb") as file:
        img.write(file)
    img2 = PngBarcodeImage(
        data_bits=[
            [0,0,0,0,0],
            [0,1,1,1,0],
            [0,1,1,1,0],
            [0,1,1,1,0],
            [0,0,0,0,0]
        ],
        barcode_type="2D"
    )
    with open("test_png_2d_image.png", "wb") as file:
        img2.write(file)


def test_svg_image():
    bits = [0,0,0,0,1,0,1,0,1,0,1,0,0,0,0]
    img = SvgBarcodeImage(data_bits=bits, barcode_height=20)
    with open("test_svg_barcode_image.svg", "w") as file:
        img.write(file)
    img2 = SvgBarcodeImage(
        data_bits=[
            [0,0,0,0,0],
            [0,1,1,1,0],
            [0,1,1,1,0],
            [0,1,1,1,0],
            [0,0,0,0,0]
        ],
        barcode_type="2D"
    )
    with open("test_svg_2d_image.svg", "w") as file:
        img2.write(file)


def test_cmd():
    contents = ("hello world", "HELLO WORLD", "0123456789")
    barcode_types = ("code93", "code128", "qrcode")
    file_types = ("png", "svg", "bmp")
    for content in contents:
        for barcode_type in barcode_types:
            for file_type in file_types:
                args = [
                    "--barcode-type={}".format(barcode_type),
                    "--file-type={}".format(file_type),
                    content,
                    "{}_{}.{}".format(content, barcode_type, file_type)
                ]
                #if barcode_type != "qrcode" and content.isnumeric():
                #    args.insert(2, "--label={}".format(content))
                print(args)
                barcode_main(args)
    ean_contents = ("1234567", "012345678901")
    for content in ean_contents:
        for file_type in file_types:
            args = [
                "--barcode-type=ean",
                "--file-type={}".format(file_type),
                "--label={}".format(content),
                content,
                "{}_{}.{}".format(content, "ean", file_type)
            ]
            print(args)
            barcode_main(args)


if __name__ == "__main__":
    import traceback

    # take locals by copy because locals will change during iteration
    loc = dict(locals())
    for name, function in loc.items():
        if name.startswith("test_") and callable(function):
            try:
                function()
            except:
                print(traceback.format_exc())
