// expect: 97281181
typedef unsigned char u8; typedef unsigned short u16; typedef unsigned int u32;
enum { F_A = 1, F_B = 2, F_C = 4, F_D = 8 };
typedef struct { u8 kind; union { int i; struct { short lo, hi; } s; char c; } u; } item;
static item items[5];
static u32 flags;
static int classify(item *it) {
    switch (it->kind) {
        case 0: return it->u.i;
        case 1: return it->u.s.lo * 100 + it->u.s.hi;
        default: return it->u.c;
    }
}
int main(void) {
    int i, h = 0;
    for (i = 0; i < 5; i++) { items[i].kind = i % 3; if (i % 3 == 0) items[i].u.i = i * 1000; else if (i % 3 == 1) { items[i].u.s.lo = i; items[i].u.s.hi = -i; } else items[i].u.c = 'a' + i; }
    for (i = 0; i < 5; i++) h = h * 31 + classify(&items[i]);
    flags |= F_A | F_C; flags &= ~F_A; flags ^= F_D;
    h = h * 31 + flags + ((flags & F_C) != 0) + ((flags & F_B) != 0);
    h += sizeof(item) * 1000 + sizeof(flags);
    return h;
}
