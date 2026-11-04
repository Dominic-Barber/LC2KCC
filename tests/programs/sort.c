// expect: -480593266
/* sorting with function-pointer comparators */
int data[40];
static unsigned seed = 12345;
static int rnd(void) { seed = seed * 1103515245u + 12345u; return (int)((seed >> 16) & 0x7fff); }
static void bubble(int *a, int n) {
    int i, j, t;
    for (i = 0; i < n - 1; i++)
        for (j = 0; j < n - 1 - i; j++)
            if (a[j] > a[j + 1]) { t = a[j]; a[j] = a[j + 1]; a[j + 1] = t; }
}
static void isort(int *a, int n) {
    int i, j, k;
    for (i = 1; i < n; i++) {
        k = a[i];
        for (j = i - 1; j >= 0 && a[j] > k; j--) a[j + 1] = a[j];
        a[j + 1] = k;
    }
}
static int asc(const void *x, const void *y) { return *(const int *)x - *(const int *)y; }
static int desc(const void *x, const void *y) { return *(const int *)y - *(const int *)x; }
static void swap_words(int *p, int *q) { int t = *p; *p = *q; *q = t; }
static void qs(int *a, int lo, int hi, int (*cmp)(const void *, const void *)) {
    int i, last;
    if (lo >= hi) return;
    swap_words(&a[lo], &a[(lo + hi) / 2]);
    last = lo;
    for (i = lo + 1; i <= hi; i++)
        if (cmp(&a[i], &a[lo]) < 0) { last++; swap_words(&a[last], &a[i]); }
    swap_words(&a[lo], &a[last]);
    qs(a, lo, last - 1, cmp);
    qs(a, last + 1, hi, cmp);
}
static int check(int *a, int n) { int i, h = 0; for (i = 0; i < n; i++) h = h * 31 + a[i]; return h; }
int main(void) {
    int i, h = 0;
    for (i = 0; i < 40; i++) data[i] = rnd() % 1000 - 500;
    bubble(data, 40); h += check(data, 40);
    for (i = 0; i < 40; i++) data[i] = rnd() % 1000;
    isort(data, 40); h = h * 7 + check(data, 40);
    for (i = 0; i < 40; i++) data[i] = rnd();
    qs(data, 0, 39, asc); h = h * 7 + check(data, 40);
    qs(data, 0, 39, desc); h = h * 7 + check(data, 40);
    return h;
}
