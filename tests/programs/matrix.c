// expect: -1904657362
/* 2D arrays and matrix kernels */
typedef int mat[4][4];
static mat A = { {1,2,3,4}, {5,6,7,8}, {9,10,11,12}, {13,14,15,16} };
static mat B, C;
static void mul(mat x, mat y, mat z) {
    int i, j, k;
    for (i = 0; i < 4; i++) for (j = 0; j < 4; j++) { int s = 0; for (k = 0; k < 4; k++) s += x[i][k] * y[k][j]; z[i][j] = s; }
}
static int trace(mat m) { int i, t = 0; for (i = 0; i < 4; i++) t += m[i][i]; return t; }
int main(void) {
    int i, j, h = 0;
    for (i = 0; i < 4; i++) for (j = 0; j < 4; j++) B[i][j] = A[j][i] - (i == j ? 3 : 0);
    mul(A, B, C);
    for (i = 0; i < 4; i++) for (j = 0; j < 4; j++) h = h * 17 + C[i][j];
    mul(C, C, B);
    h = h * 17 + trace(B) + B[3][2];
    return h;
}
