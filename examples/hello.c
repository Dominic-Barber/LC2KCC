/* The hello world of compilers: LC-2K has no I/O device, so the
 * observable output is main's return value, which the startup code
 * stores in the `Result` word. */
#define ANSWER (6 * 7)

int main(void)
{
    return ANSWER;
}
