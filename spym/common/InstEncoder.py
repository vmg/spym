from spym.common.Utils import *

class InstructionEncoder(object):
	
	INSTRUCTIONS_R = [
		'add', 'addu', 'and', 'div', 'divu', 'mult', 'multu', 'nor', 
		'or', 'ori', 'sll', 'sllv', 'sra', 'srav', 'srl', 'srlv', 'sub', 
		'subu', 'xor', 'xori', 'slt', 'sltu', 'jalr', 'jr', 'mfhi',
		'mflo', 'mthi', 'mtlo', 'syscall', 'nop']
		
	INSTRUCTIONS_I = [
		'addi', 'addiu', 'andi', 'lui', 'slti', 'sltiu', 'beq', 
		'bgtz', 'blez', 'bgez', 'bne', 'lb', 'lbu', 'lh', 'lhu', 'lw', 'sb', 
		'bgezal', 'bltzal', 'bltz', 'sh', 'sw']
		
	INSTRUCTIONS_J = ['j', 'jal']
	
	OPCODES = {
		'add'	: '100000',
		'addu'	: '100001',
		'addi'	: '001000',
		'addiu' : '001001',
		'and'   : '100100',
		'andi'  : '001100',
		'div'   : '011010',
		'divu'  : '011011',
		'mult'  : '011000',
		'multu' : '011001',
		'nor'   : '100111',
		'or'    : '100101',
		'ori'   : '001101',  
		'sll'   : '000000',  
		'sllv'  : '000100',
		'sra'   : '000011',  
		'srav'  : '000111',
		'srl'   : '000010',  
		'srlv'  : '000110',
		'sub'   : '100010',  
		'subu'  : '100011',
		'xor'   : '100110',  
		'xori'  : '001110',
		'lui'	: '001111',
		'slt'   : '101010',  
		'sltu'  : '101001',
		'slti'  : '001010',
		'sltiu' : '001001',
		'beq'   : '000100',
		'bgez'	: '000001', 
		'bgezal': '000001',
		'bltzal': '000001',
		'bltz'	: '000001',
		'bgtz'  : '000111',
		'blez'  : '000110',
		'bne'   : '000101',
		'j'     : '000010',
		'jal'   : '000011',  
		'jalr'  : '001001',
		'jr'    : '001000',
		'lb'    : '100000',  
		'lbu'   : '100100',  
		'lh'    : '100001',  
		'lhu'   : '100101',  
		'lw'    : '100011',  
		'sb'    : '101000',  
		'sh'    : '101001',  
		'sw'    : '101011',  
		'mfhi'  : '010000',
		'mflo'  : '010010',
		'mthi'  : '010001',
		'mtlo'  : '010011',
		'syscall': '100110',
		'nop'	: '000000'
	}
	
	class EncodingError(Exception):
		pass
		
	def __init__(self):
		pass
		
	def __encode_R(self, s, t, d, a, f):
		return "000000" + bin(s, 5) + bin(t, 5) + bin(d, 5) + bin(a, 5) + f
		
	def __encode_I(self, o, s, t, i):
		return o + bin(s, 5) + bin(t, 5) + bin(i, 16)
	
	def __encode_J(self, o, i):
		return o + bin(i, 26)
		
	def __call__(self, ins_name, src1 = 0, src2 = 0, des = 0, shift = 0, imm = 0):
		
		if ins_name in self.INSTRUCTIONS_R:
			str_encoding = self.__encode_R(src1, src2, des, shift, self.OPCODES[ins_name])
		elif ins_name in self.INSTRUCTIONS_I:
			str_encoding = self.__encode_I(self.OPCODES[ins_name], src1, des, imm)
		elif ins_name in self.INSTRUCTIONS_J:
			str_encoding = self.__encode_J(self.OPCODES[ins_name], imm)
		else:
			raise self.EncodingError("Undefined instruction: '%s'" % ins_name)
			
		return int(str_encoding, 2) & 0xFFFFFFFF
		