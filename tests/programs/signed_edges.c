// expect: -2027471072
int ids[] = { 0, 1, -1, 2, -2, 7, -7, 100, -100, 2147483647, -2147483647 - 1, 65536, -65536, 12345678 };
int main(void) {
    int i, j, h = 0, n = sizeof ids / sizeof ids[0];
    unsigned u;
    for (i = 0; i < n; i++) {
        for (j = 0; j < n; j++) {
            int a = ids[i], b = ids[j];
            h = h * 31 + (a < b) + (a <= b) * 2 + (a > b) * 4 + (a >= b) * 8 + (a == b) * 16;
            u = (unsigned)a;
            h = h * 31 + (u < (unsigned)b) + (u >= (unsigned)b) * 2;
            h = h * 31 + (a + b) + (a - b) * 3 + (a ^ b) + (a & b) + (a | b);
            if (b != 0 && !(a == -2147483647 - 1 && b == -1)) h = h * 31 + a / b + a % b;
            h = h * 31 + (a >> (j & 15)) + (int)((unsigned)a >> (j & 15)) + (a << (j & 7));
            h = h * 31 + a * b;
        }
    }
    return h;
}
