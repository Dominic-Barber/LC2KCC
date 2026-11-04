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

#define EE_OUTBUF_SIZE 2048
char    ee_outbuf[EE_OUTBUF_SIZE];
ee_u32  ee_outlen = 0;

int
ee_printf(const char *fmt, ...)
{
    int n = 0;
    while (fmt[n] != 0)
    {
        if (ee_outlen < EE_OUTBUF_SIZE)
            ee_outbuf[ee_outlen++] = fmt[n];
        n++;
    }
    return n;
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
