// expect: 10929513
char composite[600];
static int isqrt(int n) { int r = 0; while ((r + 1) * (r + 1) <= n) r++; return r; }
int main(void) {
    int i, j, count = 0, sum = 0;
    for (i = 2; i < 600; i++) {
        if (!composite[i]) { count++; sum += i; for (j = i * i; j < 600; j += i) composite[j] = 1; }
    }
    return count * 100000 + sum + isqrt(1000) * 7;
}
