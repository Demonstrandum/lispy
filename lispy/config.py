import sys, os

SAFE       = 1000
SAFE_UPPER = 1500
UNSAFE     = 2000  # Be ware of overflows...
DANGER     = 4000

RECURSION_LIMIT = DANGER
sys.setrecursionlimit(RECURSION_LIMIT)


DEBUG = False
EXIT_ON_ERROR = True
RECOVERING_FROM_ERROR = False

COLORS = True
if os.name == 'nt':  # If we're on the Windows NT kernel:
    COLORS = False   #   Don't use colors. Because Windows is bad.
