/*
 * lc2kcc runtime library, compiled with the user's program (only the
 * functions the program reaches are emitted). The code generator calls
 * these for `/` and `%`. It must not use `/` or `%`
 * itself.
 */

/* Restoring division, one quotient bit per iteration, MSB first. */
static unsigned int
__udivmod(unsigned int n, unsigned int d, unsigned int *rem)
{
    unsigned int q = 0, r = 0, top;
    int i;

    if (d == 0)
    {
        *rem = n;
        return 0xffffffffu;
    }
    for (i = 0; i < 32; i++)
    {
        top = r >> 31;
        r   = (r << 1) | (n >> 31);
        n <<= 1;
        q <<= 1;
        if (top || r >= d)
        {
            r -= d;
            q |= 1;
        }
    }
    *rem = r;
    return q;
}

unsigned int
__udiv(unsigned int n, unsigned int d)
{
    unsigned int r;
    return __udivmod(n, d, &r);
}

unsigned int
__umod(unsigned int n, unsigned int d)
{
    unsigned int r;
    __udivmod(n, d, &r);
    return r;
}

int
__sdiv(int n, int d)
{
    unsigned int un = n < 0 ? 0u - (unsigned int)n : (unsigned int)n;
    unsigned int ud = d < 0 ? 0u - (unsigned int)d : (unsigned int)d;
    unsigned int r;
    unsigned int q = __udivmod(un, ud, &r);
    return ((n < 0) != (d < 0)) ? (int)(0u - q) : (int)q;
}

int
__smod(int n, int d)
{
    unsigned int un = n < 0 ? 0u - (unsigned int)n : (unsigned int)n;
    unsigned int ud = d < 0 ? 0u - (unsigned int)d : (unsigned int)d;
    unsigned int r;
    __udivmod(un, ud, &r);
    return n < 0 ? (int)(0u - r) : (int)r;
}
