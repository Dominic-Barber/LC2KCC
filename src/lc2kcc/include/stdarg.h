/* lc2kcc freestanding <stdarg.h>: a scalar argument occupies one word, a
 * struct or long long argument occupies sizeof words, and variadic arguments
 * follow the last named parameter in memory. */
#ifndef _STDARG_H
#define _STDARG_H

typedef char *va_list;

#define va_start(ap, last) ((ap) = (char *)&(last) + 1)
#define __va_words(type)   (sizeof(type) <= 4 ? 1 : sizeof(type))
#define va_arg(ap, type)   (*(type *)((ap) += __va_words(type), (ap) - __va_words(type)))
#define va_end(ap)         ((void)0)

#endif
