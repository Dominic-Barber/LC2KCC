// expect: 1050426691
static int popcount(unsigned x) { int c = 0; while (x) { x &= x - 1; c++; } return c; }
static unsigned rotl(unsigned x, int n) { return (x << n) | (x >> (32 - n)); }
static unsigned rev(unsigned x) { unsigned r = 0; int i; for (i = 0; i < 32; i++) { r = (r << 1) | (x & 1); x >>= 1; } return r; }
static unsigned crc32(const unsigned char *p, int n) {
    unsigned crc = 0xffffffffu; int i, j;
    for (i = 0; i < n; i++) { crc ^= p[i]; for (j = 0; j < 8; j++) crc = (crc >> 1) ^ (0xEDB88320u & -(crc & 1)); }
    return ~crc;
}
static int clz(unsigned x) { int n = 0; if (!x) return 32; while (!(x & 0x80000000u)) { x <<= 1; n++; } return n; }
unsigned char msg[] = "The quick brown fox jumps over the lazy dog";
int main(void) {
    unsigned h = 7;
    h = h * 31 + popcount(0xdeadbeefu) + popcount(0) + popcount(0xffffffffu);
    h = h * 31 + rotl(0x12345678u, 5) + rotl(0x80000001u, 1) + rotl(1, 31);
    h = h * 31 + rev(0x12345678u) + rev(1);
    h = h * 31 + crc32(msg, 43) + clz(1) + clz(0x00ff0000u) + clz(0);
    h = h * 31 + (0x80000000u >> 31) + (0xf0f0f0f0u >> 4) + ((int)0x80000000 >> 4) + (-1 >> 7);
    return (int)h;
}
