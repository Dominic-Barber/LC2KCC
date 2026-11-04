// expect: 17006442
static int hanoi(int n, int a, int b, int c) { return n == 0 ? 0 : hanoi(n - 1, a, c, b) + 1 + hanoi(n - 1, c, b, a); }
static int ack(int m, int n) { return m == 0 ? n + 1 : (n == 0 ? ack(m - 1, 1) : ack(m - 1, ack(m, n - 1))); }
static int gcd(int a, int b) { return b ? gcd(b, a % b) : a; }
static int power(int b, int e) { int r = 1; while (e) { if (e & 1) r *= b; b *= b; e >>= 1; } return r; }
static int memo[40];
static int fibm(int n) { if (n < 2) return n; if (memo[n]) return memo[n]; return memo[n] = fibm(n - 1) + fibm(n - 2); }
static int collatz_len(unsigned n) { int c = 0; while (n != 1) { n = n % 2 ? 3 * n + 1 : n / 2; c++; } return c; }
int main(void) {
    int h = hanoi(9, 1, 2, 3);
    h = h * 7 + ack(2, 3) + gcd(1071, 462) + gcd(17, 5) + power(3, 13) + power(-2, 9) + fibm(30);
    h = h * 7 + collatz_len(27) + collatz_len(97);
    return h;
}
