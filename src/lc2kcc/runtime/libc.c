/*
 * Freestanding C library subset for lc2kcc. Compiled with every program;
 * only the functions a program reaches are emitted, and a program may
 * define its own version of any of them (these are weak).
 */
#include <stdarg.h>
#include <stddef.h>

void *
memcpy(void *dst, const void *src, size_t n)
{
    char       *d = dst;
    const char *s = src;
    while (n != 0)
    {
        *d++ = *s++;
        n--;
    }
    return dst;
}

void *
memmove(void *dst, const void *src, size_t n)
{
    char       *d = dst;
    const char *s = src;
    if (d < s)
    {
        while (n != 0)
        {
            *d++ = *s++;
            n--;
        }
    }
    else
    {
        d += n;
        s += n;
        while (n != 0)
        {
            *--d = *--s;
            n--;
        }
    }
    return dst;
}

void *
memset(void *dst, int c, size_t n)
{
    char *d = dst;
    while (n != 0)
    {
        *d++ = (char)c;
        n--;
    }
    return dst;
}

int
memcmp(const void *a, const void *b, size_t n)
{
    const unsigned char *x = a, *y = b;
    while (n != 0)
    {
        if (*x != *y)
            return *x - *y;
        x++;
        y++;
        n--;
    }
    return 0;
}

size_t
strlen(const char *s)
{
    const char *p = s;
    while (*p != 0)
        p++;
    return (size_t)(p - s);
}

char *
strcpy(char *dst, const char *src)
{
    char *d = dst;
    while ((*d++ = *src++) != 0)
        ;
    return dst;
}

char *
strncpy(char *dst, const char *src, size_t n)
{
    size_t i = 0;
    while (i < n && src[i] != 0)
    {
        dst[i] = src[i];
        i++;
    }
    while (i < n)
        dst[i++] = 0;
    return dst;
}

char *
strcat(char *dst, const char *src)
{
    strcpy(dst + strlen(dst), src);
    return dst;
}

int
strcmp(const char *a, const char *b)
{
    while (*a != 0 && *a == *b)
    {
        a++;
        b++;
    }
    return (unsigned char)*a - (unsigned char)*b;
}

int
strncmp(const char *a, const char *b, size_t n)
{
    while (n != 0 && *a != 0 && *a == *b)
    {
        a++;
        b++;
        n--;
    }
    return n == 0 ? 0 : (unsigned char)*a - (unsigned char)*b;
}

char *
strchr(const char *s, int c)
{
    while (*s != (char)c)
    {
        if (*s == 0)
            return 0;
        s++;
    }
    return (char *)s;
}

char *
strrchr(const char *s, int c)
{
    const char *last = 0;
    do
    {
        if (*s == (char)c)
            last = s;
    } while (*s++ != 0);
    return (char *)last;
}

int
abs(int x)
{
    return x < 0 ? -x : x;
}

long
labs(long x)
{
    return x < 0 ? -x : x;
}

int
atoi(const char *s)
{
    int n = 0, neg = 0;
    while (*s == ' ' || (*s >= 9 && *s <= 13))
        s++;
    if (*s == '-' || *s == '+')
        neg = *s++ == '-';
    while (*s >= '0' && *s <= '9')
        n = n * 10 + (*s++ - '0');
    return neg ? -n : n;
}

long
atol(const char *s)
{
    return atoi(s);
}

static unsigned int rand_state = 1;

void
srand(unsigned int seed)
{
    rand_state = seed;
}

int
rand(void)
{
    rand_state = rand_state * 1103515245u + 12345u;
    return (int)((rand_state >> 16) & 0x7fff);
}

static void
swap_items(char *a, char *b, size_t size)
{
    while (size != 0)
    {
        char t = *a;
        *a++   = *b;
        *b++   = t;
        size--;
    }
}

/* Shell sort: no recursion, no allocation. */
void
qsort(void *base, size_t n, size_t size, int (*cmp)(const void *, const void *))
{
    char  *b = base;
    size_t gap, i, j;
    for (gap = n / 2; gap > 0; gap /= 2)
        for (i = gap; i < n; i++)
            for (j = i; j >= gap && cmp(b + (j - gap) * size, b + j * size) > 0; j -= gap)
                swap_items(b + (j - gap) * size, b + j * size, size);
}

void *
bsearch(const void *key, const void *base, size_t n, size_t size, int (*cmp)(const void *, const void *))
{
    const char *b = base;
    size_t      lo = 0, hi = n;
    while (lo < hi)
    {
        size_t mid = lo + (hi - lo) / 2;
        int    c   = cmp(key, b + mid * size);
        if (c == 0)
            return (void *)(b + mid * size);
        if (c < 0)
            hi = mid;
        else
            lo = mid + 1;
    }
    return 0;
}

int
isdigit(int c)
{
    return c >= '0' && c <= '9';
}

int
isxdigit(int c)
{
    return isdigit(c) || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
}

int
isupper(int c)
{
    return c >= 'A' && c <= 'Z';
}

int
islower(int c)
{
    return c >= 'a' && c <= 'z';
}

int
isalpha(int c)
{
    return isupper(c) || islower(c);
}

int
isalnum(int c)
{
    return isalpha(c) || isdigit(c);
}

int
isspace(int c)
{
    return c == ' ' || (c >= 9 && c <= 13);
}

int
isprint(int c)
{
    return c >= 32 && c < 127;
}

int
ispunct(int c)
{
    return isprint(c) && c != ' ' && !isalnum(c);
}

int
toupper(int c)
{
    return islower(c) ? c - 32 : c;
}

int
tolower(int c)
{
    return isupper(c) ? c + 32 : c;
}

/* ---- formatted output ---- */

#define STDOUT_SIZE 2048
char         __stdout[STDOUT_SIZE];
unsigned int __stdout_len;

struct fmt_out
{
    char  *buf;
    size_t cap; /* writable characters, not counting the terminator */
    size_t len; /* characters produced, even beyond cap */
};

static void
out_char(struct fmt_out *o, char c)
{
    if (o->len < o->cap)
        o->buf[o->len] = c;
    o->len++;
}

static void
out_number(struct fmt_out *o, unsigned int value, unsigned int base, int upper, int width, int left, char pad, char sign)
{
    char digits[12];
    int  n = 0, total;
    do
    {
        unsigned int d = value % base;
        digits[n++]    = (char)(d < 10 ? '0' + d : (upper ? 'A' : 'a') + (d - 10));
        value /= base;
    } while (value != 0);
    total = n + (sign != 0);
    if (!left && pad == ' ')
        while (width > total)
        {
            out_char(o, ' ');
            width--;
        }
    if (sign != 0)
        out_char(o, sign);
    if (!left && pad == '0')
        while (width > total)
        {
            out_char(o, '0');
            width--;
        }
    while (n > 0)
        out_char(o, digits[--n]);
    if (left)
        while (width > total)
        {
            out_char(o, ' ');
            width--;
        }
}

static void
out_number64(struct fmt_out *o, unsigned long long value, unsigned int base, int upper, int width, int left, char pad, char sign)
{
    char digits[24];
    int  n = 0, total;
    do
    {
        unsigned int d = (unsigned int)(value % base);
        digits[n++]    = (char)(d < 10 ? '0' + d : (upper ? 'A' : 'a') + (d - 10));
        value /= base;
    } while (value != 0);
    total = n + (sign != 0);
    if (!left && pad == ' ')
        while (width > total)
        {
            out_char(o, ' ');
            width--;
        }
    if (sign != 0)
        out_char(o, sign);
    if (!left && pad == '0')
        while (width > total)
        {
            out_char(o, '0');
            width--;
        }
    while (n > 0)
        out_char(o, digits[--n]);
    if (left)
        while (width > total)
        {
            out_char(o, ' ');
            width--;
        }
}

int
vsnprintf(char *out, size_t cap, const char *fmt, va_list ap)
{
    struct fmt_out o;
    o.buf = out;
    o.cap = cap > 0 ? cap - 1 : 0;
    o.len = 0;
    while (*fmt != 0)
    {
        char c = *fmt++;
        int  left = 0, width = 0, longs;
        char pad = ' ';
        if (c != '%')
        {
            out_char(&o, c);
            continue;
        }
        for (;; fmt++)
        {
            if (*fmt == '-')
                left = 1;
            else if (*fmt == '0')
                pad = '0';
            else
                break;
        }
        while (*fmt >= '0' && *fmt <= '9')
            width = width * 10 + (*fmt++ - '0');
        longs = 0;
        while (*fmt == 'l' || *fmt == 'h')
            longs += *fmt++ == 'l';
        c = *fmt++;
        if (longs >= 2 && (c == 'd' || c == 'i' || c == 'u' || c == 'x' || c == 'X'))
        {
            unsigned long long v = va_arg(ap, unsigned long long);
            if ((c == 'd' || c == 'i') && (long long)v < 0)
                out_number64(&o, 0ull - v, 10, 0, width, left, pad, '-');
            else
                out_number64(&o, v, (c == 'x' || c == 'X') ? 16 : 10, c == 'X', width, left, pad, 0);
        }
        else if (c == 'd' || c == 'i')
        {
            int v = va_arg(ap, int);
            if (v < 0)
                out_number(&o, 0u - (unsigned int)v, 10, 0, width, left, pad, '-');
            else
                out_number(&o, (unsigned int)v, 10, 0, width, left, pad, 0);
        }
        else if (c == 'u')
            out_number(&o, va_arg(ap, unsigned int), 10, 0, width, left, pad, 0);
        else if (c == 'x' || c == 'X' || c == 'p')
            out_number(&o, va_arg(ap, unsigned int), 16, c == 'X', width, left, pad, 0);
        else if (c == 'c')
            out_char(&o, (char)va_arg(ap, int));
        else if (c == 's')
        {
            const char *s = va_arg(ap, const char *);
            int         n = (int)strlen(s);
            if (!left)
                while (width > n)
                {
                    out_char(&o, ' ');
                    width--;
                }
            while (*s != 0)
                out_char(&o, *s++);
            if (left)
                while (width > n)
                {
                    out_char(&o, ' ');
                    width--;
                }
        }
        else if (c == '%')
            out_char(&o, '%');
        else if (c == 0)
            break;
        else
            out_char(&o, c);
    }
    if (cap > 0)
        out[o.len < o.cap ? o.len : o.cap] = 0;
    return (int)o.len;
}

int
snprintf(char *out, size_t cap, const char *fmt, ...)
{
    va_list ap;
    int     n;
    va_start(ap, fmt);
    n = vsnprintf(out, cap, fmt, ap);
    va_end(ap);
    return n;
}

int
sprintf(char *out, const char *fmt, ...)
{
    va_list ap;
    int     n;
    va_start(ap, fmt);
    n = vsnprintf(out, 0x7fffffff, fmt, ap);
    va_end(ap);
    return n;
}

int
printf(const char *fmt, ...)
{
    va_list ap;
    int     n = 0;
    va_start(ap, fmt);
    if (__stdout_len < STDOUT_SIZE - 1)
    {
        n = vsnprintf(__stdout + __stdout_len, STDOUT_SIZE - __stdout_len, fmt, ap);
        __stdout_len += n < STDOUT_SIZE - 1 - __stdout_len ? n : STDOUT_SIZE - 1 - __stdout_len;
    }
    va_end(ap);
    return n;
}

int
putchar(int c)
{
    if (__stdout_len < STDOUT_SIZE - 1)
    {
        __stdout[__stdout_len++] = (char)c;
        __stdout[__stdout_len]   = 0;
    }
    return c;
}

int
puts(const char *s)
{
    while (*s != 0)
        putchar(*s++);
    putchar('\n');
    return 1;
}
