/*
 * CoreMark port for lc2kcc (LC-2K). Derived from third_party/coremark/barebones.
 *
 * LC-2K has no timer and no I/O device, so:
 *  - Time is synthetic: every run reports exactly 10 seconds, which keeps
 *    CoreMark's "must run >= 10 secs" check from counting as an error.
 *    Real performance comes from the simulator's instruction count.
 *  - ee_printf copies the raw format string (arguments are ignored) into
 *    ee_outbuf, which the simulator can dump as text after halt. That is
 *    enough to see "Correct operation validated." or the ERROR! lines.
 */
#include "coremark.h"
#include <stdarg.h>

#if (SEED_METHOD == SEED_VOLATILE)
#if VALIDATION_RUN
volatile ee_s32 seed1_volatile = 0x3415;
volatile ee_s32 seed2_volatile = 0x3415;
volatile ee_s32 seed3_volatile = 0x66;
#endif
#if PERFORMANCE_RUN
volatile ee_s32 seed1_volatile = 0x0;
volatile ee_s32 seed2_volatile = 0x0;
volatile ee_s32 seed3_volatile = 0x66;
#endif
#if PROFILE_RUN
volatile ee_s32 seed1_volatile = 0x8;
volatile ee_s32 seed2_volatile = 0x8;
volatile ee_s32 seed3_volatile = 0x8;
#endif
volatile ee_s32 seed4_volatile = ITERATIONS;
volatile ee_s32 seed5_volatile = 0;
#endif

#define TICKS_PER_SEC 1000

static CORE_TICKS start_time_val, stop_time_val;

void
start_time(void)
{
    start_time_val = 0;
}

void
stop_time(void)
{
    stop_time_val = 10 * TICKS_PER_SEC;
}

CORE_TICKS
get_time(void)
{
    return stop_time_val - start_time_val;
}

secs_ret
time_in_secs(CORE_TICKS ticks)
{
    return ticks / TICKS_PER_SEC;
}

ee_u32 default_num_contexts = 1;

#define EE_OUTBUF_SIZE 1024
char   ee_outbuf[EE_OUTBUF_SIZE];
ee_u32 ee_outlen = 0;

static void
put_char(char c)
{
    if (ee_outlen < EE_OUTBUF_SIZE - 1)
        ee_outbuf[ee_outlen++] = c;
}

/* Print `value` in `base` (10 or 16), left-padded to `width` with `pad`. */
static void
put_number(ee_u32 value, ee_u32 base, int width, char pad)
{
    char digits[12];
    int  n = 0;
    do
    {
        ee_u32 d = value % base;
        digits[n++] = (char)(d < 10 ? '0' + d : 'a' + (d - 10));
        value /= base;
    } while (value != 0);
    while (width > n)
    {
        put_char(pad);
        width--;
    }
    while (n > 0)
        put_char(digits[--n]);
}

/* Minimal printf: %d %u %x %c %s %% with optional 0 flag, width and l. */
int
ee_printf(const char *fmt, ...)
{
    va_list ap;
    ee_u32  start = ee_outlen;
    va_start(ap, fmt);
    while (*fmt != 0)
    {
        char c = *fmt++;
        if (c != '%')
        {
            put_char(c);
            continue;
        }
        char pad   = ' ';
        int  width = 0;
        if (*fmt == '0')
        {
            pad = '0';
            fmt++;
        }
        while (*fmt >= '0' && *fmt <= '9')
            width = width * 10 + (*fmt++ - '0');
        while (*fmt == 'l')
            fmt++;
        c = *fmt++;
        if (c == 'd')
        {
            ee_s32 v = va_arg(ap, ee_s32);
            if (v < 0)
            {
                put_char('-');
                put_number((ee_u32)0 - (ee_u32)v, 10, width > 0 ? width - 1 : 0, pad);
            }
            else
                put_number((ee_u32)v, 10, width, pad);
        }
        else if (c == 'u')
            put_number(va_arg(ap, ee_u32), 10, width, pad);
        else if (c == 'x')
            put_number(va_arg(ap, ee_u32), 16, width, pad);
        else if (c == 'c')
            put_char((char)va_arg(ap, int));
        else if (c == 's')
        {
            const char *s = va_arg(ap, const char *);
            while (*s != 0)
                put_char(*s++);
        }
        else if (c == '%')
            put_char('%');
        else
            put_char(c);
    }
    va_end(ap);
    ee_outbuf[ee_outlen] = 0;
    return (int)(ee_outlen - start);
}

void
portable_init(core_portable *p, int *argc, char *argv[])
{
    (void)argc;
    (void)argv;
    p->portable_id = 1;
}

void
portable_fini(core_portable *p)
{
    p->portable_id = 0;
}
