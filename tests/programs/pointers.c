// expect: 867268792
int a[10] = {5, 6, 7, 8, 9, 10, 11, 12, 13, 14};
int *pick(int **pp, int i) { *pp = &a[i]; return *pp; }
static int sumrange(int *lo, int *hi) { int s = 0; while (lo < hi) s += *lo++; return s; }
int main(void) {
    int *p = a, **pp = &p, i, h = 0;
    int *q = a + 9;
    char *c = (char *)a;
    void *v = a;
    int *w = (int *)v;
    h += *p + **pp + p[3] + *(p + 4) + 3[p];
    h = h * 31 + (int)(q - p) + (q > p) + (p < q) * 2 + (p == a) * 4 + (p != q) * 8 + (p >= q) * 16;
    h = h * 31 + *pick(pp, 7) + *p;
    h = h * 31 + sumrange(a, a + 10) + sumrange(a + 3, a + 6);
    h = h * 31 + w[2] + ((int *)((char *)w + 4))[0] + (int)((char *)(a + 3) - c);
    p = a;
    for (i = 0; i < 10; i++) { *p++ = i * i; }
    p -= 10;
    for (i = 0; i < 10; i++) h = h * 31 + p[i];
    h += (p + 5 == a + 5) + (&a[9] - &a[1]);
    return h;
}
