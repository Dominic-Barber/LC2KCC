// expect: -75610814
long long g = 5000000000LL;
unsigned long long ug = 0xfedcba9876543210ULL;
long long arr[3] = { 1, -2, 0x100000000LL };
long long f(long long a, int b) { return a * b + (a >> 3); }
int main(void) {
    long long a = 123456789012345LL, b = -987654321LL, c;
    unsigned long long u = 18446744073709551615ULL, v = 1000000007;
    int i, h = 0;
    c = a + b; h += (int)(c >> 20) + (int)c;
    c = a - b; h = h * 31 + (int)(c >> 7) + (int)(c >> 40);
    c = a * b; h = h * 31 + (int)c + (int)(c >> 32);
    c = a / 1000; h = h * 31 + (int)c;
    c = a % 1000003; h = h * 31 + (int)c;
    c = b / 7; h = h * 31 + (int)c;
    c = b % 7; h = h * 31 + (int)c;
    c = -b; h = h * 31 + (int)c;
    c = ~a; h = h * 31 + (int)(c >> 33);
    c = a & 0xffffffffLL; h = h * 31 + (int)c;
    c = a | 1; h = h * 31 + (int)c;
    c = a ^ b; h = h * 31 + (int)(c >> 5);
    c = a << 12; h = h * 31 + (int)(c >> 33);
    h = h * 31 + (a < b) + (a > b) * 2 + (a == b) * 4 + (a != b) * 8 + (a <= a) * 16 + (b >= a) * 32;
    h = h * 31 + (u > v) + (u / v == 18446743936ULL) * 2 + (int)(u % v) + (int)(u >> 60);
    h = h * 31 + (int)g + (int)(g >> 32) + (int)(ug >> 56) + (int)ug;
    for (i = 0; i < 3; i++) h = h * 31 + (int)arr[i] + (int)(arr[i] >> 32);
    h = h * 31 + (int)f(1000000LL, 3000) + (int)(f(1000000LL, 3000) >> 32);
    c = 0; for (i = 0; i < 40; i++) { c += i; c *= 3; if (c > 1000000000000LL) c -= 999999999999LL; }
    h = h * 31 + (int)c + (int)(c >> 32);
    c = 5; c++; ++c; c--; c += 10; c <<= 2; c -= 3; h = h * 31 + (int)c;
    h = h * 31 + (a ? 1 : 2) + (0LL ? 4 : 8) + sizeof(long long) + sizeof(arr) + (i == 40 && c);
    c = (a > b) ? a : b; h = h * 31 + (int)c;
    h = h * 31 + (int)(unsigned char)a + (int)(short)b + (int)(long long)i + (int)(unsigned long long)-1;
    return h;
}
