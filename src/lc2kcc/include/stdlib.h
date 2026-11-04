/* lc2kcc freestanding <stdlib.h> subset (runtime/libc.c) */
#ifndef _STDLIB_H
#define _STDLIB_H

#include <stddef.h>

#define RAND_MAX 32767

int abs(int x);
long labs(long x);
int atoi(const char *s);
long atol(const char *s);
int rand(void);
void srand(unsigned int seed);
void qsort(void *base, size_t n, size_t size, int (*cmp)(const void *, const void *));
void *bsearch(const void *key, const void *base, size_t n, size_t size, int (*cmp)(const void *, const void *));

#endif
