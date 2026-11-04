// expect: -184638405
/* linked list from a static pool */
struct node { int val; struct node *next; };
static struct node pool[32];
static int used;
static struct node *alloc(int v) { struct node *n = &pool[used++]; n->val = v; n->next = 0; return n; }
static struct node *push(struct node *head, int v) { struct node *n = alloc(v); n->next = head; return n; }
static struct node *reverse(struct node *h) {
    struct node *prev = 0, *next;
    while (h) { next = h->next; h->next = prev; prev = h; h = next; }
    return prev;
}
static int sum(struct node *h) { int s = 0; for (; h; h = h->next) s = s * 3 + h->val; return s; }
static struct node *merge(struct node *a, struct node *b) {
    struct node head, *t = &head;
    head.next = 0;
    while (a && b) {
        if (a->val <= b->val) { t->next = a; a = a->next; } else { t->next = b; b = b->next; }
        t = t->next;
    }
    t->next = a ? a : b;
    return head.next;
}
int main(void) {
    struct node *a = 0, *b = 0;
    int i, h;
    for (i = 0; i < 10; i++) a = push(a, 100 - i * 7);
    for (i = 0; i < 8; i++) b = push(b, 90 - i * 5);
    h = sum(a);
    a = reverse(a); b = reverse(b);
    h = h * 5 + sum(a);
    h = h * 5 + sum(merge(a, b));
    return h + used;
}
