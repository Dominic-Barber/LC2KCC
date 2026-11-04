// expect: 657667
/* structs, unions, function pointers, recursion */
struct P { int x; short y; char z; struct P *next; };
struct Q { char a[5]; struct P p; int w[3]; };
union U { int i; char c; };
struct P gp = { 1, 2, 3, 0 };
struct Q gq = { {1,2,3,4,5}, {6,7,8,0}, {9,10,11} };
int fib(int n) { return n < 2 ? n : fib(n - 1) + fib(n - 2); }
int twice(int (*f)(int), int x) { return f(f(x)); }
int inc(int x) { return x + 1; }
int sq(int x) { return x * x; }
int sum(struct P *p) { int s = 0; while (p) { s += p->x + p->y + p->z; p = p->next; } return s; }
int main(void) {
    struct P a, b, c;
    struct Q q;
    int h = 0;
    a.x = 10; a.y = -3; a.z = 4; a.next = &b;
    b.x = 20; b.y = 5; b.z = -1; b.next = &c;
    c = gp; c.x = 99;
    h += sum(&a);
    q = gq; q.w[1] += 100; q.p.y = 77; q.a[3] = 9;
    h = h * 5 + q.w[0] + q.w[1] + q.w[2] + q.p.x + q.p.y + q.p.z + q.a[0] + q.a[3];
    h = h * 5 + fib(15);
    h = h * 5 + twice(inc, 5) + twice(sq, 3);
    h = h * 5 + sizeof(struct P) + sizeof(struct Q) + sizeof(union U) + sizeof(int[7]) + sizeof(short) + sizeof(char *);
    {
        int (*tab[2])(int) = { inc, sq };
        h = h * 5 + tab[0](7) + tab[1](7);
    }
    return h;
}
