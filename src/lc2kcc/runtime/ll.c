/*
 * 64-bit integer support. The compiler lowers every `long long` operation to
 * a call of one of these, passing and returning a `struct ll` by value (low
 * word first). They must be written with 32-bit operations only.
 */

struct ll
{
    unsigned int lo, hi;
};

struct ll
__ll_add(struct ll a, struct ll b)
{
    struct ll r;
    r.lo = a.lo + b.lo;
    r.hi = a.hi + b.hi + (r.lo < a.lo);
    return r;
}

struct ll
__ll_sub(struct ll a, struct ll b)
{
    struct ll r;
    r.lo = a.lo - b.lo;
    r.hi = a.hi - b.hi - (a.lo < b.lo);
    return r;
}

struct ll
__ll_neg(struct ll a)
{
    struct ll r;
    r.lo = 0u - a.lo;
    r.hi = 0u - a.hi - (a.lo != 0);
    return r;
}

struct ll
__ll_not(struct ll a)
{
    struct ll r;
    r.lo = ~a.lo;
    r.hi = ~a.hi;
    return r;
}

struct ll
__ll_and(struct ll a, struct ll b)
{
    struct ll r;
    r.lo = a.lo & b.lo;
    r.hi = a.hi & b.hi;
    return r;
}

struct ll
__ll_or(struct ll a, struct ll b)
{
    struct ll r;
    r.lo = a.lo | b.lo;
    r.hi = a.hi | b.hi;
    return r;
}

struct ll
__ll_xor(struct ll a, struct ll b)
{
    struct ll r;
    r.lo = a.lo ^ b.lo;
    r.hi = a.hi ^ b.hi;
    return r;
}

struct ll
__ll_shl(struct ll a, int n)
{
    struct ll r;
    n &= 63;
    if (n == 0)
        return a;
    if (n < 32)
    {
        r.hi = (a.hi << n) | (a.lo >> (32 - n));
        r.lo = a.lo << n;
    }
    else
    {
        r.hi = a.lo << (n - 32);
        r.lo = 0;
    }
    return r;
}

struct ll
__ll_shru(struct ll a, int n)
{
    struct ll r;
    n &= 63;
    if (n == 0)
        return a;
    if (n < 32)
    {
        r.lo = (a.lo >> n) | (a.hi << (32 - n));
        r.hi = a.hi >> n;
    }
    else
    {
        r.lo = a.hi >> (n - 32);
        r.hi = 0;
    }
    return r;
}

struct ll
__ll_shrs(struct ll a, int n)
{
    struct ll r;
    n &= 63;
    if (n == 0)
        return a;
    if (n < 32)
    {
        r.lo = (a.lo >> n) | (a.hi << (32 - n));
        r.hi = (unsigned int)((int)a.hi >> n);
    }
    else
    {
        r.lo = (unsigned int)((int)a.hi >> (n - 32));
        r.hi = (unsigned int)((int)a.hi >> 31);
    }
    return r;
}

/* 32 x 32 -> 64 multiply from 16-bit pieces */
static void
mul32(unsigned int a, unsigned int b, unsigned int *hi, unsigned int *lo)
{
    unsigned int a0 = a & 0xffff, a1 = a >> 16, b0 = b & 0xffff, b1 = b >> 16;
    unsigned int p00 = a0 * b0, p01 = a0 * b1, p10 = a1 * b0, p11 = a1 * b1;
    unsigned int mid = (p00 >> 16) + (p01 & 0xffff) + (p10 & 0xffff);
    *lo = (p00 & 0xffff) | (mid << 16);
    *hi = p11 + (p01 >> 16) + (p10 >> 16) + (mid >> 16);
}

struct ll
__ll_mul(struct ll a, struct ll b)
{
    struct ll    r;
    unsigned int hi, lo;
    mul32(a.lo, b.lo, &hi, &lo);
    r.lo = lo;
    r.hi = hi + a.lo * b.hi + a.hi * b.lo;
    return r;
}

/* Restoring division, one quotient bit per iteration. */
static struct ll
udivmod64(struct ll n, struct ll d, struct ll *rem)
{
    struct ll    q;
    unsigned int rh = 0, rl = 0, top, borrow;
    int          i;
    q.lo = 0;
    q.hi = 0;
    if (d.lo == 0 && d.hi == 0)
    {
        *rem = n;
        q.lo = 0xffffffffu;
        q.hi = 0xffffffffu;
        return q;
    }
    for (i = 0; i < 64; i++)
    {
        top = rh >> 31;
        rh  = (rh << 1) | (rl >> 31);
        rl  = (rl << 1) | (n.hi >> 31);
        n.hi = (n.hi << 1) | (n.lo >> 31);
        n.lo <<= 1;
        q.hi = (q.hi << 1) | (q.lo >> 31);
        q.lo <<= 1;
        if (top || rh > d.hi || (rh == d.hi && rl >= d.lo))
        {
            borrow = rl < d.lo;
            rl -= d.lo;
            rh = rh - d.hi - borrow;
            q.lo |= 1;
        }
    }
    rem->lo = rl;
    rem->hi = rh;
    return q;
}

struct ll
__ll_udiv(struct ll a, struct ll b)
{
    struct ll r;
    return udivmod64(a, b, &r);
}

struct ll
__ll_umod(struct ll a, struct ll b)
{
    struct ll r;
    udivmod64(a, b, &r);
    return r;
}

static int
negative(struct ll a)
{
    return (int)a.hi < 0;
}

struct ll
__ll_sdiv(struct ll a, struct ll b)
{
    struct ll r, q;
    int       neg = negative(a) != negative(b);
    if (negative(a))
        a = __ll_neg(a);
    if (negative(b))
        b = __ll_neg(b);
    q = udivmod64(a, b, &r);
    return neg ? __ll_neg(q) : q;
}

struct ll
__ll_smod(struct ll a, struct ll b)
{
    struct ll r;
    int       neg = negative(a);
    if (negative(a))
        a = __ll_neg(a);
    if (negative(b))
        b = __ll_neg(b);
    udivmod64(a, b, &r);
    return neg ? __ll_neg(r) : r;
}

int
__ll_cmps(struct ll a, struct ll b)
{
    if (a.hi != b.hi)
        return (int)a.hi < (int)b.hi ? -1 : 1;
    if (a.lo != b.lo)
        return a.lo < b.lo ? -1 : 1;
    return 0;
}

int
__ll_cmpu(struct ll a, struct ll b)
{
    if (a.hi != b.hi)
        return a.hi < b.hi ? -1 : 1;
    if (a.lo != b.lo)
        return a.lo < b.lo ? -1 : 1;
    return 0;
}

int
__ll_ne0(struct ll a)
{
    return (a.lo | a.hi) != 0;
}
