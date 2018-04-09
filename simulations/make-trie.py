import marisa_trie
import sys, gzip
from scipy import sparse as sps
import scipy
import os
import resource
import array
import numpy as np
from functools import lru_cache
import itertools
 
# resource.setrlimit(resource.RLIMIT_DATA, (1e9, 10e9))
num_devices = 34616536
num_apps = 12484762
Msize = 5190470377-num_devices
triefname = 'apps-unique.marisa_trie'
T = marisa_trie.Trie().load(triefname)
 
def trie(fname):
    i = 0
    ofname = fname.rsplit('.', 2)[0] + '.marisa_trie'
    if os.path.exists(ofname):
        T = marisa_trie.Trie().load(ofname)
        return T, N
    with gzip.open(fname, 'rt') as f:
        T = marisa_trie.Trie(l.strip() for i, l in enumerate(f))
        T.save(ofname)
    return T, i
 
@lru_cache(maxsize=10000000)
def _get(term):
    x = T.get(term.strip(), -1)
    if x == -1:
        print("Cannot find: {!r}".format(term))
    return x+1
 
# 5,190,470,377 apps.txt
# 34,616,536 appset_data-lno.txt.gz
# 12,484,762 apps-wcount.txt.gz
LIM = int(1e6)  # Every million entries flush the matrix
done_cnt = 0
 
 
def create_matrix(mf, mfname, ofname_cnt):
    indptr = np.zeros(LIM+1, dtype=np.int32)
    indices = array.array('I')
    ofname = mfname.rsplit('.', 2)[0] + '.csr_matrix'.format(ofname_cnt)
    j = 0
    for j, d in enumerate(mf):
        if j>LIM: break
        terms = d.decode('utf-8').strip().split(',')
        if len(terms)<1: continue
        i, terms = int(terms[0]), terms[1:]
        indices.extend([_get(t) for t in terms])
        indptr[j%LIM+1] = len(indices)
        if j % 10000 == 0:
            print("Done {}".format(j))
 
    # print("Saving: j={} start: {} stop: {}".format(j, start, stop))
    if j>0:
        print("Saving... {}".format(ofname))
        if len(indptr) > j:
            indptr = indptr[:j+2]
        print(len(indices), indptr)
         
        M = sps.csr_matrix(
            (np.ones(len(indices)), indices, indptr),
            shape=(len(indptr)-1, num_apps),
            dtype=bool
        )
        print(M.nnz)
        sps.save_npz(ofname, M)
        create_matrix(mf, mfname, ofname_cnt+1)
 
     
def to_matrix(mfname, start=0, stop=None):
    print("Num-Apps: {}\tNum-devices: {}\tlen(trie): {}".format(
        num_apps, num_devices, len(T)))
    print("Start: {}\t\tStop: {}".format(start, stop))
    mf = itertools.islice(gzip.open(mfname), start, stop)
    create_matrix(mf, mfname, start//LIM)
 
 
 
 
# from multiprocessing import Pool
# def parallel_process(mfnames):
#     with Pool(1) as p:
#         start = done_cnt
#         stop = num_devices
#         print(mfnames)
#         # step = LIM*4
#         # args = [(mfname) for start in range(start, stop, step)]
#         # print(args)
#         p.map(to_matrix, mfnames)
 
 
def simple_convert_name_to_integer(mfname):
    ofname = mfname.rsplit('.', 2)[0] + '.int.gz'
 
    with gzip.open(mfname) as f, gzip.open(ofname, 'wt') as wf:
        for i,l in enumerate(f):
            terms = l.decode('utf-8').strip().split(',')
            wf.write(terms[0] + ',')
            wf.write(','.join(str(_get(t)) for t in terms[1:]) + '\n')
            if i % 10000 == 0:
                print("Done {}k".format(i//1000))
 
 
def join_smart_mat(fnames):
    """Join arrays in Mlist inplace"""
    # M.indptr M.indices
    indptr = np.zeros(num_devices+1, dtype=np.int32)
    indices = np.zeros(Msize, dtype=np.int32)    
    i_indptr, i_indices = 0, 0
    ofname = 'joined_mat.npz'
    M = [None for _ in fnames]
    for i, mf in enumerate(fnames) :
        M[i] = sps.load_npz(mf)
        print("Loaded matrix={}. shape={}. nnz={}".format(mf, M[i].shape, M[i].nnz))
        # Mindptr = M.indptr
        # Mindices = M.indices
        # indptr[i_indptr+1:i_indptr+len(Mindptr)] = Mindptr[1:] + indptr[i_indptr]
        # i_indptr += len(Mindptr)-1
        # indices[i_indices:i_indices+len(Mindices)] = Mindices
        # i_indices += i_indices
        # del M
    print("Saving the file...")
    M = sps.csr_matrix(
        (np.ones(len(indices)), indices, indptr),
        shape=(len(indptr)-1, num_apps),
        dtype=bool
    )
    print(M.nnz)
    sps.save_npz(ofname, M)
 
 
 
 
def join_mats(fnames, s, e):
    ofname="mat_{}_{}".format(s, e)
    print(ofname, fnames)
    M = [sps.load_npz(f) for f in fnames]
    print("Done reading..")
    sps.save_npz(
        ofname,
        sps.vstack(M)
    )
if __name__ == "__main__":
#     if len(sys.argv)<2 or sys.argv[1] == '-h':
#         print("""USAGE: 
# $ python {} file1 [file2, file3...]
#         """.format(sys.argv[0]))
#         exit(0)
#     for f in sys.argv[1:]:
#         trie(f)
    # to_matrix(sys.argv[1], 'apps-unique.marisa_trie')
    # parallel_process(sys.argv[1])
    # simple_convert_name_to_integer(sys.argv[1])
    # parallel_process(sys.argv[1:])
    join_smart_mat(sys.argv[1:])
