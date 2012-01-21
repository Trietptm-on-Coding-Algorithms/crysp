#!/usr/bin/env python

import pickle
import random
from des import *
from poly import Poly

# -----------------------------------------------------------------------------
# Electronic Code Book mode of Operation
class ECB(object):

# encryption mode
    def enc(self,M):
        n,p = divmod(len(M),8)
        if p>0:
            M += chr(8-p)*(8-p)
            n += 1
            print "warning: padding added %d byte(s) %x"%(8-p,8-p)
        C = []
        for b in range(n):
            C.append(hex(self._cipher(Bits(M[0:8]),1)))
            M = M[8:]
        assert len(M)==0
        return ''.join(C)

# decryption mode
    def dec(self,C):
        n,p = divmod(len(C),8)
        assert p==0
        M = []
        for b in range(n):
            M.append(hex(self._cipher(Bits(C[0:8]),-1)))
            C = C[8:]
        assert len(C)==0
        return ''.join(M)

# null cipher
    def _cipher(self,B,direction):
        return B

# -----------------------------------------------------------------------------
# The easy WhiteBox DES:

def table_rKS(r,K):
    fk = subkey(PC1(K),r)
    nfk = [fk[6*n:6*n+6] for n in range(8)]
    rks = []
    for n in range(8):
        rks.append([0]*64)
    for v in range(64):
        re = Bits(v,6)
        for n in range(8):
            x = re^nfk[n]
            i = x[(5,0)].ival
            j = x[(4,3,2,1)].ival
            rks[n][re.ival] = Bits(S(n,(i<<4)+j),4)[::-1].ival
    for n in range(8):
        rks[n] = tuple(rks[n])
    return tuple(rks)


class WhiteBoxDes(ECB):

    def __init__(self,KS):
        self.KS = KS

    def _cipher(self,M,d):
        assert M.size==64
        blk = IP(M)
        L = blk[0:32]
        R = blk[32:64]
        for r in range(16)[::d]:
            L = L^self.F(r,R)
            L,R = R,L
        L,R = R,L
        C = Bits(0,64)
        C[0:32] = L
        C[32:64] = R
        return IPinv(C)

    def F(self,r,R):
        RE = E(R)
        fout = Bits(0,32)
        ri,ro = 0,0
        for n in range(8):
            nri,nro = ri+6,ro+4
            x = RE[ri:nri]
            fout[ro:nro] = self.KS[r][n][x.ival]
            ri,ro = nri,nro
        return P(fout)

# -----------------------------------------------------------------------------
# The naked DES:

def table_rKT(r,K):
    rks = table_rKS(r,K)
    rkt = []
    for n in range(12):
        rkt.append(range(256))
    for v in range(256):
        re = Bits(v,8)
        for n in range(8):
            x = Bits(rks[n][re[0:6].ival],4)//re[(0,5,6,7)]
            rkt[n][re.ival] = x.ival
    for n in range(12):
        rkt[n] = tuple(rkt[n])
    return rks,tuple(rkt)

def getrbits_T_in():
    r = E(Poly(range(32))).ival
    sr = set(range(32))
    rbits=[]
    for i in range(8):
        sr.remove(r[0])
        sr.remove(r[5])
        rbits += [r[0],r[5]]
        r = r[6:]
    return rbits+list(sr)

def table_M1():
    l,r = range(32),Poly(range(32,64))
    re = E(r).ival
    rbits = r.ival
    blk = []
    for b in range(12):
        blk.append([None]*8)
        if b<8:
            blk[b][0:6]=re[0:6]
            rbits.remove(re[0])
            rbits.remove(re[5])
            re = re[6:]
            blk[b][6:8]=l[0:2]
            l = l[2:]
        else:
            blk[b][0:4]=l[0:4]
            blk[b][4:8]=rbits[0:4]
            l = l[4:]
            rbits = rbits[4:]
    assert len(rbits)==0
    assert len(l)==0
    table = []
    for b in range(12):
        table.extend(blk[b])
    M = Poly(range(64))
    return IP(M)[table].ival

def SRLRformat():
    I = Poly(range(96))
    SR = Poly([None]*32)
    L = Poly([None]*32)
    R = Poly([None]*32)
    rbits = getrbits_T_in()
    for i in range(0,8):
        s = I[8*i:8*i+8].ival
        SR[4*i:4*i+4]= s[:4]
        R[rbits[:2]] = s[4:6]
        L[2*i:2*i+2] = s[6:8]
        rbits = rbits[2:]
    for i in range(8,12):
        s = I[8*i:8*i+8].ival
        L[4*i-16:4*i-12] = s[:4]
        R[rbits[:4]] = s[4:]
        rbits = rbits[4:]
    return SR,L,R

def ERLRformat():
    I = Poly(range(96))
    ER = Poly([None]*48)
    L = Poly([None]*32)
    R = Poly([None]*32)
    rbits = getrbits_T_in()
    for i in range(0,8):
        s = I[8*i:8*i+8].ival
        ER[6*i:6*i+6]= s[:6]
        R[rbits[:2]] = [s[0],s[5]]
        L[2*i:2*i+2] = s[6:8]
        rbits = rbits[2:]
    for i in range(8,12):
        s = I[8*i:8*i+8].ival
        L[4*i-16:4*i-12] = s[:4]
        R[rbits[:4]] = s[4:]
        rbits = rbits[4:]
    return ER,L,R

def table_M2():
    Mat = [Bits(0,96) for i in range(96)]
    SR,L,R = SRLRformat()
    newL = R.ival
    newR = Poly(zip(P(SR),L))
    RE = E(newR).ival
    m=[]
    for r in range(8):
        m += RE[0:6]+newL[0:2]
        RE = RE[6:]
        newL  = newL[2:]
    rbits = getrbits_T_in()[16:]
    for r in range(4):
        m += newL[0:4]
        for b in rbits[:4]:
            m += [newR.e(b)]
        newL = newL[4:]
        rbits = rbits[4:]
    assert len(m)==96
    for v in range(96):
        l = m[v]
        try:
            for x in l: Mat[v][x]=1
        except TypeError:
            Mat[v][l]=1
        Mat[v] = Mat[v].ival
    return Mat,m

def table_M3():
    ER,L,R = ERLRformat()
    C = Poly(R.ival+L.ival)
    return IPinv(C).ival

class WhiteDES(ECB):

    def __init__(self,KT,tM1,tM2,tM3):
        self.KT = KT
        self.tM1 = tM1
        self.tM2 = tM2
        self.tM3 = tM3

    def FX(self,v):
        res = Bits(0,96)
        for b in range(96):
            res[b] = (v&self.tM2[b]).hw()%2
        return res

    def _cipher(self,M,d):
        assert M.size==64
        if d==1:
            blk = M[self.tM1]
            for r in range(16):
                t = 0
                for n in range(12):
                    nt = t+8
                    blk[t:nt] = self.KT[r][n][blk[t:nt].ival]
                    t = nt
                blk = self.FX(blk)
            return blk[self.tM3]
        if d==-1:
            raise NotImplementedError

