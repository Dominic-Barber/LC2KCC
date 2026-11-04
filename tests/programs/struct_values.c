// expect: 161823781
struct V { int x, y; };
struct Big { int a[12]; int tag; };
struct V add(struct V a, struct V b) { struct V r; r.x = a.x + b.x; r.y = a.y + b.y; return r; }
struct V mk(int x, int y) { struct V v = { x, y }; return v; }
struct Big bigf(struct Big b, int k) { int i; for (i = 0; i < 12; i++) b.a[i] += k; b.tag = k; return b; }
int sumv(struct V v) { return v.x * 10 + v.y; }
int main(void) {
    struct V a = mk(1, 2), b = { 10, 20 }, c;
    struct Big big, r2;
    int i, h = 0;
    c = add(a, b);
    h = sumv(c) + add(c, c).y + sumv(mk(7, 8));
    for (i = 0; i < 12; i++) big.a[i] = i * i;
    big.tag = 5;
    r2 = bigf(big, 100);
    for (i = 0; i < 12; i++) h = h * 3 + r2.a[i];
    h += r2.tag + big.tag + big.a[3];
    h += ((struct V){ 3, 4 }).y + ((int[]){ 5, 6, 7 })[2];
    return h;
}
