// expect: 11103
typedef _Bool boolean;
int g[3];
boolean f(int x) { return x; }
int main(void) {
    boolean a = 256, b = 0, c = -1, d = g;
    int h = a * 1 + b * 10 + c * 100 + d * 1000 + f(512) * 10000 + f(0) * 100000;
    boolean arr[3] = { 5, 0, 7 };
    h += arr[0] + arr[1] + arr[2];
    return h;
}
