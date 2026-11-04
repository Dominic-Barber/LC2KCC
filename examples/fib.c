/* Recursion, loops, arrays and pointers: the answer is in the Result word. */
int memo[20];

int fib(int n)
{
    if (n < 2)
        return n;
    return fib(n - 1) + fib(n - 2);
}

int sum(const int *p, int n)
{
    int s = 0;
    while (n--)
        s += *p++;
    return s;
}

int main(void)
{
    int i;
    for (i = 0; i < 20; i++)
        memo[i] = fib(i);
    return sum(memo, 20); /* 10945 = fib(21) - 1 */
}
