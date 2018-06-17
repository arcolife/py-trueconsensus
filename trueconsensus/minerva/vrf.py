from Crypto.Hash import SHA256
from Crypto.PublicKey.RSA import RSAImplementation
from Crypto.Random import random
from Crypto.Util import number
import hashlib
from math import ceil
import sys

def getOctetSize(n) :
    nbits=1
    while n :
        n >>= 1
        nbits+=1
    q,_ = divmod(nbits, 8)
    return q

class PrivateKeyPrim(object) :
    __slots__ = ('n', 'd', 'k')
    def __init__(self,priv_exp, size):
        self.d = priv_exp
        self.n = size
        self.k = getOctetSize(size)

class PublicKeyPrim(object) :
    __slots__ = ('n', 'e', 'k')
    def __init__(self,pub_exp, size):
        self.e = pub_exp
        self.n = size
        self.k = getOctetSize(size)


def I2OSP(x, xLen):
    if x > pow(256,xLen) :
        raise  Exception('Exception: Number too large')
    else :
        octet_s = number.long_to_bytes(x, xLen)
        return b''+octet_s

def OS2IP(X):
    integer = number.bytes_to_long(X)
    return integer

def MGF1(mgfSeed, maskLen, Hlen=32, Hash=SHA256.new):
    if maskLen > Hlen * pow(2,32) :
        raise Exception('Exception: mask length is too large')
    else : 
        T=b''
        for counter in range(int(ceil(maskLen/Hlen))) :
            C = I2OSP(counter, 4)
            T = T + Hash(mgfSeed+C).digest()
        return T[:maskLen]


def RSAVP1(PK, m):
    if m > PK.n or m < 0 :
        raise Exception('m out of range')
    else : 
        return pow(m,PK.e, PK.n)

def RSASP1(SK, c):
    if c > SK.n or c < 0 :
        raise Exception('c out of range')
    else :
        return pow(c, SK.d, SK.n)

class RSAFDHVRF:
    def __init__(self, Hash=SHA256.new, Hlen=32):
        self.Hash=Hash
        self.Hlen=Hlen

    def prove(self,K, alpha):
        EM=MGF1(alpha, K.k-1, self.Hlen, self.Hash)
        m=OS2IP(EM)
        s=RSASP1(K, m)
        pi=I2OSP(s, K.k)
        return pi

    def proof2hash(self,pi):
        beta=self.Hash(pi).digest()
        return beta

    def verify(self,PK, alpha, pi):
        s=OS2IP(pi)
        m=RSAVP1(PK,s)
        EM=I2OSP(m, PK.k-1)
        EM_=MGF1(alpha,PK.k-1, self.Hlen, self.Hash)
        if OS2IP(EM) == OS2IP(EM_):
            return True
        else:
            return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "USAGE: python vrf.py [plaintext]"
        exit(1)
    kf = RSAImplementation()
    keyPair = kf.generate(1024)
    pubkey = PublicKeyPrim(keyPair.e, keyPair.n)
    privkey= PrivateKeyPrim(keyPair.d, keyPair.n)
    alpha = ''.join(sys.argv[1:])
    VRF = RSAFDHVRF()
    pi = VRF.prove(privkey, alpha)
    beta = VRF.proof2hash(pi)
    if VRF.verify(pubkey, alpha, pi) :
        print("Valid")
    else :
        print("Invalid")

