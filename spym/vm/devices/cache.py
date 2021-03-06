# Copyright (c) 2009 Vicent Marti
# 
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

import sys, random
from spym.common.utils import _debug
    
class CacheLine(object):
    def __init__(self, cache_ptr, replacementPolicy):
        # control
        self.valid = 0
        self.label = 0
        self.dirty = 0
        self.counter = 0
        self.start_addr = None
        self.cache = cache_ptr
        self.policy = replacementPolicy
        
        # data (we store words here)
        self.contents = [0x0, ] * (cache_ptr.blocksize // 4)
        
    def setCounters(self):
        self.counter = 0
        startl = self.start_addr // self.cache.blocksize
        startl = startl % self.cache.total_sets
        startl = startl * self.cache.set_size
        
        for line in self.cache.cache[startl : startl + self.cache.set_size]:
            if line is not self:
                line.counter += 1
        
    def loadFromMemory(self, start_addr):
        self.start_addr = start_addr
        self.dirty = 0
        self.valid = 1
        self.label = self.cache.getLabel(start_addr)
        
        for i in range(len(self.contents)): self.contents[i] = \
            self.cache.memory[start_addr + i * 0x4, 4]
            
        if self.policy == 'FIFO':
            self.setCounters()
        
    def getContents(self):
        if self.policy == 'LRU':
            self.setCounters()
            
        return self.contents
    
    def control(self):
        return self.label, self.valid, self.dirty, self.counter
        
    def writeBack(self):
        for (offset, word) in enumerate(self.contents):
            self.cache.memory[self.start_addr + offset * 0x4, 4] = word
        
    def writeContents(self, word_in_block, word_desp, size, data):
        word = self.contents[word_in_block]
        word &= ~(BaseCache.SIZE_MASKS[size] << (word_desp * 8))
        word |= ((data & BaseCache.SIZE_MASKS[size]) << (word_desp * 8))
        
        if self.policy == 'LRU':
            self.setCounters()
            
        self.contents[word_in_block] = word
        self.dirty = 1
        self.valid = 1
    
class BaseCache(object):
    SIZE_MASKS = [None, 0xFF, 0xFFFF, None, 0xFFFFFFFF]
    
    def __init__(self, cache_name, memory_ptr, blockSize,
                waySize, numberOfLines, writePolicy_hit,
                writePolicy_miss, replacementPolicy):
        """
Base cache constructor.

    memory_ptr: 
        Reference for the secondary memory which will be used as a fallback 
        for the cache. May be another cache of a higher level, or the main 
        memory.
        
    blockSize: 
        Size (in bytes) of a memory block. Usually 4 or 8 words (16 or 32 
        bytes) on the MIPS R2000 standard.
        
    waySize: 
        Number of ways for multiple-associative caches.
        
    numberOfLines: 
        Total number of lines in the cache (each line holds one block of 
        memory)
    
    writePolicy_hit: 
        Resolution policy for writing a 'hit' on the cache.
        
        - 'write-back': 
            Data is written on the cache line, and then copied 
            to memory when such line is replaced.
            
        - 'write-through': 
            Data is written both in the cache line and in memory 
            simultaneously.
    
    writePolicy_miss: 
        Resolution policy for writing a 'miss' on the cache
        
        - 'write-allocate': 
            Bring the memory block into a local line, then write into it.
            
        - 'write-noallocate': 
            Completely skip the cache and write on memory.
        
    replacementPolicy: 
        Policy taken for block replacement on a collision.
        
        - 'LRU': Remove the least recently used line.
        - 'FIFO': Remove the line which came first (the oldest) from memory.
        - 'random': Randomly choose a line to remove
        
NOTE ON CACHE MODES:
    This is a generic cache which simulates all three addressing modes.
    
    To use a 'direct' mapping, set the desired number of lines, and set the
    number of ways to 1.
    
    To use a 'multi-way' (i.e. 2-way or 4-way) mapping, set the number of 
    lines and the number of ways to their desired values.
    
    To use a 'fully associative' map, set the number of lines and the number
     of ways to the same value.
        """
        self.cache_name = cache_name
        self.memory = memory_ptr
        self.linecount = numberOfLines
        self.total_sets = numberOfLines // waySize
        self.set_size = waySize
        self.blocksize = blockSize
        
        assert(writePolicy_hit in ('write-back', 'write-through'))
        assert(writePolicy_miss in ('write-allocate', 'write-noallocate'))
        assert(replacementPolicy in ('LRU', 'FIFO', 'random'))
            
        self.writePolicy_hit = writePolicy_hit
        self.writePolicy_miss = writePolicy_miss
        self.replacementPolicy = replacementPolicy
        
        self.cache = [CacheLine(self, self.replacementPolicy)
                      for i in range(numberOfLines)]
        
    def __str__(self):
        """
        Build a visual representation of the cache's contents to use with 
        str() methods.
        """
        output = "[%s] - %d lines, %d bytes/block (%dB of storage)\n" % (
            self.linecount, self.blocksize, self.linecount * self.blocksize)
    
        output += "-".ljust(85, '-') + "\n"
        output += ("|   LINE | VALID | DIRTY "
                   "|LABEL  | COUNTER | CONTENTS").ljust(85)
        output += "|\n"
        output += "-".ljust(85, '-') + "\n"
        
        for line_co, line in enumerate(self.cache):
            data = line.contents
            data.reverse()
            label, valid_bit, dirty_bit, counter = line.control()
            
            if (line_co and self.set_size > 1 and not 
                line_co % self.set_size):
                output += "-".ljust(85, '-') + "\n"
                
            output += "| %6d | %5d | %5d | %8X | %7d | " % (
                line_co, valid_bit, dirty_bit, label, counter)
                
            output += "%08X %08X %08X %08X |\n" % tuple(data)
            
        output += "-".ljust(85, '-') + "\n"
        return output
        
    def getLabel(self, address):
        """
        Return the LABEL part of a given address.
        """
        block = address // self.blocksize
        return block // self.total_sets
        
    def buildDataReturn(self, block, address, size):
        """
        Extracts the required data from a Memory Block.
        
            block: Memory block, straight from a cache line.
            
            address: Address used to obtain such block (i.e. 
                pointing to one of the words inside the block)
            
            size: Byte size of the data to extract (1, 2 or 4 for byte, 
            half or word).
            
            Returns: the integer inside 'block' of 'size' bytes pointed 
            by 'address'
        """
        subword_offset = address % 4
        word_in_block = (address % self.blocksize) // 4
        word = block[word_in_block]

        if not subword_offset and size == 4:
            return word

        return (word >> (subword_offset * 8)) & self.SIZE_MASKS[size]
        
    def bringFromMemory(self, address):
        """
        Brings a memory block from main memory and stores it in its 
        corresponding cache line.
            
            address: Address to bring (may be unaligned, the cache will 
            load the whole block containing the address)
            
            Returns: The contents of the new block.
        """
        target_line = self.findEmptyLine(address)
        if  target_line.valid and target_line.dirty and \
            self.writePolicy_hit == 'write-back':
            target_line.writeBack()
            
        start_addr = (address // self.blocksize) * self.blocksize
        target_line.loadFromMemory(start_addr)

        return target_line.getContents()
        
    def findEmptyLine(self, address):
        """
        Finds an empty line where a new memory block can be stored. If none 
        are available, the selected replacement algorithm will drop one for 
        use anyway.
            
            address: The address of the block which needs 
            to be placed inside the line.
            
            Returns: A reference to the CacheLine object which may be used
            for the storage of a new block.
        """
        block = address // self.blocksize
        line_set = block % self.total_sets

        line_start = line_set * self.set_size
        fullset = self.cache[line_start : line_start + self.set_size]
        highest_id = fullset[0]

        for line in fullset:
            if line.counter > highest_id.counter:
                highest_id = line

            if not line.valid:
                return line

        if self.replacementPolicy == 'random':
            return random.choice(fullset)
            
        return highest_id
        
    def findLineForAddress(self, address):
        """
        Finds the cache line which contains the specified address.
        
            Returns: The line number, if the address is found in the cache, 
            'None' otherwise.
        """
        block = address // self.blocksize
        line_set = block % self.total_sets

        line_start = line_set * self.set_size
        for i in range(self.set_size):
            ctrl = self.cache[line_start + i].control()
            label, valid_bit, _, _ = ctrl

            if valid_bit and label == self.getLabel(address):
                return (line_start + i)

        return None

    def getData(self, address, size):
        """
        Read 'size' bytes of data of 'address' from the cache. Handle hits 
        and misses.
        """
        dest_line = self.findLineForAddress(address)
        if dest_line is None:
            data = self.bringFromMemory(address)
        else:
            data = self.cache[dest_line].getContents()

        return self.buildDataReturn(data, address, size)
        
    def setData(self, address, size, data):
        """
        Write 'size' bytes with 'data' in 'address' in the cache.
        """
        dest_line = self.findLineForAddress(address)
        word_in_block = (address % self.blocksize) // 4
        
        if dest_line is None:
            # resolve writing miss with or without allocation
            if self.writePolicy_miss == 'write-allocate':
                self.bringFromMemory(address)
                dest_line = self.findLineForAddress(address)
                
                self.cache[dest_line].writeContents(
                    word_in_block,
                    address % 4,
                    size, data)

            elif self.writePolicy_miss == 'write-noallocate':
                self.memory[address, size] = data
                
        else:
            # always write on cache
            self.cache[dest_line].writeContents(
                word_in_block,
                address % 4,
                size, data)
            
            # if this is write-through, write on memory, 
            # otherwise wait until 
            # removal for writing
            if self.writePolicy_hit == 'write-through':
                self.memory[address, size] = data
        
    def __getitem__(self, address_tuple):
        address, size = address_tuple
        return self.getData(address, size)

    def __setitem__(self, address_tuple, data):
        address, size = address_tuple
        self.setData(address, size, data)
        
class MIPSCache_TEMPLATE(BaseCache):
    def __init__(self,
                 cacheName,
                 block_size,
                 cacheMapping,
                 numberOfLines,
                 sizeOfWay = None,
                 writePolicy_hit = 'write-back',
                 writePolicy_miss = 'write-allocate',
                 replacementPolicy = 'FIFO'):
                
        if cacheMapping is 'direct':
            sizeOfWay = 1
        elif cacheMapping is 'associative':
            sizeOfWay = numberOfLines
            
        BaseCache.__init__(self,
            cacheName, None, block_size,
            sizeOfWay, numberOfLines,
            writePolicy_hit, writePolicy_miss,
            replacementPolicy)
