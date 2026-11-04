// expect: 1119172816
/* less common but valid C */
static inline int twice(int x) { return x * 2; }
typedef int row4[4];
struct pt { int x, y; };
union bits { unsigned u; struct { unsigned char b0, b1, b2, b3; } b; };
int (*pick(int which))(int) { static int (*tab[2])(int) = { twice, 0 }; return tab[which]; }
static int sum_rows(row4 *m, int n) { int i, j, s = 0; for (i = 0; i < n; i++) for (j = 0; j < 4; j++) s += m[i][j] * (i + 1); return s; }
static int count(const char *const *names) { int n = 0; while (names[n]) n++; return n; }
static struct pt mid(struct pt a, struct pt b) { struct pt r = { (a.x + b.x) / 2, (a.y + b.y) / 2 }; return r; }
static long lsum(long a, unsigned long b, short c, signed char d) { return a + (long)b + c + d; }
int main(void) {
    register int r = 3;
    int a[2][4] = { {1, 2, 3, 4}, {5, 6, 7, 8} }, h = 0;
    int (*pa)[4] = a;
    const char *const names[] = { "x", "yy", "zzz", 0 };
    struct pt p = mid((struct pt){ 10, 20 }, (struct pt){ 30, 41 });
    long int li = -5L;
    unsigned long long_ = 4000000000ul;
    short int si = 7; unsigned short int usi = 65535; unsigned u = 3;
    h += twice(r) + pick(0)(5) + sum_rows(a, 2) + count(names) + p.x * 100 + p.y;
    h = h * 31 + (int)(long_ / 1000) + (int)li + si + usi + (int)u + (int)lsum(1, 2, 3, -4);
    h = h * 31 + pa[1][2] + (*pa)[3] + *(*(pa + 1) + 1);
    h = h * 31 + (pick(0) == twice) + (int)sizeof(row4) + (int)sizeof(int[10]) + (int)sizeof(*pa) + (int)sizeof a[0][0];
    { union bits ub; ub.u = 0; ub.b.b1 = 3; h = h * 31 + (int)ub.b.b1 + (ub.b.b0 == 0); }
    { char c = 'a'; c += 2; c *= 2; h = h * 31 + c; }
    h += ((void)0, 7) + (int)(&a[1][0] - &a[0][0]);
    return h;
}
