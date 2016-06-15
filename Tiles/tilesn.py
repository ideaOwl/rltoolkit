"""
Tiling routines

External documentation and recommendations on the
use of this code is # available at
http://rlai.cs.ualberta.ca/RLAI/RLtoolkit/tiles.html

This is an implementation of grid-style tile codings, _based originally on
the UNH CMAC code (see http://www.ece.unh.edu/robots/cmac.htm). 
Here we provide a function, "getTiles", that maps floating and integer
variables to a list of tiles. This function is memoryless and requires no
setup...but only if hashing collisions are to be ignored.  This is a second 
version that optionally checks for hashing collisions and handles them appropriately
to simulate an infinite, accurate memory.  (Until we run out of memory
of course.)  We use open addressing with double hashing indexing.
Memory-size must be a power of 2.  

The float variables will be gridded at unit intervals, so generalization
will be by approximately 1 in each direction, and any scaling will have 
to be done externally before calling tiles.

It is recommended by the UNH folks that numtilings be a power of 2, e.g., 16. 

Useful routines and classes:
       CollisionTable(size,safety) or makeCtable(size,safety)
           size is optional and must be a power of 2 (defaults to 2048)
           safety - optional (defaults to safe)
              'unsafe': note the number of collisions, but don't handle them
              'safe': keeps an extra hash numbers to check for collisions; it is possible (although
                  unlikely) that a collision will be determined to be a simple hit instead
              'super safe': keep whole list for comparison in collisions; more memory but safer

       tiles(numtilings, memctable, floats, ints)
       loadtiles(tiles, startelement, numtilings, memctable, floats, ints)
           both of these routines prepare numTiling tiles
               getTiles returns them as a list
               loadTiles loads them into array tiles starting from position startelement
           if memctable is a CollisionTable, 
               hashing collisions are checked for and handled
               otherwise it must be an integer power of 2 and collisions are ignored
           floats is a list of real variables to be tiled
           ints is an optional list of integer variables to be tiled
       tileswrap(numtilings, memctable, floats, wrapwidths, ints)
       loadtileswrap(tiles, startelement, numtilings, memctable, floats, wrapwidths ints)
           arguments are the same as above except for the addition of
           wrapwidths - which specifies for each float the width of the range over
              which it wraps (e.g., 2pi). If you don't want a float to wrap, it's wrap-width
              should be zero. The wrapping width is in the same units as the floats, but an integer
"""

import random 
import math
from numarray import *

_maxnumfloats = 20                      # maximum number of variables used in one grid
_maxLongint = 2147483647                # maximum integer
_maxLongintBy4 = _maxLongint // 4       # maximum integer divided by 4   
_randomTable = array([random.randrange(65536) for i in range(2048)])   #table of random numbers

# The following are temporary variables used by tiles.
_qstate = zeros([_maxnumfloats]) #[0 for i in xrange(_maxnumfloats)]
_base = zeros([_maxnumfloats]) #[0 for i in xrange(_maxnumfloats)]
_coordinates = zeros([1+2*_maxnumfloats])  #[0 for i in xrange(1 + 2*_maxnumfloats)]

class CollisionTable:
    "Structure to handle collisions"
    def __init__(self, sizeval=2048, safetyval='safe'):
        # if not power of 2 error
        if not powerOf2(sizeval):
                print("error - size should be a power of 2")
        self.size = sizeval                        
        self.safety = safetyval            # one of 'safe', 'super safe' or 'unsafe'
        self.calls = 0
        self.clearhits = 0
        self.collisions = 0
        self.data = zeros([self.size]) - 1 #array([-1 for i in xrange(self.size)])

    def __str__(self):
        "Prepares a string for printing whenever this object is printed"
        return "Collision table: " + \
               " Safety : " + self.safety + \
               " Usage : " + str(self.usage()) + \
               " Size :" + str(self.size) + \
               " Calls : "+ str(self.calls) + \
               " Collisions : " + str(self.collisions)
    

    def print_ (self):
        "Prints info about collision table"
        print(("usage", self.usage(), "size", self.size, "calls", self.calls, "clearhits", self.clearhits, \
                        "collisions", self.collisions, "safety", self.safety))

    def reset (self):
        "Reset Ctable values"
        self.calls = 0
        self.clearhits = 0
        self.collisions = 0
        self.data = zeros([self.size]) - 1 #[-1 for i in xrange(self.size)]
    
    def stats (self):
        "Return some statistics of the usage of the collision table"
        return self.calls, self.clearhits, self.collisions, self.usage

    def usage (self):
        "count how many entries in the collision table are used"
        use = 0
        for d in self.data:
            if d >= 0:
                use += 1
        return use

def startTiles (numtilings, floats, ints=[]):
    "Does initial assignments to _coordinates, _base and _qstate for both GetTiles and LoadTiles"
    global _coordinates, _base, _qstate
    numfloats = len(floats)
    i = numfloats + 1                   # starting place for integers
    for v in ints:                      # for each integer variable, store it
        _coordinates[i] = v             
        i += 1
    i = 0
    for float in floats:                # for real variables, quantize state to integers
        _base[i] = 0
        _qstate[i] = int(math.floor(float * numtilings))
        i += 1
        
def fixcoord (numtilings, numfloats, j):
    "Fiddles with _coordinates and _base - done once for each tiling"
    global _coordinates, _base, _qstate
    for i in range(numfloats):          # for each real variable
        if _qstate[i] >= _base[i]:
            _coordinates[i] = _qstate[i] - ((_qstate[i] - _base[i]) % numtilings)
        else:
            _coordinates[i] = _qstate[i]+1 + ((_base[i] - _qstate[i] - 1) % numtilings) - numtilings
        _base[i] += 1 + 2*i
    _coordinates[numfloats] = j
    
def hashtile (numtilings, memctable, numcoord):
    "Chooses hashing method and applies"
    global _coordinates
    if isinstance(memctable, CollisionTable):
        hnum = hash(_coordinates, numcoord, memctable)
    else:
        hnum = hashUNH(_coordinates, numcoord, memctable)
    return hnum

def hashUNH (ints, numInts, m, increment=449):
    "Hashing of array of integers into below m, using random table"
    res = 0
    for i in range(numInts):
        res += _randomTable[(ints[i] + i*increment) % 2048] 
    return res % m

def hash (ints, numInts, ct):
    "Returns index in collision table corresponding to first part of ints (an array)"
    ct.calls += 1
    memSize = ct.size
    j = hashUNH(ints, numInts, memSize)
    if ct.safety == 'super safe':
        ccheck = ints[:]                # use whole list as check
    else:                               # for safe or unsafe, use extra hash number as check
        ccheck = hashUNH(ints, numInts, _maxLongint, 457)
    if ccheck == ct.data[j]:            # if new data same as saved data, add to hits
        ct.clearhits += 1
    elif ct.data[j] < 0:                # first time, set up data
        ct.clearhits += 1
        ct.data[j] = ccheck
    elif ct.safety == 'unsafe':         # collison, but we don't care   
        ct.collisions += 1
    else:                               # handle collision - rehash
        h2 = 1 + 2*hashUNH(ints, numInts, _maxLongintBy4)
        i = 1
        while ccheck != ct.data[j]:     # keep looking for a new spot until we find an empty spot
            ct.collisions += 1
            j = (j + h2) % memSize
            if i > memSize:             # or we run out of space 
                print("Tiles: Collision table out of memory")
                return -1               # force it to stop if out of memory
            if ct.data[j] < 0:          
                ct.data[j] = ccheck
            i += 1
    return j

def powerOf2 (n):
    lgn = math.log(n, 2)
    return (lgn - math.floor(lgn)) == 0

def mod(num, by):
    if num >= 0:
        return num % by
    else:
        return (by + (num % by)) % by
    
def fixcoordwrap(numtilings, numfloats, j, wrapwidths):
    global _widthxnumtilings, _qstate, _base, _coordinates
    for i in range(numfloats):  # loop over each relevant dimension
        # find coordinates of activated tile in tiling space 
        if _qstate[i] >= _base[i]:
            _coordinates[i] = _qstate[i] - ((_qstate[i] - _base[i]) % numtilings)
        else:
            _coordinates[i] = _qstate[i]+1 + ((_base[i] - _qstate[i] - 1) % numtilings) - numtilings
        if wrapwidths[i] != 0:
            _coordinates[i] = mod(_coordinates[i], _widthxnumtilings[i])
        _base[i] += 1 + (2 * i) # compute displacement of next tiling in quantized space 
    _coordinates[numfloats] = j # add indices for tiling and hashing_set so they hash differently
    
def tiles (numtilings, memctable, floats, ints=[]):
    """Returns list of numtilings tiles corresponding to variables (floats and ints),
        hashed down to memSize, using ctable to check for collisions"""
    numfloats = len(floats)
    numcoord = 1 + numfloats + len(ints)
    startTiles (numtilings, floats, ints)
    tlist = []
    for j in range(numtilings):             # for each tiling
        fixcoord(numtilings, numfloats, j)
        hnum = hashtile(numtilings, memctable, numcoord)
        tlist.append(hnum)
    return tlist

def loadtiles (tiles, startelement, numtilings, memctable, floats, ints=[]):
    """Loads numtilings tiles into array tiles, starting at startelement, corresponding
       to variables (floats and ints), hashed down to memSize, using ctable to check for collisions"""
    numfloats = len(floats)
    numcoord = 1 + numfloats + len(ints)
    startTiles (numtilings, floats, ints)
    for j in range(numtilings):
        fixcoord(numtilings, numfloats, j)
        hnum = hashtile(numtilings, memctable, numcoord)
        tiles[startelement + j] = hnum
        
def tileswrap(numtilings, memsize, floats, wrapwidths, ints=[]):
    """Returns list of numtilings tiles corresponding to variables (floats and ints),
        hashed down to memSize, using ctable to check for collisions - wrap version"""
    global _widthxnumtilings
    numfloats = len(floats)
    numcoord = 1 + numfloats + len(ints)
    tiles = []
    startTiles (numtilings, floats, ints)
    _widthxnumtilings = fromfunction(lambda i: wrapwidths[i] * numtilings, [numfloats])
        #array([wrapwidths[i] * numtilings for i in xrange(numfloats)])
    for j in  range(numtilings):
        fixcoordwrap(numtilings, numfloats, j, wrapwidths)
        hnum = hashtile(numtilings, memsize, numcoord)
        tiles.append(hnum)
    return tiles

def loadtileswrap(tiles, startelement, numtilings, memsize, floats, wrapwidths, ints=[]):
    """Returns list of numtilings tiles corresponding to variables (floats and ints),
        hashed down to memSize, using ctable to check for collisions - wrap version"""
    global _widthxnumtilings
    numfloats = len(floats)
    numcoord = 1 + numfloats + len(ints)
    startTiles (numtilings, floats, ints)
    _widthxnumtilings = fromfunction(lambda i: wrapwidths[i] * numtilings, [numfloats])
    #_widthxnumtilings = array([wrapwidths[i] * numtilings for i in xrange(numfloats)])
    for j in range(numtilings):
        fixcoordwrap(numtilings, numfloats, j, wrapwidths)
        hnum = hashtile(numtilings, memsize, numcoord)
        tiles[startelement + j] = hnum

getTiles = tiles
loadTiles = loadtiles
