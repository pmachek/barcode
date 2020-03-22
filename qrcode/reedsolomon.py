# TODO: Cleanup: Remove encode/decode methods
from .galoisfield import GaloisField



primitive_polynomials = [0, 0, 0, 11, 19, 37, 67, 131, 285, 1033]


class ReedSolomonEncoder:
    def __init__(self, k, n=None, primitive_poly=None):
        if n is None and primitive_poly is None:
            primitive_poly = 285
            n = 255
        elif primitive_poly is None:
            primitive_poly = 285
        self.gf = GaloisField(primitive_poly)
        if n is None:
            n = self.gf.element_count
        elif n > self.gf.element_count:
            raise ValueError(
                "Block length doesn't correspond "
                "with supplied primitive polynomial"
            )
        self.n = n
        self.k = k
        self.corrections_len = n - k
        self.gf = GaloisField(primitive_poly)
        self.generator = self.compute_generator(self.corrections_len)

    def compute_generator(self, degree=None):
        if degree is None:
            degree = self.corrections_len
        length = degree + 1
        res_poly = [0] * length
        res_poly[0] = 1
        for i in range(1, length):
            k = self.gf.exp((i-1) % 255)
            for j in range(i, 0, -1):
                m = self.gf.mul(res_poly[j - 1], k)
                res_poly[j] = self.gf.add(res_poly[j], m)
        return bytes(res_poly)

    def compute_generator_slow(self, degree=None):
        if degree is None:
            degree = self.corrections_len
        g = [1]
        for i in range(degree):
            g = self.gf.poly_mul(g, (1, self.gf.exp(i % 255)))
        return bytes(g)

    def syndromes(self, data):
        count = self.corrections_len
        synd = [0] * count
        for i in range(count):
            synd[i] = self.gf.poly_eval(data, self.gf.exp(i % 255))
        return synd

    def correct_deletions(self, data, positions, syndromes=None):
        if syndromes is None:
            syndromes = self.syndromes(data)
        error_locator = [1]
        positions_len = len(positions)
        data_len = len(data)
        for i in range(positions_len):
            x = self.gf.exp(data_len - 1 - positions[i])
            error_locator = self.gf.poly_mul(error_locator, (x, 1))
        error_evaluator = syndromes[:positions_len]
        error_evaluator.reverse()
        error_evaluator = self.gf.poly_mul(error_locator, error_evaluator)
        eval_len = len(error_evaluator)
        error_evaluator = error_evaluator[eval_len - positions_len:eval_len]
        loc_len = len(error_locator)
        error_locator = error_locator[loc_len & 1:loc_len:2]
        corrected_data = list(data)
        for i in range(positions_len):
            x = self.gf.exp((positions[i] + 256 - data_len) % 255)
            y = self.gf.poly_eval(error_evaluator, x)
            x_2 = self.gf.mul(x, x)
            z = self.gf.poly_eval(error_locator, x_2)
            correction = self.gf.div(y, self.gf.mul(x, z))
            if correction != 0:
                p = positions[i]
                corrected_data[p] = self.gf.add(corrected_data[p], correction)
        return bytes(corrected_data)

    def find_errors(self, data, synd=None):
        if synd is None:
            synd = self.syndromes(data)
        err_poly = [1]
        old_poly = [1]
        for i in range(self.corrections_len):
            old_poly.append(0)
            delta = synd[i]
            err_poly_len = len(err_poly)
            for j in range(1, err_poly_len):
                m = self.gf.mul(err_poly[err_poly_len - 1 - j], synd[i - j])
                delta = self.gf.add(delta, m)
            if delta != 0:
                if len(old_poly) > err_poly_len:
                    new_poly = self.gf.poly_scale(old_poly, delta)
                    k = self.gf.inverse(delta)
                    old_poly = self.gf.poly_scale(err_poly, k)
                    err_poly = new_poly
                scaled_old = self.gf.poly_scale(old_poly, delta)
                err_poly = self.gf.poly_add(err_poly, scaled_old)
        errors = len(err_poly) - 1
        if errors * 2 > self.corrections_len:
            return None
        error_positions = []
        data_len = len(data)
        for i in range(data_len):
            e = self.gf.poly_eval(err_poly, self.gf.exp((255 - i) % 255))
            if e == 0:
                error_positions.append(data_len - i - 1)
        if len(error_positions) != errors:
            return None
        return error_positions

    def forney_syndromes(self, positions, synd):
        fsynd = list(synd)
        for i in range(len(positions)):
            index = (self.corrections_len - 1 - positions[i]) % 255
            x = self.gf.exp(index)
            for i in range(len(fsynd) - 1):
                k = self.gf.mul(fsynd[i], x)
                fsynd[i] = self.gf.add(k, fsynd[i + 1])
            fsynd.pop()
        return fsynd

    def encode_block(self, data):
        if type(data) != type(b""):
            raise TypeError("Data should be bytes type")
        if len(data) != self.k:
            raise ValueError("Encoded data length is not one block")
        correction_data = self.gf.poly_mod(data, self.generator)
        return bytes(correction_data)

    def decode_block(self, data):
        if type(data) != type(b""):
            raise TypeError("Data should be bytes type")
        data_len = len(data)
        if data_len != self.n:
            raise ValueError("Encoded data length is not one block")
        decoded = list(data)
        erasure_positions = []
        for i in range(data_len):
            if decoded[i] < 0:
                decoded[i] = 0
                erasure_positions.append(i)
        if len(erasure_positions) > self.corrections_len:
            # Too many erasures
            return None
        synd = self.syndromes(decoded)
        if max(synd) == 0:
            return data[:self.k]
        fsynd = self.forney_syndromes(erasure_positions, synd)
        error_positions = self.find_errors(decoded, fsynd)
        if error_positions == None:
            # Couldn't locate errors
            return None
        combined_errors = erasure_positions + error_positions
        decoded = self.correct_deletions(decoded, combined_errors)
        synd = self.syndromes(decoded)
        if max(synd) > 0:
            # Errors occured even after correction
            return None
        return decoded[:self.k]

    def encode(self, data):
        raise NotImplementedError()
        data_len = len(data)
        blocks = data_len // self.k
        encoded = b""
        i = 0
        for i in range(blocks):
            block = data[i * self.k: (i + 1) * self.k]
            encoded += self.encode_block(block)
        encoded_len = (i + 1) * self.k
        last_block_len = data_len - encoded_len
        if last_block_len != 0:
            padding = bytes(self.k - last_block_len)
            last_block = data[i * self.k:]
            padded_block = last_block + padding
            correction = self.gf.poly_mod(padded_block, self.generator)
            encoded += last_block + bytes(correction)
        return encoded

    def decode(self, data):
        raise NotImplementedError()
        data_len = len(data)
        blocks = data_len // self.n
        decoded = b""
        i = -1
        for i in range(blocks):
            block = data[i * self.n: (i + 1) * self.n]
            decoded += self.decode_block(block)
        decoded_len = (i + 1) * self.n
        last_block_len = data_len - decoded_len
        if last_block_len != 0:
            last_block = data[i * self.n:]
            last_data_len = last_block_len - self.corrections_len
            padding = bytes(self.n - last_block_len)
            last_data = last_block[:last_data_len]
            last_correction = last_block[last_data_len:]
            last_block = last_data + padding + last_correction
            decoded += self.decode_block(last_block)
        return decoded

    def test(self, data=None):
        if data is None:
            data = bytes(range(0, self.k))
        print("generator:", self.generator)
        print("data:", data)
        ec = self.encode_block(data)
        new_data = data + ec
        print("error correction:", ec)
        synd = self.syndromes(new_data)
        print("syndromes:", synd)
        err_data = b"\x01" + new_data[1:10] + b"\x07" + new_data[11:20] + \
                   b"\x08" + new_data[21:]
        print("err data:", err_data)
        synd = self.syndromes(err_data)
        print("syndromes:", synd)
        corrected_data = self.decode_block(err_data)
        print("corrected data:", corrected_data)
        print("Correction worked:", data == corrected_data)


def encode_block(data, n=None):
    k = len(data)
    rse = ReedSolomonEncoder(k, n)
    encoded = rse.encode_block(data)
    return encoded


def decode_block(data, k, n=None):
    rse = ReedSolomonEncoder(k, n)
    decoded = rse.decode_block(data)
    return decoded


def encode(data, n=None):
    k = len(data)
    rse = ReedSolomonEncoder(k, n)
    encoded = rse.encode(data)
    return encoded


def decode(data, k, n=None):
    rse = ReedSolomonEncoder(k, n)
    decoded = rse.decode(data)
    return decoded

if __name__ == "__main__":
    #data = [0x40, 0xd2, 0x75, 0x47, 0x76, 0x17, 0x32, 0x06,
    #        0x27, 0x26, 0x96, 0xc6, 0xc6, 0x96, 0x70, 0xec]
    #data = bytes(data)
    k = 223
    corrections_len = 32
    n = k + corrections_len
    rse = ReedSolomonEncoder(223, 255)
    rse.test()
