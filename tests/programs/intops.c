// expect: -728882847
int main(void) {
    unsigned char a = 200, b = 100;
    signed char sc = -5;
    short s = -300;
    unsigned short us = 65000;
    int h = 0;
    char c = -1;
    h = h * 31 + (a + b) + (unsigned char)(a + b) + (a * b) + (a - b - 200);
    h = h * 31 + (sc < 0) + (sc >> 1) + (sc << 2) + (-sc) + (~sc) + (sc * sc) + (sc / 2) + (sc % 3);
    h = h * 31 + (s * s) + (us + us) + (s >> 3) + (us >> 3) + (us << 4) + (short)(us << 4) + (s / 7) + (s % 7);
    h = h * 31 + (c < 0) + (c == -1) + ((unsigned char)c == 255) + (c >> 3);
    h = h * 31 + (-1 < 0u) + (-1 > 1u) + (s < us) + ((unsigned)s > 100) + (a > sc) + (us > s);
    h = h * 31 + !!a + !!0 + !a + !!!a + (a && b) + (a || 0) + (0 && a) + (1 ? a : b);
    h = h * 31 + (0x7fffffff + 1 < 0) + (2147483647 + 1u > 5) + (-2147483647 - 1 < 0) + (4000000000u > 3000000000u);
    h = h * 31 + ((a ^ b) & 0xf0 | 3) + (a | b << 1) + (a & ~b);
    h = h * 31 + (7 / 2) + (-7 / 2) + (7 / -2) + (-7 / -2) + (7 % 2) + (-7 % 2) + (7 % -2) + (-7 % -2);
    h = h * 31 + (1 << 30) + (1u << 31 >> 31) + (-8 >> 1) + (0x80000000u >> 1);
    return h;
}
