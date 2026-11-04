// expect: 130
/* strings, static, 2D arrays, enum, comma, compound */
enum E { A, B = 5, C };
static int counter(void) { static int n = 10; return ++n; }
const char *msg = "hello, world";
char buf[32];
int grid[3][4];
int len(const char *s) { int n = 0; while (*s++) n++; return n; }
int main(void) {
    int i, j, h = 0;
    for (i = 0; i < 3; i++) for (j = 0; j < 4; j++) grid[i][j] = i * 10 + j;
    for (i = 0; i < 3; i++) for (j = 0; j < 4; j++) h = h * 3 + grid[i][j];
    h += len(msg) + len("abc") + msg[4];
    for (i = 0; i < 12; i++) buf[i] = msg[i] + 1;
    buf[12] = 0;
    h = h * 3 + len(buf) + buf[0];
    h = h * 3 + counter() + counter() + counter();
    h = h * 3 + A + B + C;
    h = (h += 3, h * 2);
    h ^= 0xabcd; h |= 3; h &= ~4; h <<= 2; h >>= 1; h -= 5; h *= 3; h /= 7; h %= 1000;
    return h;
}
