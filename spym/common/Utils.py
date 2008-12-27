def u32(i):
	return i & 0xFFFFFFFF
	
def u16(i):
	return i & 0xFFFF
	
def u8(i):
	return i & 0xFF

def s32(i):
	return (i + (1 << 31)) % (1 << 32) - (1 << 31)

def s16(i):
	return (i + (1 << 15)) % (1 << 16) - (1 << 15)	
	
def s8(i):
	return (i + (1 << 7)) % (1 << 8) - (1 << 7)
	
def extsgn(i, size):
	size = (size * 8) - 1
	return (i + (1 << size)) % (1 << (size + 1)) - (1 << size)
	

def bin(n, count=24):
    """returns the binary of integer n, using count number of digits"""
    return "".join([str((n >> y) & 1) for y in range(count-1, -1, -1)])

FILTER=''.join([(len(repr(chr(x)))==3) and chr(x) or '.' for x in range(256)])

def bindump(src, offset = 0, length = 16):
    N=offset; result=''
    while src:
       s,src = src[:length],src[length:]
       hexa = ' '.join(["%02X"%ord(x) for x in s])
       s = s.translate(FILTER)
       result += "0x%08X | %-*s | %s\n" % (N, length*3, hexa, s)
       N+=length
    return result
