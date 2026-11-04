// expect: 1525168313
#include <stdarg.h>
static int sum(int n, ...) { va_list ap; int i, s = 0; va_start(ap, n); for (i = 0; i < n; i++) s = s * 3 + va_arg(ap, int); va_end(ap); return s; }
static int fmt(char *out, const char *f, ...) {
    va_list ap; int n = 0;
    va_start(ap, f);
    while (*f) {
        if (*f == '%') {
            f++;
            if (*f == 'd') { int v = va_arg(ap, int); if (v < 0) { out[n++] = '-'; v = -v; } if (v >= 100) out[n++] = '0' + v / 100 % 10; if (v >= 10) out[n++] = '0' + v / 10 % 10; out[n++] = '0' + v % 10; }
            else if (*f == 's') { const char *s = va_arg(ap, const char *); while (*s) out[n++] = *s++; }
            else if (*f == 'c') out[n++] = (char)va_arg(ap, int);
        } else out[n++] = *f;
        f++;
    }
    out[n] = 0;
    va_end(ap);
    return n;
}
char buf[64];
int main(void) {
    int h = sum(5, 1, 2, 3, 4, 5) + sum(0) * 100 + sum(1, 9) + sum(8, 1, 2, 3, 4, 5, 6, 7, 8);
    int n = fmt(buf, "x=%d y=%s z=%c w=%d!", 42, "ok", 'Q', -7);
    h = h * 31 + n;
    { int i; for (i = 0; i < n; i++) h = h * 31 + buf[i]; }
    return h;
}
