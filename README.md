# Stripes and squares

Pure-python barcode and QR code generator with useful output formats and no dependencies beyond Python 3. This project's aim is to be multiplatform, simple to maintain and useful even in constrained environment, where installing imaging library is not possible or practical. Supported barcodes are Code93, Code128, EAN13 and EAN8. Supported output filetypes are png, gif, bmp and svg.

## Installing

Use pip to install:

```
pip install stripes-and-squares
```

You can also grab a src/stripes directory and copy it to your project. This is generally not a good practice, but you might do this if you'd have hard time dealing with pip on your platform or if you're worried about future version compatibility. I'll stabilize the API by version 1.0.0.

To see if everything is setup right, generate your first barcode:

```
python3 barcode.py --barcode-type=qr "HELLO WORLD" hello_world.png
```

## Running the tests

Testing is a bit tricky. Right now, I just open the all the files and scan them from my monitor with a mobile phone

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
