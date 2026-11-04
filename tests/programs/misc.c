// expect: -863047070
/* goto, statics, comma, ternary chains, do-while, labels, shadowing */
static int counter(void) { static int c; return ++c; }
static int shadow(int x) { { int x = 5; x += 2; } { int x = 100; return x; } }
const int table[] = { 5, 3, 8, 1, 9, 2 };
const char *names[] = { "alpha", "beta", "gamma" };
int main(void) {
    int i = 0, h = 0, n = sizeof table / sizeof table[0];
    char *p;
    loop: if (i >= n) goto done; h = h * 31 + table[i++]; goto loop;
    done:
    { int c1 = counter(); int c2 = counter(); int c3 = counter(); h += c1 + c2 * 10 + c3 * 100; }
    h += shadow(3);
    for (i = 0; i < 3; i++) for (p = (char *)names[i]; *p; p++) h = h * 31 + *p;
    i = (h > 0) ? 1 : (h < -100 ? 2 : 3);
    h += i; h += (i = 4, i * 5);
    do { h -= i; } while (--i > 0);
    h += n > 5 ? n < 7 ? 1000 : 2000 : 3000;
    return h;
}
