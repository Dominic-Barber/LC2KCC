// expect: 30412
static int f10(int a, int b, int c, int d, int e, int f, int g, int h, int i, int j) { return a + 2*b + 3*c + 4*d + 5*e + 6*f + 7*g + 8*h + 9*i + 10*j; }
static int g3(int x, int y, int z) { return x * y - z; }
static int deep(int a) { return g3(a, g3(a + 1, g3(a + 2, a + 3, a + 4), a + 5), g3(a + 6, a + 7, g3(a + 8, a + 9, a + 10))); }
static int nested(int a, int b) { return f10(a, g3(a, b, 1), deep(b), a - b, g3(b, b, b), deep(a), a * b, 7, g3(1, 2, 3), deep(3) + a); }
int main(void) {
    int x = 3, y = 5;
    return nested(x, y) * 3 + deep(2) + f10(1,2,3,4,5,6,7,8,9,10) + (x + f10(x,x,x,x,x,x,x,x,x,x) * (y + g3(x, y, 2)));
}
