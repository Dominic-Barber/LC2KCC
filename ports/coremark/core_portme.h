/*
 * CoreMark port for lc2kcc (LC-2K). Derived from third_party/coremark/barebones.
 *
 * Built natively (no __LC2K__) this same port gives the x86-32 reference
 * build used for size measurement and CRC cross-checks.
 */
#ifndef CORE_PORTME_H
#define CORE_PORTME_H

#define HAS_FLOAT  0
#define HAS_TIME_H 0
#define USE_CLOCK  0
#define HAS_STDIO  0
#define HAS_PRINTF 0

#ifndef ITERATIONS
#define ITERATIONS 1
#endif

#define COMPILER_VERSION "lc2kcc"
#define COMPILER_FLAGS   "default"
#define MEM_LOCATION     "STATIC"

/* ILP32 type sizes, as CoreMark's check_data_types() requires. */
typedef signed short   ee_s16;
typedef unsigned short ee_u16;
typedef signed int     ee_s32;
typedef int            ee_f32; /* unused: HAS_FLOAT is 0 */
typedef unsigned char  ee_u8;
typedef unsigned int   ee_u32;
typedef ee_u32         ee_ptr_int;
typedef unsigned int   ee_size_t;
#define NULL ((void *)0)

#define align_mem(x) (void *)(4 + (((ee_ptr_int)(x)-1) & ~3))

#define CORETIMETYPE ee_u32
typedef ee_u32 CORE_TICKS;

#define SEED_METHOD       SEED_VOLATILE
#define MEM_METHOD        MEM_STATIC
#define MULTITHREAD       1
#define USE_PTHREAD       0
#define USE_FORK          0
#define USE_SOCKET        0
#define MAIN_HAS_NOARGC   1
#define MAIN_HAS_NORETURN 0

extern ee_u32 default_num_contexts;

typedef struct CORE_PORTABLE_S
{
    ee_u8 portable_id;
} core_portable;

void portable_init(core_portable *p, int *argc, char *argv[]);
void portable_fini(core_portable *p);

#if !defined(PROFILE_RUN) && !defined(PERFORMANCE_RUN) \
    && !defined(VALIDATION_RUN)
#if (TOTAL_DATA_SIZE == 1200)
#define PROFILE_RUN 1
#elif (TOTAL_DATA_SIZE == 2000)
#define PERFORMANCE_RUN 1
#else
#define VALIDATION_RUN 1
#endif
#endif

int ee_printf(const char *fmt, ...);

#endif /* CORE_PORTME_H */
