/*
 * lz77_c.c  —  LZ77 C extension, 32KB window
 * ─────────────────────────────────────────────
 * Window   : 32768 bytes (15-bit offset, stored as offset-1)
 * Lookahead: 258 bytes  (8-bit length,  stored as length-3)
 *
 * Token format: 1 flag byte per group of 8 decisions.
 *   flag bit = 0  → next 1 byte is a literal
 *   flag bit = 1  → next 3 bytes are a back-reference:
 *
 *     byte0 = (enc_off >> 8) & 0x7F    high 7 bits of 15-bit offset
 *     byte1 =  enc_off       & 0xFF    low  8 bits of 15-bit offset
 *     byte2 =  enc_len       & 0xFF    8-bit length (length-3)
 *
 *     enc_off = offset - 1   (0..32767, fits 15 bits)
 *     enc_len = length - 3   (0..255,   fits 8  bits)
 *
 * Clean byte boundaries — no bit-sharing between fields.
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>

#define WINDOW_SIZE    32768
#define MAX_MATCH_LEN  258
#define MIN_MATCH_LEN  3
#define HASH_SIZE      32768
#define HASH_MASK      (HASH_SIZE - 1)
#define MAX_CHAIN      128
#define NIL            -1

static inline int hash3(const unsigned char *p)
{
    return (int)(((uint32_t)p[0] ^ ((uint32_t)p[1] << 4) ^
                  ((uint32_t)p[2] << 8)) & HASH_MASK);
}

static int find_match(
    const unsigned char *data, int pos, int n,
    const int *head, const int *chain,
    int *best_offset)
{
    int best_len = 0;
    int limit    = pos - WINDOW_SIZE;
    if (limit < 0) limit = 0;

    if (pos + MIN_MATCH_LEN > n)
        return 0;

    int h     = hash3(data + pos);
    int cur   = head[h];
    int depth = MAX_CHAIN;

    while (cur >= limit && depth-- > 0) {
        /* Guard: cur must have MIN_MATCH_LEN bytes before end */
        if (cur + MIN_MATCH_LEN > n) { cur = chain[cur]; continue; }

        if (data[cur]   == data[pos] &&
            data[cur+1] == data[pos+1] &&
            data[cur+2] == data[pos+2])
        {
            int len  = 3;
            int maxl = pos + MAX_MATCH_LEN;
            if (maxl > n) maxl = n;
            while (pos + len < maxl && data[cur + len] == data[pos + len])
                len++;

            if (len > best_len) {
                best_len     = len;
                *best_offset = pos - cur;   /* always >= 1 */
                if (best_len == MAX_MATCH_LEN) break;
            }
        }
        cur = chain[cur];
    }
    return (best_len >= MIN_MATCH_LEN) ? best_len : 0;
}

/* ── compress ─────────────────────────────────────────────────────────────── */

static PyObject *py_compress(PyObject *self, PyObject *args)
{
    const unsigned char *data;
    Py_ssize_t           n;
    if (!PyArg_ParseTuple(args, "y#", &data, &n)) return NULL;
    if (n == 0) return PyBytes_FromStringAndSize(NULL, 0);

    /* Worst case: all literals → n + ceil(n/8) flag bytes */
    Py_ssize_t out_cap = n + n / 8 + 64;
    unsigned char *out = (unsigned char *)malloc(out_cap);
    int *head          = (int *)malloc(HASH_SIZE * sizeof(int));
    int *chain         = (int *)malloc((size_t)n  * sizeof(int));
    if (!out || !head || !chain) {
        free(out); free(head); free(chain); return PyErr_NoMemory();
    }
    for (int i = 0; i < HASH_SIZE; i++) head[i] = NIL;

    Py_ssize_t out_pos = 0;
    int        pos     = 0;

    while (pos < (int)n) {
        /* Need room for: 1 flag + up to 8*(3 bytes backref) = 25 bytes */
        if (out_pos + 25 > out_cap) {
            out_cap = out_cap * 2 + 64;
            unsigned char *tmp = (unsigned char *)realloc(out, out_cap);
            if (!tmp) { free(out); free(head); free(chain); return PyErr_NoMemory(); }
            out = tmp;
        }

        int           flag_pos = (int)out_pos++;
        unsigned char flag     = 0;

        for (int bit = 0; bit < 8 && pos < (int)n; bit++) {
            int offset = 0, mlen = 0;
            if (pos + MIN_MATCH_LEN <= (int)n)
                mlen = find_match(data, pos, (int)n, head, chain, &offset);

            if (mlen >= MIN_MATCH_LEN) {
                flag |= (1 << (7 - bit));
                int enc_off = offset - 1;            /* 0..32767 */
                int enc_len = mlen - MIN_MATCH_LEN;  /* 0..255   */
                out[out_pos++] = (enc_off >> 8) & 0x7F;
                out[out_pos++] =  enc_off       & 0xFF;
                out[out_pos++] =  enc_len       & 0xFF;
                /* Update hash */
                for (int k = 0; k < mlen; k++) {
                    int p = pos + k;
                    if (p + MIN_MATCH_LEN <= (int)n) {
                        int h = hash3(data + p);
                        chain[p] = head[h]; head[h] = p;
                    }
                }
                pos += mlen;
            } else {
                out[out_pos++] = data[pos];
                if (pos + MIN_MATCH_LEN <= (int)n) {
                    int h = hash3(data + pos);
                    chain[pos] = head[h]; head[h] = pos;
                }
                pos++;
            }
        }
        out[flag_pos] = flag;
    }

    free(head); free(chain);
    PyObject *result = PyBytes_FromStringAndSize((char *)out, out_pos);
    free(out);
    return result;
}

/* ── decompress ───────────────────────────────────────────────────────────── */

static PyObject *py_decompress(PyObject *self, PyObject *args)
{
    const unsigned char *data;
    Py_ssize_t           n;
    if (!PyArg_ParseTuple(args, "y#", &data, &n)) return NULL;
    if (n == 0) return PyBytes_FromStringAndSize(NULL, 0);

    Py_ssize_t out_cap = n * 6 + 64;
    unsigned char *out = (unsigned char *)malloc(out_cap);
    if (!out) return PyErr_NoMemory();

    Py_ssize_t out_pos = 0;
    Py_ssize_t i       = 0;

    while (i < n) {
        unsigned char flag = data[i++];

        for (int bit = 0; bit < 8; bit++) {
            if (i >= n) break;

            if (flag & (1 << (7 - bit))) {
                /* Back-reference: need exactly 3 more bytes */
                if (i + 3 > n) break;
                unsigned char b0 = data[i++];
                unsigned char b1 = data[i++];
                unsigned char b2 = data[i++];

                int enc_off = ((int)(b0 & 0x7F) << 8) | (int)b1;
                int enc_len = (int)b2;
                int offset  = enc_off + 1;
                int length  = enc_len + MIN_MATCH_LEN;

                int start = (int)out_pos - offset;
                if (start < 0) {
                    free(out);
                    PyErr_SetString(PyExc_ValueError,
                        "LZ77: invalid back-reference (corrupted archive)");
                    return NULL;
                }
                /* Grow if needed */
                if (out_pos + length > out_cap) {
                    out_cap = (out_pos + length) * 2;
                    unsigned char *tmp = (unsigned char *)realloc(out, out_cap);
                    if (!tmp) { free(out); return PyErr_NoMemory(); }
                    out = tmp;
                }
                /* Byte-by-byte handles overlapping copies */
                for (int k = 0; k < length; k++)
                    out[out_pos++] = out[start + k];
            } else {
                /* Literal */
                if (out_pos >= out_cap) {
                    out_cap *= 2;
                    unsigned char *tmp = (unsigned char *)realloc(out, out_cap);
                    if (!tmp) { free(out); return PyErr_NoMemory(); }
                    out = tmp;
                }
                out[out_pos++] = data[i++];
            }
        }
    }

    PyObject *result = PyBytes_FromStringAndSize((char *)out, out_pos);
    free(out);
    return result;
}

/* ── Module ──────────────────────────────────────────────────────────────── */

static PyMethodDef Lz77Methods[] = {
    {"compress",   py_compress,   METH_VARARGS, "LZ77 compress bytes->bytes"},
    {"decompress", py_decompress, METH_VARARGS, "LZ77 decompress bytes->bytes"},
    {NULL, NULL, 0, NULL}
};
static struct PyModuleDef lz77module = {
    PyModuleDef_HEAD_INIT, "_lz77_c", NULL, -1, Lz77Methods
};
PyMODINIT_FUNC PyInit__lz77_c(void) { return PyModule_Create(&lz77module); }
