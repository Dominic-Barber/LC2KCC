// expect: -2127777982
struct rec { char name[8]; short vals[3]; int *ptr; struct { int a, b; } in; };
static int target = 55;
static struct rec recs[3] = {
    { "ab", { 1, 2, 3 }, &target, { 4, 5 } },
    { "cdef", { -1 }, 0, { .b = 9 } },
    { .vals = { [2] = 7 }, .in.a = 8 },
};
static int tri[3][3] = { {1}, {2, 3}, {4, 5, 6} };
static int sparse[8] = { [1] = 10, [5] = 50, 60 };
static char text[] = { 'x', 'y', 'z', 0 };
static const char *words[] = { "one", "two", "three", 0 };
int main(void) {
    int i, j, h = 0;
    struct rec local = { "q", { 9, 8, 7 }, &target, { 1, 2 } };
    int arr[5] = { 1, 2 };
    for (i = 0; i < 3; i++) { h = h * 31 + recs[i].name[0] + recs[i].name[1] + recs[i].vals[0] + recs[i].vals[2] + recs[i].in.a + recs[i].in.b + (recs[i].ptr ? *recs[i].ptr : -1); }
    for (i = 0; i < 3; i++) for (j = 0; j < 3; j++) h = h * 31 + tri[i][j];
    for (i = 0; i < 8; i++) h = h * 31 + sparse[i];
    for (i = 0; text[i]; i++) h = h * 31 + text[i];
    for (i = 0; words[i]; i++) h = h * 31 + words[i][0] + words[i][1];
    h = h * 31 + local.name[0] + local.vals[1] + *local.ptr + local.in.b;
    for (i = 0; i < 5; i++) h = h * 31 + arr[i];
    return h;
}
