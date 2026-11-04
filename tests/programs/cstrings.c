// expect: 756142331
/* C string routines over char arrays */
static int slen(const char *s) { const char *p = s; while (*p) p++; return (int)(p - s); }
static char *scpy(char *d, const char *s) { char *r = d; while ((*d++ = *s++)) ; return r; }
static int scmp(const char *a, const char *b) { while (*a && *a == *b) { a++; b++; } return (unsigned char)*a - (unsigned char)*b; }
static int atoi_(const char *s) { int n = 0, neg = 0; if (*s == '-') { neg = 1; s++; } while (*s >= '0' && *s <= '9') n = n * 10 + (*s++ - '0'); return neg ? -n : n; }
static int itoa_(int v, char *buf) {
    char tmp[12]; int n = 0, i = 0;
    unsigned u = v < 0 ? -(unsigned)v : (unsigned)v;
    if (u == 0) tmp[n++] = '0';
    while (u) { tmp[n++] = '0' + u % 10; u /= 10; }
    if (v < 0) buf[i++] = '-';
    while (n) buf[i++] = tmp[--n];
    buf[i] = 0;
    return i;
}
static void reverse(char *s) { int i = 0, j = slen(s) - 1; char t; while (i < j) { t = s[i]; s[i++] = s[j]; s[j--] = t; } }
char b1[40], b2[40];
int main(void) {
    int h = 0;
    scpy(b1, "Hello, LC-2K!");
    h += slen(b1);
    scpy(b2, b1); reverse(b2);
    h = h * 31 + scmp(b1, b2) + scmp(b1, b1) * 1000 + scmp("abc", "abd") + scmp("b", "a");
    h = h * 31 + atoi_("12345") + atoi_("-678") + atoi_("9x");
    h = h * 31 + itoa_(-9876, b1) + slen(b1) + b1[0] + b1[4];
    h = h * 31 + itoa_(0, b1) + b1[0];
    h = h * 31 + itoa_(2147483647, b1) + b1[9];
    return h;
}
