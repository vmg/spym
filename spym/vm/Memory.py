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
			self.contents = 0x0
			
		def getData(self, size, offset):
			assert(offset <= self.BLOCK_SIZE)				
			return (self.contents >> (offset * 8)) & self.SIZE_MASKS[size]
			
		def setData(self, size, offset, value):
			assert(offset <= self.BLOCK_SIZE)
			self.contents = self.contents & ~(self.SIZE_MASKS[size] << (offset * 8))
			self.contents = self.contents | ((value & self.SIZE_MASKS[size]) << (offset * 8))
			
	class CodeBlock(object):
		def __init__(self, blockSize):
			self.inst_count = blockSize // 4
			self.contents = [None, ] * self.inst_count
			
		def setData(self, size, offset, value):
			if size != 4 or offset % 4:
				raise MemoryManager.UnalignedMemoryAccess
			
			self.contents[offset // 4] = value
			
		def getData(self, size, offset):
			if size != 4 or offset % 4:
				raise MemoryManager.UnalignedMemoryAccess
			
			return self.contents[offset // 4] or 0x0
	
	def __init__(self, vm, blockSize):
		self.BLOCK_SIZE = blockSize
		self.vm = vm
		self.memory = {}
		
	def __allocate(self, address):
		if 'text' in self.getSegment(address):
			newBlock = self.CodeBlock(self.BLOCK_SIZE)
		else:
			newBlock = self.MemoryBlock(self.BLOCK_SIZE)

		self.memory[address // self.BLOCK_SIZE] = newBlock
	
	def __contains__(self, address):
		return (address // self.BLOCK_SIZE) in self.memory
		
	def __getData(self, address, size, binary = True):
		if 	(address % size) or (not self.MIN_ADDRESS <= address <= self.MAX_ADDRESS):
			raise self.vm.MIPS_Exception('ADDRL', badaddr = address)
			
		if self.vm.getAccessMode() == 'user' and not self.USER_READ_SPACE[0] <= address <= self.USER_READ_SPACE[1]:
			raise self.vm.MIPS_Exception('ADDRL', badaddr = address) # FIXME: is this the right exception?
		
		if not self.__contains__(address):
			return 0x0
		
		data = self.memory[address // self.BLOCK_SIZE].getData(size, address % self.BLOCK_SIZE)
		return data.mem_content if binary and hasattr(data, 'mem_content') else data
		
		
	def __setData(self, address, size, data):
		if 	(address % size) or (not self.MIN_ADDRESS <= address <= self.MAX_ADDRESS):
			raise self.vm.MIPS_Exception('ADDRS', badaddr = address)
			
		if self.vm.getAccessMode() == 'user' and not self.USER_WRITE_SPACE[0] <= address <= self.USER_WRITE_SPACE[1]:
			raise self.vm.MIPS_Exception('ADDRS', badaddr = address) # FIXME: is this the right exception?
		
		if not self.__contains__(address):
			self.__allocate(address)
			
		destinationBlock = self.memory[address // self.BLOCK_SIZE]
		
		if hasattr(data, '__call__') and not isinstance(destinationBlock, self.CodeBlock):
			raise AssemblyParser.ParserException("Cannot assemble instructions in data-only segments.")
			
		self.memory[address // self.BLOCK_SIZE].setData(size, address % self.BLOCK_SIZE, data)
	
	def getInstruction(self, address):
		return self.__getData(address, 4, False)
		
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
			contents = self.memory[address // self.BLOCK_SIZE].contents
			if (isinstance(contents, int) and contents == 0) or not any(contents):
				return address
			
			address += self.BLOCK_SIZE
			
		return address
				
		
	def getInstructionData(self):
		for block in self.memory.values():
			if isinstance(block, self.CodeBlock):
				for ins in block.contents:
					if ins: yield ins
	
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
				
			if isinstance(block, self.CodeBlock):			
				for i in range(self.BLOCK_SIZE // 4):
					ins = block.contents[i]
					if ins:
						output += "[0x%08X]    " % (address + i * 4)
						output += "0x%08X  " % ins.mem_content
						
						text_output = ins.text.ljust(30) + "; " + ins.orig_text
						output += text_output + "\n"
						
			elif isinstance(block, self.MemoryBlock):
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
		data_contents = []
		text_contents = []
		
		for (address, block) in self.memory.items():
			if isinstance(block, self.MemoryBlock):
				data_contents.append(address)
			elif isinstance(block, self.CodeBlock):
				text_contents.append(address)
				
		memContents = "MIPS R2000 Virtual Memory\n"
		memContents += "  * 4GB addressing space\n"
		memContents += "  * %d blocks allocated (%d data blocks, %d text blocks)\n" % (len(self.memory), len(data_contents), len(text_contents))
		memContents += "  * Block Size set at %d Bytes (%d Words per block)\n" % (self.BLOCK_SIZE, self.BLOCK_SIZE // 4)
		
		if self.memory:
			memContents += "  * Block data:\n"
			memContents += self.__str_Segments(text_contents + data_contents) + "\n"
			
		return memContents
	
