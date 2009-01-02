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

from spym.common.utils import _debug

class AssemblyPreprocessor(object):
	
	class PreprocessorException(Exception):
		pass
		
	def __init__(self, parser, memory):
		self.parser = parser
		self.memory = memory
		
		self.align = None
		self.lastSegmentAddr = {}
		
	def __call__(self, identifier, args, cur_address):
		func = 'dir_' + identifier[1:]
		
		if not hasattr(self, func):
			raise self.PreprocessorException(
				"Unknown preprocessor directive: %s" % func)
		
		return 	(getattr(self, func)(args, cur_address) or
				(cur_address, cur_address))
		
	def __checkArgs(self, args, _min = None, _max = None, _count = None):
		argcount = len(args)
		
		if  (_min is not None and argcount < _min) or \
			(_max is not None and argcount > _max) or \
			(_count is not None and argcount != _count):
			raise self.PreprocessorException(
				"Wrong parameter count in preprocessor directive.")
		
	def __segmentChange(self, args, segment):
		self.__checkArgs(args, _max = 1)
		self.align = None
		
		if not args:
			if segment in self.lastSegmentAddr:
				block_start = self.lastSegmentAddr[segment]
			else:
				block_start = self.memory.SEGMENT_DATA[segment][0]
				
			address = self.memory.getNextFreeBlock(block_start)
		else:	
			try:
				address = int(args[0], 16)
			except ValueError:
				raise self.PreprocessorException(
					"Invalid address: '%s'" % args[0])
		
			if self.memory.getSegment(address) != segment:
				raise self.PreprocessorException(
					"Address %X doesn't belong to the %s segment." % 
						(address, segment))
		
		self.lastSegmentAddr[segment] = address
		return (address, address)
		
	def __assembleString(self, string, address, nullterm):
		if not string[0] == '"' or not string[-1] == '"':
			raise self.PreprocessorException("Malformed string constant.")
			
		original_address = address
		string = string[1:-1]
		string = string.replace(r'\n', '\n')
		string = string.replace(r'\"', '"')
		string = string.replace(r'\t', '\t')
		
		for c in string:
			self.memory[address, 1] = ord(c) & 0xFF
			address += 1
			
		if nullterm:
			self.memory[address, 1] = 0x0
			address += 1
			
		return (original_address, address)
		
	def __assembleData(self, data, size, address):		
		if self.align is None:
			mod = address % size
		else:
			mod = address % (2 ** self.align)
			
		address += (4 - mod) if mod else 0
		original_address = address

		try:
			for d in data:
				if not d: continue
				if len(d) == 3 and d[0] == "'" and d[2] == "'":
					d = ord(d[1])
				elif d in self.parser.local_labels:
					d = self.parser.local_labels[d]
				else:
					d = int(d, 0)
					
				self.memory[address, size] = d
				address += size
		
		except ValueError:
			raise self.PreprocessorException(
				"Invalid integer constants for data assembly: '%s'" % d)
			
		return (original_address, address)
		
	def dir_set(self, args, cur_address):
		self.__checkArgs(args, _count = 1)
		if args[0] == 'noat':
			self.parser.instruction_assembler.assembly_regiser_protected = False
			
		elif args[0] == 'at':
			self.parser.instruction_assembler.assembly_regiser_protected = True
		
	def dir_data(self, args, cur_address):
		return self.__segmentChange(args, 'user_data')
	
	def dir_text(self, args, cur_address):
		return self.__segmentChange(args, 'user_text')
		
	def dir_kdata(self, args, cur_address):
		return self.__segmentChange(args, 'kernel_data')
			
	def dir_ktext(self, args, cur_address):
		return self.__segmentChange(args, 'kernel_text')
		
	def dir_globl(self, args, cur_address):
		self.__checkArgs(args, _count = 1)
		label = args[0]
		
		if label in self.parser.global_labels:
			raise self.PreprocessorException("Global label redefinition.")
			
		self.parser.global_labels[label] = None
		
	def dir_extern(self, args, cur_address):
		pass # TODO. what the fuck is this?
		
	def dir_align(self, args, cur_address):
		self.__checkArgs(args, _count = 1)
		
		try:
			self.alignment = int(args[0], 0)
		except ValueError:
			raise self.PreprocessorException("Invalid value for alignment.")
	
	def dir_ascii(self, args, cur_address):
		self.__checkArgs(args, _count = 1)
		return self.__assembleString(args[0], cur_address, False)
		
	def dir_asciiz(self, args, cur_address):
		self.__checkArgs(args, _count = 1)
		return self.__assembleString(args[0], cur_address, True)
		
	def dir_byte(self, args, cur_address):
		return self.__assembleData(args, 1, cur_address)

	def dir_half(self, args, cur_address):
		return self.__assembleData(args, 2, cur_address)
		
	def dir_word(self, args, cur_address):
		return self.__assembleData(args, 4, cur_address)
		
	def dir_space(self, args, cur_address):
		self.__checkArgs(args, _count = 1)
		
		try:
			space_count = int(args[0], 0)
		except ValueError:
			raise self.PreprocessorException("Invalid space value.")

		return self.__assembleData(['0',] * space_count, 1, cur_address)
