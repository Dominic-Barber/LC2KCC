// expect: 181889081
typedef int (*binop)(int, int);
typedef struct node { int v; struct node *l, *r; } node;
typedef struct { int tag; union { int i; char c[4]; }; struct { short a, b; }; } anon;
enum color { RED, GREEN = 5, BLUE = GREEN * 2, LAST };
enum { N = sizeof(int) * 3 + 1, M = N << 1 };
static int add(int a, int b) { return a + b; }
static int sub(int a, int b) { return a - b; }
static int mul(int a, int b) { return a * b; }
static binop ops[3] = { add, sub, mul };
static const int primes[] = { 2, 3, 5, 7, 11, 13 };
static int grid[M][N];
static node pool[7];
static node *build(int lo, int hi, int *next) {
    node *n; int mid;
    if (lo > hi) return 0;
    mid = (lo + hi) / 2;
    n = &pool[(*next)++];
    n->v = primes[mid % 6] + mid;
    n->l = build(lo, mid - 1, next);
    n->r = build(mid + 1, hi, next);
    return n;
}
static int walk(node *n, int depth) { return n ? walk(n->l, depth + 1) * 3 + n->v * depth + walk(n->r, depth + 1) : 0; }
static int apply(binop f, int a, int b) { return f(a, b); }
int main(void) {
    int i, j, h = 0, next = 0;
    anon an;
    char c = '\n', d = '\x41', e = '\101', f = '\\';
    for (i = 0; i < 3; i++) h = h * 31 + apply(ops[i], 20, 7);
    for (i = 0; i < M; i++) for (j = 0; j < N; j++) grid[i][j] = i * j - 3;
    for (i = 0; i < M; i++) h = h * 31 + grid[i][N - 1] + grid[M - 1 - i][i % N];
    h = h * 31 + walk(build(0, 6, &next), 1);
    an.tag = 9; an.i = 0x01020304; an.a = -5; an.b = 6;
    h = h * 31 + an.tag + an.a + an.b + (an.i & 0xff) + sizeof(anon);
    h = h * 31 + c + d + e + f + RED + GREEN + BLUE + LAST + N + M;
    h = h * 31 + (int)sizeof(grid) + (int)(sizeof grid / sizeof grid[0]) + (int)sizeof primes;
    return h;
}
