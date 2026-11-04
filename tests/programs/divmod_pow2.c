// expect: 922263585
int main(void) {
    int vals[] = { 0, 1, -1, 2, -2, 3, -3, 7, -7, 8, -8, 9, -9, 100, -100, 1023, -1024, 2147483647, -2147483647 - 1, 12345, -12345 };
    int i, h = 0, n = sizeof vals / sizeof vals[0];
    int *p = vals, *q = vals + 17;
    for (i = 0; i < n; i++) {
        int x = vals[i];
        h = h * 31 + x / 2 + x % 2 + x / 4 + x % 4 + x / 8 + x % 8 + x / 1024 + x % 1024 + x / 65536 + x % 65536 + x / 1 + x % 1;
    }
    h = h * 31 + (int)(q - p) + (int)(p - q);
    return h;
}
