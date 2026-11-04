// expect: 242999407
/* char/short narrowing, pointers, arrays */
unsigned char uc; signed char sc; short ss; unsigned short us;
int arr[10]; char carr[16]; short sarr[5];
int main(void) {
    int i, h = 0;
    uc = 300; sc = 200; ss = 70000; us = 70000;
    h = uc + sc * 3 + ss * 5 + us * 7;
    for (i = 0; i < 10; i++) arr[i] = i * i - 5;
    for (i = 0; i < 16; i++) carr[i] = i * 17;
    for (i = 0; i < 5; i++) sarr[i] = i * 20000;
    for (i = 0; i < 10; i++) h = h * 3 + arr[i];
    for (i = 0; i < 16; i++) h = h * 3 + carr[i];
    for (i = 0; i < 5; i++) h = h * 3 + sarr[i];
    {
        int *p = arr + 3; char *q = &carr[2];
        h += *p + p[2] + *(p - 1) + *q + q[3];
        p++; q += 5; h += *p + *q;
        h += (int)(p - arr) + (int)(q - carr);
    }
    uc++; sc--; ss += 10; us -= 5;
    h = h * 7 + uc + sc + ss + us;
    return h;
}
