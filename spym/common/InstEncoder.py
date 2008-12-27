from spym.common.Utils import *

class InstructionEncoder(object):	
	class EncodingError(Exception):
		pass
		
	def __init__(self, builder):
		self.builder = builder
		
	def __encode_R(self, s, t, d, a, f):
		return "000000" + bin(s, 5) + bin(t, 5) + bin(d, 5) + bin(a, 5) + f
		
	def __encode_I(self, o, s, t, i):
		return o + bin(s, 5) + bin(t, 5) + bin(i, 16)
	
	def __encode_J(self, o, i):
		return o + bin(i, 26)
		
	def encodeBinary(self, encoding, opcode, s, t, d, shift, imm):
		if encoding == 'R':
			str_encoding = self.__encode_R(s, t, d, shift, opcode)
		elif encoding == 'I':
			str_encoding = self.__encode_I(opcode, s, t, imm)
		elif encoding == 'J':
			str_encoding = self.__encode_J(opcode, imm)
			
		assert(len(str_encoding) == 32)
		
		return int(str_encoding, 2) & 0xFFFFFFFF

	def encodeText(self, ins_name, encoding, syntax, s, t, d, a, imm, label):
		if not syntax:
			return ins_name.lower()
			
		if encoding == 'J':
			imm = (imm << 2)
		
		syntax = syntax.replace('imm', r'%(imm)d').replace('label', r'0x%(imm)08X [%(label)s]')
		syntax = syntax.replace('$d', r'$%(d)d').replace('$s', r'$%(s)d').replace('$t', r'$%(t)d')
		syntax = syntax.replace('shift', r'%(a)d')
		return ins_name.lower() + " " + syntax % {'s' : s, 't' : t, 'd' : d, 'a' : a, 'imm' : imm, 'label' : label}
		
		
	def __call__(self, ins_closure, ins_name, s = 0, t = 0, d = 0, shift = 0, imm = 0, label = ""):
		encoding, _, opcode, syntax = self.builder.asm_metadata['ins_' + ins_name]
		
		binary_encoding = self.encodeBinary(encoding, opcode, s, t, d, shift, imm)
		text_encoding = self.encodeText(ins_name, encoding, syntax, s, t, d, shift, imm, label)
		
		setattr(ins_closure, 'mem_content', binary_encoding)
		setattr(ins_closure, 'text', text_encoding)
			
		
		