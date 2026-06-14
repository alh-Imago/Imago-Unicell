/*
 * huffman_c.c  —  Canonical Huffman entropy coding, C extension
 * ──────────────────────────────────────────────────────────────
 * Same algorithm and header format as huffman.py:
 *
 * Header:
 *   [2 bytes BE]  symbol count
 *   per symbol:
 *     [1 byte] symbol value
 *     [1 byte] code bit-length
 *   [4 bytes BE]  total symbol count (for exact termination on decompress)
 *
 * Then a packed MSB-first bit stream, zero-padded to byte boundary.
 *
 * Canonical code assignment: sort by (bit_length, symbol), assign codes
 * sequentially. Only lengths need to be stored — decompressor reconstructs
 * identical codes deterministically.
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>

#define MAX_SYMBOLS  256
#define MAX_CODELEN  16    /* max Huffman code length we'll allow */

/* ── Min-heap for tree building ──────────────────────────────────────────── */

typedef struct {
    uint64_t freq;
    int      symbol;    /* -1 = internal node */
    int      left;
    int      right;
} Node;

typedef struct {
    Node  *nodes;
    int   *heap;        /* indices into nodes */
    int    size;
    int    cap;
} Heap;

static void heap_push(Heap *h, int idx)
{
    int i = h->size++;
    h->heap[i] = idx;
    /* sift up */
    while (i > 0) {
        int parent = (i - 1) / 2;
        if (h->nodes[h->heap[parent]].freq <= h->nodes[h->heap[i]].freq)
            break;
        int tmp = h->heap[parent];
        h->heap[parent] = h->heap[i];
        h->heap[i] = tmp;
        i = parent;
    }
}

static int heap_pop(Heap *h)
{
    int ret = h->heap[0];
    h->heap[0] = h->heap[--h->size];
    /* sift down */
    int i = 0;
    while (1) {
        int l = 2*i+1, r = 2*i+2, smallest = i;
        if (l < h->size && h->nodes[h->heap[l]].freq < h->nodes[h->heap[smallest]].freq)
            smallest = l;
        if (r < h->size && h->nodes[h->heap[r]].freq < h->nodes[h->heap[smallest]].freq)
            smallest = r;
        if (smallest == i) break;
        int tmp = h->heap[i]; h->heap[i] = h->heap[smallest]; h->heap[smallest] = tmp;
        i = smallest;
    }
    return ret;
}

/* ── Build code lengths via Huffman tree ─────────────────────────────────── */

static int build_lengths(
    const unsigned char *data, Py_ssize_t n,
    uint8_t *lengths,           /* out: lengths[256] */
    int     *sym_order,         /* out: symbols sorted by (length, symbol) */
    int     *sym_count_out)     /* out: number of unique symbols */
{
    uint64_t freq[MAX_SYMBOLS] = {0};
    for (Py_ssize_t i = 0; i < n; i++)
        freq[data[i]]++;

    int nsyms = 0;
    for (int i = 0; i < MAX_SYMBOLS; i++)
        if (freq[i]) nsyms++;

    if (nsyms == 0) { *sym_count_out = 0; return 0; }

    /* Single symbol edge case */
    if (nsyms == 1) {
        for (int i = 0; i < MAX_SYMBOLS; i++)
            if (freq[i]) { lengths[i] = 1; sym_order[0] = i; }
        *sym_count_out = 1;
        return 1;
    }

    /* Allocate node pool: up to 2*nsyms-1 nodes */
    int max_nodes = 2 * nsyms;
    Node *nodes = (Node *)calloc(max_nodes, sizeof(Node));
    int  *heap_arr = (int *)malloc(max_nodes * sizeof(int));
    if (!nodes || !heap_arr) { free(nodes); free(heap_arr); return -1; }

    Heap h = { nodes, heap_arr, 0, max_nodes };
    int  node_count = 0;

    for (int i = 0; i < MAX_SYMBOLS; i++) {
        if (freq[i]) {
            nodes[node_count] = (Node){ freq[i], i, -1, -1 };
            heap_push(&h, node_count++);
        }
    }

    while (h.size > 1) {
        int a = heap_pop(&h);
        int b = heap_pop(&h);
        nodes[node_count] = (Node){
            nodes[a].freq + nodes[b].freq, -1, a, b
        };
        heap_push(&h, node_count++);
    }

    /* Walk tree to assign depths */
    memset(lengths, 0, MAX_SYMBOLS);

    /* Iterative DFS using explicit stack */
    int  stk_node[512], stk_depth[512], stk_top = 0;
    stk_node[stk_top]  = heap_pop(&h);
    stk_depth[stk_top] = 0;
    stk_top++;

    while (stk_top > 0) {
        stk_top--;
        int nd = stk_node[stk_top];
        int d  = stk_depth[stk_top];
        if (nodes[nd].symbol >= 0) {
            lengths[nodes[nd].symbol] = (uint8_t)(d < 1 ? 1 : d);
        } else {
            if (stk_top + 2 >= 512) { free(nodes); free(heap_arr); return -1; }
            stk_node[stk_top]   = nodes[nd].left;
            stk_depth[stk_top]  = d + 1;
            stk_top++;
            stk_node[stk_top]   = nodes[nd].right;
            stk_depth[stk_top]  = d + 1;
            stk_top++;
        }
    }

    free(nodes);
    free(heap_arr);

    /* Build sorted symbol list: sort by (length, symbol) */
    int k = 0;
    for (int i = 0; i < MAX_SYMBOLS; i++)
        if (freq[i]) sym_order[k++] = i;

    /* Simple insertion sort (at most 256 items) */
    for (int i = 1; i < k; i++) {
        int key = sym_order[i], j = i - 1;
        while (j >= 0 && (lengths[sym_order[j]] > lengths[key] ||
               (lengths[sym_order[j]] == lengths[key] && sym_order[j] > key))) {
            sym_order[j+1] = sym_order[j]; j--;
        }
        sym_order[j+1] = key;
    }

    *sym_count_out = k;
    return k;
}

/* ── Assign canonical codes ──────────────────────────────────────────────── */

static void assign_codes(
    const int *sym_order, int nsyms,
    const uint8_t *lengths,
    uint32_t *codes)    /* out: codes[256] */
{
    uint32_t code = 0;
    int      prev_len = 0;
    for (int i = 0; i < nsyms; i++) {
        int sym = sym_order[i];
        int L   = lengths[sym];
        code <<= (L - prev_len);
        codes[sym] = code;
        code++;
        prev_len = L;
    }
}

/* ── compress ─────────────────────────────────────────────────────────────── */

static PyObject *py_compress(PyObject *self, PyObject *args)
{
    const unsigned char *data;
    Py_ssize_t           n;
    if (!PyArg_ParseTuple(args, "y#", &data, &n))
        return NULL;
    if (n == 0)
        return PyBytes_FromStringAndSize(NULL, 0);

    uint8_t  lengths[MAX_SYMBOLS] = {0};
    int      sym_order[MAX_SYMBOLS];
    int      nsyms = 0;
    uint32_t codes[MAX_SYMBOLS]   = {0};

    if (build_lengths(data, n, lengths, sym_order, &nsyms) < 0)
        return PyErr_NoMemory();

    assign_codes(sym_order, nsyms, lengths, codes);

    /* Build header */
    /* 2 (sym count) + nsyms*2 + 4 (total syms) */
    int hdr_size = 2 + nsyms * 2 + 4;
    /* Stream: worst case all 8-bit codes = n bytes + 1 padding byte */
    Py_ssize_t out_cap = hdr_size + n + 8;
    unsigned char *out = (unsigned char *)malloc(out_cap);
    if (!out) return PyErr_NoMemory();

    int pos = 0;
    /* sym count BE */
    out[pos++] = (nsyms >> 8) & 0xFF;
    out[pos++] =  nsyms       & 0xFF;
    for (int i = 0; i < nsyms; i++) {
        int sym = sym_order[i];
        out[pos++] = (unsigned char)sym;
        out[pos++] = lengths[sym];
    }
    /* total symbol count BE uint32 */
    out[pos++] = (n >> 24) & 0xFF;
    out[pos++] = (n >> 16) & 0xFF;
    out[pos++] = (n >>  8) & 0xFF;
    out[pos++] =  n        & 0xFF;

    /* Encode bit stream */
    uint64_t bits  = 0;
    int      nbits = 0;

    for (Py_ssize_t i = 0; i < n; i++) {
        int      sym  = data[i];
        uint32_t code = codes[sym];
        int      L    = lengths[sym];

        bits   = (bits << L) | code;
        nbits += L;

        while (nbits >= 8) {
            if (pos >= out_cap) {
                out_cap *= 2;
                unsigned char *tmp = (unsigned char *)realloc(out, out_cap);
                if (!tmp) { free(out); return PyErr_NoMemory(); }
                out = tmp;
            }
            nbits -= 8;
            out[pos++] = (unsigned char)((bits >> nbits) & 0xFF);
        }
    }
    /* Flush remaining bits */
    if (nbits > 0) {
        if (pos >= out_cap) {
            out_cap++;
            unsigned char *tmp = (unsigned char *)realloc(out, out_cap);
            if (!tmp) { free(out); return PyErr_NoMemory(); }
            out = tmp;
        }
        out[pos++] = (unsigned char)((bits << (8 - nbits)) & 0xFF);
    }

    PyObject *result = PyBytes_FromStringAndSize((char *)out, pos);
    free(out);
    return result;
}

/* ── decompress ───────────────────────────────────────────────────────────── */

static PyObject *py_decompress(PyObject *self, PyObject *args)
{
    const unsigned char *data;
    Py_ssize_t           n;
    if (!PyArg_ParseTuple(args, "y#", &data, &n))
        return NULL;
    if (n == 0)
        return PyBytes_FromStringAndSize(NULL, 0);

    int i = 0;

    /* Read symbol count */
    if (i + 2 > n) goto trunc;
    int nsyms = ((int)data[i] << 8) | data[i+1]; i += 2;

    uint8_t  lengths[MAX_SYMBOLS] = {0};
    int      sym_order[MAX_SYMBOLS];

    for (int k = 0; k < nsyms; k++) {
        if (i + 2 > n) goto trunc;
        int     sym = data[i++];
        uint8_t L   = data[i++];
        lengths[sym]  = L;
        sym_order[k]  = sym;
    }

    /* Read total symbol count */
    if (i + 4 > n) goto trunc;
    uint32_t total_syms =
        ((uint32_t)data[i]   << 24) |
        ((uint32_t)data[i+1] << 16) |
        ((uint32_t)data[i+2] <<  8) |
         (uint32_t)data[i+3];
    i += 4;

    /* Assign canonical codes */
    uint32_t codes[MAX_SYMBOLS] = {0};
    assign_codes(sym_order, nsyms, lengths, codes);

    /* Build decode table: for each possible (code, length) pair store the symbol.
     * We use a simple linear search over nsyms at each step — fast enough for
     * MAX_SYMBOLS=256 and typical code lengths <= 16.
     * For production a lookup table indexed by next-N-bits would be faster.
     */

    /* Allocate output */
    Py_ssize_t out_cap = (Py_ssize_t)total_syms + 1;
    unsigned char *out = (unsigned char *)malloc(out_cap);
    if (!out) return PyErr_NoMemory();

    int      max_len = 0;
    for (int k = 0; k < nsyms; k++)
        if (lengths[sym_order[k]] > max_len)
            max_len = lengths[sym_order[k]];

    uint64_t bits  = 0;
    int      nbits = 0;
    uint32_t decoded = 0;

    while (decoded < total_syms) {
        /* Refill */
        while (nbits < max_len && i < n) {
            bits   = (bits << 8) | data[i++];
            nbits += 8;
        }

        /* Try each length 1..min(nbits,max_len) */
        int matched = 0;
        for (int L = 1; L <= nbits && L <= max_len; L++) {
            uint32_t candidate = (uint32_t)((bits >> (nbits - L)) & ((1u << L) - 1));
            /* Linear search through symbols of this length */
            for (int k = 0; k < nsyms; k++) {
                int sym = sym_order[k];
                if (lengths[sym] == L && codes[sym] == candidate) {
                    out[decoded++] = (unsigned char)sym;
                    nbits -= L;
                    bits  &= (1ULL << nbits) - 1;
                    matched = 1;
                    break;
                }
            }
            if (matched) break;
        }
        if (!matched) break;
    }

    PyObject *result = PyBytes_FromStringAndSize((char *)out, decoded);
    free(out);
    return result;

trunc:
    PyErr_SetString(PyExc_ValueError, "Huffman: truncated header");
    return NULL;
}

/* ── Module ──────────────────────────────────────────────────────────────── */

static PyMethodDef HuffMethods[] = {
    {"compress",   py_compress,   METH_VARARGS, "Huffman compress bytes->bytes"},
    {"decompress", py_decompress, METH_VARARGS, "Huffman decompress bytes->bytes"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef huffmodule = {
    PyModuleDef_HEAD_INIT, "_huffman_c", NULL, -1, HuffMethods
};

PyMODINIT_FUNC PyInit__huffman_c(void) {
    return PyModule_Create(&huffmodule);
}
