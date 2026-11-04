/* lc2kcc freestanding <stdarg.h>: every argument occupies one word, and
 * variadic arguments follow the last named parameter in memory. */
#ifndef _STDARG_H
#define _STDARG_H

typedef char *va_list;

#define va_start(ap, last) ((ap) = (char *)&(last) + 1)
#define va_arg(ap, type)   (*(type *)((ap) += 1, (ap) - 1))
#define va_end(ap)         ((void)0)

#endif
