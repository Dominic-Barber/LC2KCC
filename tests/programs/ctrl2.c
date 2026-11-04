// expect: 872433545
static int steps;
static int f(int n) { int i, r = 0; for (i = 0; ; i++) { if (i >= n) return r; if (i % 2) continue; r += i; steps++; } }
static int g(int n) { int r = 0; while (1) { r += n; if (r > 50) break; n++; } return r; }
static int sw(int c) {
    switch (c) {
        case 'a': return 1;
        case 'b': case 'c': return 2;
        case 100: { int x = c * 2; return x; }
        case -1: return 77;
        case 1000: return 5;
    }
    return 0;
}
static int nested(int x, int y) {
    switch (x) { case 1: switch (y) { case 1: return 11; case 2: return 12; } break; case 2: return 20; default: return -1; }
    return 99;
}
int main(void) {
    int i, j, h = 0, k = 0;
    h += f(10) + g(3) + steps;
    for (i = 0; i < 6; i++) h = h * 31 + sw("abcxd"[i % 5]) + sw(i == 3 ? 100 : i == 4 ? -1 : 1000);
    for (i = 0; i < 4; i++) for (j = 0; j < 4; j++) h = h * 31 + nested(i, j);
    for (i = 0, j = 10; i < j; i += 2, j--) k += i * j;
    h += k;
    for (;;) { k--; if (k < 0) break; }
    i = 0; do { i++; if (i == 3) continue; h += i; } while (i < 6);
    { int arr[5] = {1,2,3,4,5}; int *p = arr; while (p < arr + 5) h = h * 3 + *p++; }
    return h + k;
}
