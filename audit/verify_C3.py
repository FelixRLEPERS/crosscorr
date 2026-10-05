"""C3: двойное выделение памяти под суррогаты.

pairs.py создаёт `out` (N,B,T) в куче, затем SharedMemory того же размера
и копирует `out` в view. Пик памяти ~2x размера блока суррогатов.
Проверяем объём: out.nbytes и shm размер.
"""
import numpy as np

N, B, T = 10, 200, 5000
dtype = np.float32
out_nbytes = N * B * T * np.dtype(dtype).itemsize
print("surrogates block nbytes =", out_nbytes)
print("plus X (T,N) float64    =", T * N * 8)
print("peak double-alloc extra =", out_nbytes, "bytes (out + shm copy)")
