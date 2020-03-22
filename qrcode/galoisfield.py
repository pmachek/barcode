def modulo_gf2(a, mod):
    mod_bitlen = mod.bit_length()
    a_bitlen = a.bit_length()
    if a_bitlen < mod_bitlen:
        return a
    m = mod << (a_bitlen - mod_bitlen)
    bit = 1 << (a_bitlen - 1)
    while m >= mod:
        if a & bit:
            a ^= m
        bit >>= 1
        m >>= 1
    return a

def modulo_gfn(a, mod, n):
    if a < mod:
        return a
    a_poly = []
    mod_poly = []
    while a > 0:
        a_poly.append(a % n)
        a = a // n
    while mod > 0:
        mod_poly.append(mod % n)
        mod = mod // n
    a_poly.reverse()
    mod_poly.reverse()
    mod_len = len(mod_poly)
    steps = len(a_poly) - mod_len + 1
    for i in range(steps):
        a_coeff = a_poly[i]
        if a_coeff != 0:
            for j in range(mod_len):
                c = a_poly[i + j] - a_coeff * mod_poly[j]
                a_poly[i + j] = c % n
    for i in range(mod_len + 1):
        a = a * n + a_poly[i]
    return a
    

class GaloisField:
    def __init__(self, primitive_poly=285, characteristic=2):
        self.primitive_poly = primitive_poly
        self.characteristic = characteristic
        if characteristic == 2:
            power = primitive_poly.bit_length()
            self.element_count = 2 ** (power - 1) - 1
        else:
            raise NotImplementedError("Characteristic must be 2")
        self.exp_table = [1] * (self.element_count + 1)
        self.log_table = [0] * (self.element_count + 1)
        if characteristic == 2:
            self.mod = lambda x: modulo_gf2(x, primitive_poly)
        else:
            self.mod = lambda x: modulo_gfn(x, primitive_poly, characteristic)
        for i in range(1, self.element_count):
            e = self.mod(characteristic * self.exp_table[i - 1])
            self.exp_table[i] = e
            self.log_table[e] = i
        self.log_table[0] = None

    def mul(self, a, b):
        if a == 0 or b == 0:
            return 0
        power = self.log_table[a] + self.log_table[b]
        return self.exp_table[power % self.element_count]

    def div(self, a, b):
        power = self.log_table[a] - self.log_table[b]
        return self.exp_table[power % self.element_count]

    def add(self, a, b):
        return a ^ b

    def exp(self, a):
        return self.exp_table[a]

    def log(self, a):
        return self.log_table[a]

    def inverse(self, a):
        power = -self.log_table[a]
        return self.exp_table[power % self.element_count]

    def poly_mul_standard(self, a, b):
        a_len = len(a)
        b_len = len(b)
        res = [0] * (b_len + a_len - 1)
        for i in range(a_len):
            ai = a[i]
            for j in range(b_len):
                m = self.mul(ai, b[j])
                res[i + j] = self.add(res[i + j], m)
        return res

    def poly_mul_karatsuba(self, a, b):
        a_len = len(a)
        b_len = len(b)
        if a_len < 7 or b_len < 7:
            return self.poly_mul_standard(a, b)
        split1 = a_len // 2
        split2 = b_len // 2
        p1 = a[:split1]
        p2 = a[split1:]
        q1 = b[:split2]
        q2 = b[split2:]
        z2 = self.poly_mul(p2, q2)
        z0 = self.poly_mul(p1, q1)
        z1 = self.poly_mul(self.poly_add(p1, p2), self.poly_add(q1, q2))
        z1 = self.poly_add(z1, z2)
        z1 = self.poly_add(z1, z0)
        return z0 + z1 + z2

    def poly_mul(self, a, b):
        return self.poly_mul_karatsuba(a, b)

    def poly_mod(self, a, b):
        a_len = len(a)
        b_len = len(b)
        res = list(a) + [0] * (b_len - 1)
        for i in range(a_len):
            resi = res[i]
            if resi != 0:
                for j in range(b_len):
                    m = self.mul(resi, b[j])
                    res[i + j] = self.add(res[i + j], m)
        return res[a_len:]

    def poly_mod2(self, a, b):
        b_len = len(b)
        a_len = len(a)
        res = list(a[1:b_len])
        mul_a = b[0]
        mul_b = a[0]
        cmul_a = 1
        for i in range(a_len):
            print(res)
            if mul_b != 0:
                for j in range(b_len - 1):
                    m_a = self.mul(res[j], mul_a)
                    m_b = self.mul(b[j + 1], mul_b)
                    res[j] = self.add(m_a, m_b)
            cmul_a = self.mul(mul_a, cmul_a)
            mul_b = res[0]
            for j in range(1, b_len - 1):
                res[j - 1] = res[j]
            index = b_len - 1 + i
            if index < a_len:
                res[b_len - 2] = self.mul(cmul_a, a[index])
            else:
                res[b_len - 2] = 0
        return res

    def poly_add(self, a, b):
        a_len = len(a)
        b_len = len(b)
        d = abs(a_len - b_len)
        if a_len > b_len:
            res = list(a)
            for i in range(b_len):
                res[d + i] = self.add(a[i + d], b[i])
        else:
            res = list(b)
            for i in range(a_len):
                res[d + i] = self.add(b[i + d], a[i])
        return res

    def poly_scale(self, a, b):
        a_len = len(a)
        res = [0] * a_len
        for i in range(a_len):
            res[i] = self.mul(a[i], b)
        return res

    def poly_eval(self, polynomial, x):
        # Horner scheme polynomial evaluation
        y = polynomial[0]
        for i in range(1, len(polynomial)):
            m = self.mul(y, x)
            y = self.add(polynomial[i], m)
        return y

    def poly_interpolation(self, points):
        interpolation = [0]
        points_len = len(points)
        for i in range(points_len):
            part = [points[i][1]]
            for j in range(points_len):
                if j == i:
                    continue
                part = self.poly_mul((1, points[j][0]), part)
                k = self.add(points[i][0], points[j][0])
                part = self.poly_mul(part, [self.inverse(k)])
            interpolation = self.poly_add(interpolation, part)
        return interpolation


if __name__ == "__main__":
    gf = GaloisField(285)
    p = [1, 2, 3, 4]
    q = [3, 4, 5, 6, 0, 0]
    print(bytes(gf.poly_mul(p, q)))
    print(bytes(gf.poly_mod(q, p)))
    # print(gf.poly_mod2(p2, p1))
