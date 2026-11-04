// expect: -327744882
/* control flow */
int collatz(int n) { int s = 0; while (n != 1) { n = (n & 1) ? 3 * n + 1 : n / 2; s++; } return s; }
int sw(int x) {
    switch (x) {
        case 0: return 100;
        case 1: case 2: return 200;
        case 5: x += 7;
        case 6: x += 3; break;
        default: x = -1;
    }
    return x;
}
int main(void) {
    int i, j, h = 0;
    for (i = 0; i < 7; i++) h = h * 3 + sw(i);
    for (i = 1; i < 20; i++) h = h * 3 + collatz(i);
    i = 0; do { h += i; i += 3; } while (i < 20);
    for (i = 0; i < 10; i++) { if (i == 3) continue; if (i == 8) break; for (j = 0; j < i; j++) { h += j; if (j > 4) break; } }
    j = 5; while (j--) h = h * 2 + j;
    i = 0; goto skip; h += 1000; skip: h += 7;
    h += (h > 100 && h < 100000000) ? 1 : 2;
    h += (h < 0 || h == 5) ? 3 : 4;
    return h;
}
