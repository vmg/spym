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
from spym.common.utils import buildLineOfCode
from spym.vm.exceptions import MIPS_Exception
from spym.vm.devices.cache import MIPSCache_TEMPLATE

# class MemoryManager(object):
# 	def __init__(self, vm_ptr, L1_data_cache = {}, L1_code_cache = {}, L2_data_cache = {}, L2_code_cache = {}):
# 		self.main_memory = MainMemory(vm_ptr, 32) # default block size, 8 words
# 		
# 		if L1_code_cache and L1_data_cache:
# 			self.__initCache_Dual(1, L1_data_cache, L1_code_cache)
# 			
# 		elif L1_code_cache or L1_data_cache:
# 			self.__initCache_Unified(1, L1_data_cache or L1_code_cache)
# 			
# 			if L2_code_cache and L2_code_cache:
# 				self.__initCache_Dual(2, L2_data_cache, L2_code_cache)
# 			else:
# 				self.__initCache_Unified(2, L2_data_cache or L2_code_cache)
# 		
# 		
# 	def __initCache_Unified(self, level, cache_data):
# 		if not cache: return
# 		cache_instance = MIPSCache_TEMPLATE(self, **cache_data)
# 		
# 						
# 	def __initCache_Dual(self, level, data_cache, code_cache):
# 		
# 	def getInstruction(self, address):
# 		
# 	
# 	def __getitem__(self, address):
# 		if isinstance(address, tuple):
# 			address, size = address
# 			
# 		if 'text' in self.main_memory.getSegment(address):
			
		
			
		

class MemoryManager(object):
	SEGMENT_DATA = {
		'krnel_data_bottom':(0x00000000, 0x00400000 - 1),
		'user_text' : 		(0x00400000, 0x10000000 - 1),
		'user_data' : 		(0x10000000, 0x80000000	- 1),
		'kernel_text' : 	(0x80000000, 0x90000000 - 1),
		'kernel_data' : 	(0x90000000, 0xFFFFFFFF),
	}
	
	USER_READ_SPACE 	= (0x00400000, 0x7FFFFFFF)
	USER_WRITE_SPACE 	= (0x10000000, 0x7FFFFFFF)
		
	MIN_ADDRESS =		0x00000000
	MAX_ADDRESS =		0xFFFFFFFF
	
	SIZE_DICT = {
		'word' : 4,
		'half' : 2,
		'byte' : 1
	}

	class MemoryBlock(object):
		SIZE_MASKS = [None, 0xFF, 0xFFFF, None, 0xFFFFFFFF]
		
		def __init__(self, blockSize):
			self.BLOCK_SIZE = blockSize
			self.contents = [0x0, ] * (blockSize // 4)
			
		def getData(self, size, offset):
			assert(offset <= self.BLOCK_SIZE)
			
			word = self.contents[offset // 4]
			offset = offset % 4
							
			return word if not offset and size == 4 else (word >> (offset * 8)) & self.SIZE_MASKS[size]
			
		def setData(self, size, offset, value):
			assert(offset <= self.BLOCK_SIZE)
			
			word_offset = offset // 4
			offset = offset % 4
			
			if not offset and size == 4:
				self.contents[word_offset] = value
			else:
				self.contents[word_offset] &= ~(self.SIZE_MASKS[size] << (offset * 8))
				self.contents[word_offset] |=  ((value & self.SIZE_MASKS[size]) << (offset * 8))
	
	def __init__(self, vm, blockSize):
		self.BLOCK_SIZE = blockSize
		self.vm = vm
		self.memory = {}
		self.devices_memory_map = {}
		
	def __allocate(self, address):
		self.memory[address // self.BLOCK_SIZE] = self.MemoryBlock(self.BLOCK_SIZE)
	
	def __contains__(self, address):
		return (address // self.BLOCK_SIZE) in self.memory
		
	def __getData(self, address, size):
		if 	(address % size) or (not self.MIN_ADDRESS <= address <= self.MAX_ADDRESS):
			raise MIPS_Exception('ADDRL', badaddr = address)
			
		if self.vm and self.vm.getAccessMode() == 'user' and not self.USER_READ_SPACE[0] <= address <= self.USER_READ_SPACE[1]:
			raise MIPS_Exception('ADDRL', badaddr = address) # FIXME: is this the right exception?
			
		if address & ~0x3 in self.devices_memory_map:
			device = self.devices_memory_map[address]
			return device[address, size]
		
		if not self.__contains__(address):
			return 0x0
		
		return self.memory[address // self.BLOCK_SIZE].getData(size, address % self.BLOCK_SIZE)
		
		
	def __setData(self, address, size, data):
		if 	(address % size) or (not self.MIN_ADDRESS <= address <= self.MAX_ADDRESS):
			raise MIPS_Exception('ADDRS', badaddr = address, debug_msg = 'Invalid address %08X (%d)' % (address, size))
			
		if self.vm and self.vm.getAccessMode() == 'user' and not self.USER_WRITE_SPACE[0] <= address <= self.USER_WRITE_SPACE[1]:
			raise MIPS_Exception('ADDRS', badaddr = address, debug_msg = 'Attempted to write in protected space.') # FIXME: is this the right exception?
			
		if address & ~0x3 in self.devices_memory_map:
			device = self.devices_memory_map[address]
			device[address, size] = data
			return
		
		if not self.__contains__(address):
			self.__allocate(address)
			
		destinationBlock = self.memory[address // self.BLOCK_SIZE]
		
		if hasattr(data, '_vm_asm') and 'text' not in self.getSegment(address):
			raise AssemblyParser.ParserException("Cannot assemble instructions in data-only segments.")
			
		self.memory[address // self.BLOCK_SIZE].setData(size, address % self.BLOCK_SIZE, data)
		
	def getWord(self, address):
		return self.__getData(address, 4)
	
	def getHalf(self, address):
		return self.__getData(address, 2)
		
	def getByte(self, address):
		return self.__getData(address, 1)
		
	def setWord(self, address, data):
		return self.__setData(address, 4, data)
	
	def setHalf(self, address, data):
		return self.__setData(address, 2, data)
			
	def setByte(self, address, data):
		return self.__setData(address, 1, data)
		
	def getSegment(self, address):
		for (seg_name, seg_bounds) in self.SEGMENT_DATA.items():
			if seg_bounds[0] <= address <= seg_bounds[1]:
				return seg_name
		
		return None
		
	def getNextFreeBlock(self, address):		
		while address in self:
			block = self.memory[address // self.BLOCK_SIZE]
			if not any(block.contents):
				return address
			
			address += self.BLOCK_SIZE
			
		return address
		
	def getInstructionData(self):
		for (address, block) in self.memory.items():
			for (addr_offset, ins) in enumerate(block.contents):
				if hasattr(ins, '_vm_asm'): yield (address * self.BLOCK_SIZE + addr_offset * 0x4, ins)
	
	def clear(self):
		del(self.memory)
		self.memory = {}
	
	def __getitem__(self, address):		
		if isinstance(address, tuple):
			address, size = address
		elif address % 4 == 0: 	size = 4
		elif address % 2 == 0:	size = 2
		else:					size = 1
		
		return self.__getData(address, size)
		
	def __setitem__(self, address, data):		
		if isinstance(address, tuple):
			address, size = address
		elif address % 4 == 0: 	size = 4
		elif address % 2 == 0:	size = 2
		else:					size = 1
			
		return self.__setData(address, size, data)
		
	def __str_Segments(self, segments):
		segments.sort()
		current_section = None
		output = ""
		maxwords = self.BLOCK_SIZE // 4
		
		for seg in segments:
			address = seg * self.BLOCK_SIZE
			block = self.memory[seg]
			
			if current_section != self.getSegment(address):
				current_section = self.getSegment(address)
				output += "\n        %s\n" % current_section.upper()
			
			
			if 'text' in current_section:			
				for i in range(self.BLOCK_SIZE // 4):
					ins = block.contents[i]
					if hasattr(ins, '_vm_asm'):
						output += buildLineOfCode((address + i * 4), ins)
											
			elif 'data' in current_section:
				data = block.contents
				output += "[0x%08X..0x%08X]  " % ((address + self.BLOCK_SIZE - 4), address)
				
				if data == 0:
					output += "0x00000000"
				else:
					for i in range(maxwords):
						word = (data >> ((maxwords - i - 1) * 32))
						output += "0x%08x " % (word & 0xFFFFFFFF)
						
				output += '\n'
					
		return output				
		
	def __str__(self):				
		memContents = "MIPS R2000 Virtual Memory\n"
		memContents += "  * 4GB addressing space\n"
		memContents += "  * %d blocks allocated\n" % len(self.memory)
		memContents += "  * Block Size set at %d Bytes (%d Words per block)\n" % (self.BLOCK_SIZE, self.BLOCK_SIZE // 4)
		
		if self.memory:
			memContents += "  * Block data:\n"
			memContents += self.__str_Segments(text_contents + data_contents) + "\n"
			
		return memContents
	
