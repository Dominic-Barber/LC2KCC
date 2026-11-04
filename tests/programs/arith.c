// expect: 1054031655
/* arithmetic & bit ops */
static int h = 0;
static void mix(int v) { h = h * 31 + v; }
int main(void) {
    int a = 1234567, b = -98765, c = 77, d = 0;
    unsigned u = 4000000000u, v = 12345u;
    mix(a + b); mix(a - b); mix(b - a); mix(a & b); mix(a | b); mix(a ^ b); mix(~a); mix(-b);
    mix(a & 0xff); mix(a | 0x100); mix(a ^ 0x5555); mix(c * 3); mix(c * 100); mix(c * b); mix(a * b);
    mix(a / c); mix(a % c); mix(b / c); mix(b % c); mix(a / -c); mix(a % -c); mix(b / -c); mix(b % -c);
    mix((int)(u / v)); mix((int)(u % v)); mix((int)(u / 7)); mix((int)(u % 1000)); mix((int)(u / 16)); mix((int)(u % 16));
    mix(a << 3); mix(a << c % 5); mix(b >> 3); mix(b >> 1); mix((int)(u >> 5)); mix((int)(u >> 31)); mix(a >> 20); mix(b >> 31);
    mix(1 << 10); mix(5 - 7); mix(0 - u); mix(d - 1);
    mix(u < v); mix(v < u); mix(a < b); mix(b < a); mix(a <= a); mix(a >= b); mix(u > 3); mix(-1 < 0u);
    mix(a == b); mix(a != b); mix(!a); mix(!d); mix(a && b); mix(d || a); mix(d && a);
    return h;
}
