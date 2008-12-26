

class AssemblyPreprocessor(object):
	
	class InvalidDirective(Exception):
		pass
		
	class InvalidParameterCount(Exception):
		pass
	
	class InvalidParameter(Exception):
		pass
	
	def __init__(self, parser, memory):
		self.parser = parser
		self.memory = memory
		
		self.align = None
		
	def __call__(self, identifier, args, cur_address):
		func = 'dir_' + identifier[1:]
		
		if not hasattr(self, func):
			raise self.InvalidDirective("Unknown instruction: %s" % func)
		
		return getattr(self, func)(args, cur_address) or cur_address
		
	def __checkArgs(self, args, _min = None, _max = None, _count = None):
		argcount = len(args)
		
		if  (_min is not None and argcount < _min) or \
			(_max is not None and argcount > _max) or \
			(_count is not None and argcount != _count):
			raise self.InvalidParameterCount
		
	def __segmentChange(self, args, segment):
		self.__checkArgs(args, _max = 1)
		
		if not args:
			return self.memory.getNextFreeBlock(self.memory.SEGMENT_DATA[segment][0])
			
		try:
			address = int(args[0], 0)
		except ValueError:
			raise self.InvalidParameter("Invalid address: '%s'" % args[0])
		
		if self.memory.getSegment(address) != segment:
			raise self.InvalidParameter("Address %X doesn't belong to the %s segment." % (address, segment))
		
		return address
		
	def __assembleString(self, string, address, nullterm):
		if not string[0] == '"' or not string[-1] == '"':
			raise self.InvalidParameter("Malformed string constant.")
			
		string = string[1:-1].decode('string_escape')
		
		for c in string:
			self.memory[address, 1] = ord(c) & 0xFF
			address += 1
			
		if nullterm:
			self.memory[address, 1] = 0x0
			address += 1
			
		return address
		
	def __assembleData(self, data, size, address):
		if self.align is None:
			address += address % size
		else:
			address += address % (2 ** self.align)
		
		self.align = None
		try:
			for d in data:
				if len(d) == 3 and d[0] == "'" and d[2] == "'":
					d = ord(d[1])
				else:
					d = int(d, 0)
					
				self.memory[address, size] = d
				address += size
		
		except ValueError:
			raise self.InvalidParameter("Invalid integer constants for data assembly: '%s'" % d)
			
		return address
		
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
			raise self.parser.LabelException("Global label redefinition.")
			
		self.parser.global_labels[label] = None
		
	def dir_extern(self, args, cur_address):
		pass # TODO. what the fuck is this?
		
	def dir_align(self, args, cur_address):
		self.__checkArgs(args, _count = 1)
		
		try:
			self.alignment = int(args[0], 0)
		except ValueError:
			raise self.InvalidParameter("Invalid value for alignment.")
	
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
			raise self.InvalidParameter("Invalid space value.")

		return self.__assembleData(['0',] * space_count, 1, cur_address)