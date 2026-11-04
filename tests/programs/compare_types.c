// expect: 2082632017
/* generated: every relational operator over mixed types and boundary values */
static int v0[] = { (int)(0), (int)(1), (int)(-1), (int)(2), (int)(-2), (int)(127), (int)(128), (int)(255), (int)(256), (int)(32767), (int)(32768), (int)(65535), (int)(65536), (int)(2147483647), (int)(-2147483647-1), (int)(4294967295u), (int)(100000), (int)(-100000) };
static unsigned v1[] = { (unsigned)(0), (unsigned)(1), (unsigned)(-1), (unsigned)(2), (unsigned)(-2), (unsigned)(127), (unsigned)(128), (unsigned)(255), (unsigned)(256), (unsigned)(32767), (unsigned)(32768), (unsigned)(65535), (unsigned)(65536), (unsigned)(2147483647), (unsigned)(-2147483647-1), (unsigned)(4294967295u), (unsigned)(100000), (unsigned)(-100000) };
static short v2[] = { (short)(0), (short)(1), (short)(-1), (short)(2), (short)(-2), (short)(127), (short)(128), (short)(255), (short)(256), (short)(32767), (short)(32768), (short)(65535), (short)(65536), (short)(2147483647), (short)(-2147483647-1), (short)(4294967295u), (short)(100000), (short)(-100000) };
static unsigned short v3[] = { (unsigned short)(0), (unsigned short)(1), (unsigned short)(-1), (unsigned short)(2), (unsigned short)(-2), (unsigned short)(127), (unsigned short)(128), (unsigned short)(255), (unsigned short)(256), (unsigned short)(32767), (unsigned short)(32768), (unsigned short)(65535), (unsigned short)(65536), (unsigned short)(2147483647), (unsigned short)(-2147483647-1), (unsigned short)(4294967295u), (unsigned short)(100000), (unsigned short)(-100000) };
static signed char v4[] = { (signed char)(0), (signed char)(1), (signed char)(-1), (signed char)(2), (signed char)(-2), (signed char)(127), (signed char)(128), (signed char)(255), (signed char)(256), (signed char)(32767), (signed char)(32768), (signed char)(65535), (signed char)(65536), (signed char)(2147483647), (signed char)(-2147483647-1), (signed char)(4294967295u), (signed char)(100000), (signed char)(-100000) };
static unsigned char v5[] = { (unsigned char)(0), (unsigned char)(1), (unsigned char)(-1), (unsigned char)(2), (unsigned char)(-2), (unsigned char)(127), (unsigned char)(128), (unsigned char)(255), (unsigned char)(256), (unsigned char)(32767), (unsigned char)(32768), (unsigned char)(65535), (unsigned char)(65536), (unsigned char)(2147483647), (unsigned char)(-2147483647-1), (unsigned char)(4294967295u), (unsigned char)(100000), (unsigned char)(-100000) };
static int mask(int a, int b, int c, int d, int e, int f) { return a | b << 1 | c << 2 | d << 3 | e << 4 | f << 5; }
static int c00(int a, int b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c01(int a, unsigned b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c02(int a, short b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c03(int a, unsigned short b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c04(int a, signed char b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c05(int a, unsigned char b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c10(unsigned a, int b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c11(unsigned a, unsigned b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c12(unsigned a, short b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c13(unsigned a, unsigned short b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c14(unsigned a, signed char b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c15(unsigned a, unsigned char b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c20(short a, int b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c21(short a, unsigned b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c22(short a, short b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c23(short a, unsigned short b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c24(short a, signed char b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c25(short a, unsigned char b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c30(unsigned short a, int b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c31(unsigned short a, unsigned b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c32(unsigned short a, short b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c33(unsigned short a, unsigned short b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c34(unsigned short a, signed char b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c35(unsigned short a, unsigned char b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c40(signed char a, int b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c41(signed char a, unsigned b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c42(signed char a, short b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c43(signed char a, unsigned short b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c44(signed char a, signed char b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c45(signed char a, unsigned char b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c50(unsigned char a, int b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c51(unsigned char a, unsigned b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c52(unsigned char a, short b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c53(unsigned char a, unsigned short b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c54(unsigned char a, signed char b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
static int c55(unsigned char a, unsigned char b) { return mask(a < b, a <= b, a > b, a >= b, a == b, a != b); }
int main(void) {
    int i, j, h = 0;
    int n = 18;
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c00(v0[i], v0[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c01(v0[i], v1[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c02(v0[i], v2[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c03(v0[i], v3[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c04(v0[i], v4[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c05(v0[i], v5[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c10(v1[i], v0[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c11(v1[i], v1[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c12(v1[i], v2[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c13(v1[i], v3[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c14(v1[i], v4[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c15(v1[i], v5[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c20(v2[i], v0[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c21(v2[i], v1[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c22(v2[i], v2[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c23(v2[i], v3[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c24(v2[i], v4[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c25(v2[i], v5[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c30(v3[i], v0[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c31(v3[i], v1[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c32(v3[i], v2[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c33(v3[i], v3[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c34(v3[i], v4[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c35(v3[i], v5[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c40(v4[i], v0[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c41(v4[i], v1[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c42(v4[i], v2[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c43(v4[i], v3[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c44(v4[i], v4[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c45(v4[i], v5[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c50(v5[i], v0[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c51(v5[i], v1[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c52(v5[i], v2[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c53(v5[i], v3[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c54(v5[i], v4[j]);
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) h = h * 31 + c55(v5[i], v5[j]);
    for (i = 0; i < n; i++) {
        h = h * 31 + mask(v0[i] < 0, v0[i] <= 0, v0[i] > 0, v0[i] >= 0, 0 < v0[i], 0 >= v0[i]);
        h = h * 31 + mask(v0[i] < 1, v0[i] <= 1, v0[i] > 1, v0[i] >= 1, 1 < v0[i], 1 >= v0[i]);
        h = h * 31 + mask(v0[i] < -1, v0[i] <= -1, v0[i] > -1, v0[i] >= -1, -1 < v0[i], -1 >= v0[i]);
        h = h * 31 + mask(v0[i] < 255, v0[i] <= 255, v0[i] > 255, v0[i] >= 255, 255 < v0[i], 255 >= v0[i]);
        h = h * 31 + mask(v0[i] < 256, v0[i] <= 256, v0[i] > 256, v0[i] >= 256, 256 < v0[i], 256 >= v0[i]);
        h = h * 31 + mask(v0[i] < 32768, v0[i] <= 32768, v0[i] > 32768, v0[i] >= 32768, 32768 < v0[i], 32768 >= v0[i]);
        h = h * 31 + mask(v0[i] < 65535, v0[i] <= 65535, v0[i] > 65535, v0[i] >= 65535, 65535 < v0[i], 65535 >= v0[i]);
        h = h * 31 + mask(v0[i] < 2147483647, v0[i] <= 2147483647, v0[i] > 2147483647, v0[i] >= 2147483647, 2147483647 < v0[i], 2147483647 >= v0[i]);
        h = h * 31 + mask(v0[i] < -2147483647-1, v0[i] <= -2147483647-1, v0[i] > -2147483647-1, v0[i] >= -2147483647-1, -2147483647-1 < v0[i], -2147483647-1 >= v0[i]);
        h = h * 31 + mask(v0[i] < 0u, v0[i] <= 0u, v0[i] > 0u, v0[i] >= 0u, 0u < v0[i], 0u >= v0[i]);
        h = h * 31 + mask(v0[i] < 4294967295u, v0[i] <= 4294967295u, v0[i] > 4294967295u, v0[i] >= 4294967295u, 4294967295u < v0[i], 4294967295u >= v0[i]);
        h = h * 31 + mask(v1[i] < 0, v1[i] <= 0, v1[i] > 0, v1[i] >= 0, 0 < v1[i], 0 >= v1[i]);
        h = h * 31 + mask(v1[i] < 1, v1[i] <= 1, v1[i] > 1, v1[i] >= 1, 1 < v1[i], 1 >= v1[i]);
        h = h * 31 + mask(v1[i] < -1, v1[i] <= -1, v1[i] > -1, v1[i] >= -1, -1 < v1[i], -1 >= v1[i]);
        h = h * 31 + mask(v1[i] < 255, v1[i] <= 255, v1[i] > 255, v1[i] >= 255, 255 < v1[i], 255 >= v1[i]);
        h = h * 31 + mask(v1[i] < 256, v1[i] <= 256, v1[i] > 256, v1[i] >= 256, 256 < v1[i], 256 >= v1[i]);
        h = h * 31 + mask(v1[i] < 32768, v1[i] <= 32768, v1[i] > 32768, v1[i] >= 32768, 32768 < v1[i], 32768 >= v1[i]);
        h = h * 31 + mask(v1[i] < 65535, v1[i] <= 65535, v1[i] > 65535, v1[i] >= 65535, 65535 < v1[i], 65535 >= v1[i]);
        h = h * 31 + mask(v1[i] < 2147483647, v1[i] <= 2147483647, v1[i] > 2147483647, v1[i] >= 2147483647, 2147483647 < v1[i], 2147483647 >= v1[i]);
        h = h * 31 + mask(v1[i] < -2147483647-1, v1[i] <= -2147483647-1, v1[i] > -2147483647-1, v1[i] >= -2147483647-1, -2147483647-1 < v1[i], -2147483647-1 >= v1[i]);
        h = h * 31 + mask(v1[i] < 0u, v1[i] <= 0u, v1[i] > 0u, v1[i] >= 0u, 0u < v1[i], 0u >= v1[i]);
        h = h * 31 + mask(v1[i] < 4294967295u, v1[i] <= 4294967295u, v1[i] > 4294967295u, v1[i] >= 4294967295u, 4294967295u < v1[i], 4294967295u >= v1[i]);
        h = h * 31 + mask(v2[i] < 0, v2[i] <= 0, v2[i] > 0, v2[i] >= 0, 0 < v2[i], 0 >= v2[i]);
        h = h * 31 + mask(v2[i] < 1, v2[i] <= 1, v2[i] > 1, v2[i] >= 1, 1 < v2[i], 1 >= v2[i]);
        h = h * 31 + mask(v2[i] < -1, v2[i] <= -1, v2[i] > -1, v2[i] >= -1, -1 < v2[i], -1 >= v2[i]);
        h = h * 31 + mask(v2[i] < 255, v2[i] <= 255, v2[i] > 255, v2[i] >= 255, 255 < v2[i], 255 >= v2[i]);
        h = h * 31 + mask(v2[i] < 256, v2[i] <= 256, v2[i] > 256, v2[i] >= 256, 256 < v2[i], 256 >= v2[i]);
        h = h * 31 + mask(v2[i] < 32768, v2[i] <= 32768, v2[i] > 32768, v2[i] >= 32768, 32768 < v2[i], 32768 >= v2[i]);
        h = h * 31 + mask(v2[i] < 65535, v2[i] <= 65535, v2[i] > 65535, v2[i] >= 65535, 65535 < v2[i], 65535 >= v2[i]);
        h = h * 31 + mask(v2[i] < 2147483647, v2[i] <= 2147483647, v2[i] > 2147483647, v2[i] >= 2147483647, 2147483647 < v2[i], 2147483647 >= v2[i]);
        h = h * 31 + mask(v2[i] < -2147483647-1, v2[i] <= -2147483647-1, v2[i] > -2147483647-1, v2[i] >= -2147483647-1, -2147483647-1 < v2[i], -2147483647-1 >= v2[i]);
        h = h * 31 + mask(v2[i] < 0u, v2[i] <= 0u, v2[i] > 0u, v2[i] >= 0u, 0u < v2[i], 0u >= v2[i]);
        h = h * 31 + mask(v2[i] < 4294967295u, v2[i] <= 4294967295u, v2[i] > 4294967295u, v2[i] >= 4294967295u, 4294967295u < v2[i], 4294967295u >= v2[i]);
        h = h * 31 + mask(v3[i] < 0, v3[i] <= 0, v3[i] > 0, v3[i] >= 0, 0 < v3[i], 0 >= v3[i]);
        h = h * 31 + mask(v3[i] < 1, v3[i] <= 1, v3[i] > 1, v3[i] >= 1, 1 < v3[i], 1 >= v3[i]);
        h = h * 31 + mask(v3[i] < -1, v3[i] <= -1, v3[i] > -1, v3[i] >= -1, -1 < v3[i], -1 >= v3[i]);
        h = h * 31 + mask(v3[i] < 255, v3[i] <= 255, v3[i] > 255, v3[i] >= 255, 255 < v3[i], 255 >= v3[i]);
        h = h * 31 + mask(v3[i] < 256, v3[i] <= 256, v3[i] > 256, v3[i] >= 256, 256 < v3[i], 256 >= v3[i]);
        h = h * 31 + mask(v3[i] < 32768, v3[i] <= 32768, v3[i] > 32768, v3[i] >= 32768, 32768 < v3[i], 32768 >= v3[i]);
        h = h * 31 + mask(v3[i] < 65535, v3[i] <= 65535, v3[i] > 65535, v3[i] >= 65535, 65535 < v3[i], 65535 >= v3[i]);
        h = h * 31 + mask(v3[i] < 2147483647, v3[i] <= 2147483647, v3[i] > 2147483647, v3[i] >= 2147483647, 2147483647 < v3[i], 2147483647 >= v3[i]);
        h = h * 31 + mask(v3[i] < -2147483647-1, v3[i] <= -2147483647-1, v3[i] > -2147483647-1, v3[i] >= -2147483647-1, -2147483647-1 < v3[i], -2147483647-1 >= v3[i]);
        h = h * 31 + mask(v3[i] < 0u, v3[i] <= 0u, v3[i] > 0u, v3[i] >= 0u, 0u < v3[i], 0u >= v3[i]);
        h = h * 31 + mask(v3[i] < 4294967295u, v3[i] <= 4294967295u, v3[i] > 4294967295u, v3[i] >= 4294967295u, 4294967295u < v3[i], 4294967295u >= v3[i]);
        h = h * 31 + mask(v4[i] < 0, v4[i] <= 0, v4[i] > 0, v4[i] >= 0, 0 < v4[i], 0 >= v4[i]);
        h = h * 31 + mask(v4[i] < 1, v4[i] <= 1, v4[i] > 1, v4[i] >= 1, 1 < v4[i], 1 >= v4[i]);
        h = h * 31 + mask(v4[i] < -1, v4[i] <= -1, v4[i] > -1, v4[i] >= -1, -1 < v4[i], -1 >= v4[i]);
        h = h * 31 + mask(v4[i] < 255, v4[i] <= 255, v4[i] > 255, v4[i] >= 255, 255 < v4[i], 255 >= v4[i]);
        h = h * 31 + mask(v4[i] < 256, v4[i] <= 256, v4[i] > 256, v4[i] >= 256, 256 < v4[i], 256 >= v4[i]);
        h = h * 31 + mask(v4[i] < 32768, v4[i] <= 32768, v4[i] > 32768, v4[i] >= 32768, 32768 < v4[i], 32768 >= v4[i]);
        h = h * 31 + mask(v4[i] < 65535, v4[i] <= 65535, v4[i] > 65535, v4[i] >= 65535, 65535 < v4[i], 65535 >= v4[i]);
        h = h * 31 + mask(v4[i] < 2147483647, v4[i] <= 2147483647, v4[i] > 2147483647, v4[i] >= 2147483647, 2147483647 < v4[i], 2147483647 >= v4[i]);
        h = h * 31 + mask(v4[i] < -2147483647-1, v4[i] <= -2147483647-1, v4[i] > -2147483647-1, v4[i] >= -2147483647-1, -2147483647-1 < v4[i], -2147483647-1 >= v4[i]);
        h = h * 31 + mask(v4[i] < 0u, v4[i] <= 0u, v4[i] > 0u, v4[i] >= 0u, 0u < v4[i], 0u >= v4[i]);
        h = h * 31 + mask(v4[i] < 4294967295u, v4[i] <= 4294967295u, v4[i] > 4294967295u, v4[i] >= 4294967295u, 4294967295u < v4[i], 4294967295u >= v4[i]);
        h = h * 31 + mask(v5[i] < 0, v5[i] <= 0, v5[i] > 0, v5[i] >= 0, 0 < v5[i], 0 >= v5[i]);
        h = h * 31 + mask(v5[i] < 1, v5[i] <= 1, v5[i] > 1, v5[i] >= 1, 1 < v5[i], 1 >= v5[i]);
        h = h * 31 + mask(v5[i] < -1, v5[i] <= -1, v5[i] > -1, v5[i] >= -1, -1 < v5[i], -1 >= v5[i]);
        h = h * 31 + mask(v5[i] < 255, v5[i] <= 255, v5[i] > 255, v5[i] >= 255, 255 < v5[i], 255 >= v5[i]);
        h = h * 31 + mask(v5[i] < 256, v5[i] <= 256, v5[i] > 256, v5[i] >= 256, 256 < v5[i], 256 >= v5[i]);
        h = h * 31 + mask(v5[i] < 32768, v5[i] <= 32768, v5[i] > 32768, v5[i] >= 32768, 32768 < v5[i], 32768 >= v5[i]);
        h = h * 31 + mask(v5[i] < 65535, v5[i] <= 65535, v5[i] > 65535, v5[i] >= 65535, 65535 < v5[i], 65535 >= v5[i]);
        h = h * 31 + mask(v5[i] < 2147483647, v5[i] <= 2147483647, v5[i] > 2147483647, v5[i] >= 2147483647, 2147483647 < v5[i], 2147483647 >= v5[i]);
        h = h * 31 + mask(v5[i] < -2147483647-1, v5[i] <= -2147483647-1, v5[i] > -2147483647-1, v5[i] >= -2147483647-1, -2147483647-1 < v5[i], -2147483647-1 >= v5[i]);
        h = h * 31 + mask(v5[i] < 0u, v5[i] <= 0u, v5[i] > 0u, v5[i] >= 0u, 0u < v5[i], 0u >= v5[i]);
        h = h * 31 + mask(v5[i] < 4294967295u, v5[i] <= 4294967295u, v5[i] > 4294967295u, v5[i] >= 4294967295u, 4294967295u < v5[i], 4294967295u >= v5[i]);
    }
    return h;
}
