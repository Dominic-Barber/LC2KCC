/* lc2kcc <stdio.h> subset. LC-2K has no I/O: printf and friends append to the
 * global buffer __stdout (a marked OUTPUT: word array), which `lc2kcc run`
 * prints after the program halts. */
#ifndef _STDIO_H
#define _STDIO_H

#include <stddef.h>
#include <stdarg.h>

#define EOF (-1)

int printf(const char *fmt, ...);
int sprintf(char *out, const char *fmt, ...);
int snprintf(char *out, size_t cap, const char *fmt, ...);
int vsnprintf(char *out, size_t cap, const char *fmt, va_list ap);
int puts(const char *s);
int putchar(int c);

#endif
