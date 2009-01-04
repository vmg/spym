"""""
Copyright (c) 2009 Vicent Marti

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""""
import sys

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
    
def getFromWord(word_register, offset, size = 4):   
    offset = offset * 8
    mask = (1 << (size * 8)) - 1
    return (word_register >> offset) & mask
    
def breakAddress(address):
    size = 4
    if isinstance(address, tuple):
        address, size = address
    
    offset = address & 0x3
    address = address & ~0x3
    
    return (address, offset, size)

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

def _debug(msg):
    sys.stderr.write(msg)

def buildLineOfCode(address, instruction):
    RIGHT_MARGIN = 55
    if not hasattr(instruction, '_vm_asm'):
        return ''
        
    output = "[0x%08X]    0x%08X  %s" % (address, instruction, instruction.text)
    output = output.ljust(RIGHT_MARGIN) + "; "
    text, comment = instruction.orig_text, ""
    
    if '#' in instruction.orig_text:
        text, comment = text.split('#', 1)
        comment = ' # ' + comment.strip()

    output += text.strip().ljust(30) + comment
    
    return output + '\n'