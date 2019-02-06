import sys

SAFE       = 1000
SAFE_UPPER = 1500
UNSAFE     = 2000  # Be ware of overflows...
DANGER     = 4000

sys.setrecursionlimit(DANGER)
DEBUG = False
