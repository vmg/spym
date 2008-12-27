import re
import pdb

from spym.common.Utils import *
from spym.common.InstEncoder import InstructionEncoder
from spym.vm.RegBank import RegisterBank

class InstBuilder(object):
	
	SYNTAX_DATA = {            
	    'arithlog'  :	('R', "$d, $s, $t"	),
	    'divmult'   :	('R', "$s, $t"		),
	    'shift'    	:	('R', "$d, $t, shift"),
	    'shiftv'  	:	('R', "$d, $t, $s"	),
	    'jumpr'    	:	('R', "$s"			),
	    'movefrom'	:	('R', "$d"			),
	    'moveto'	:	('R', "$s"			),
	    'arithlogi'	:	('I', "$t, $s, imm"	),
	    'loadi'		:	('I', "$t, imm"		),
	    'branch'	:	('I', "$s, $t, label"),
	    'branchz'	:	('I', "$s, label"	),
	    'loadstore'	:	('I', "$t, imm($s)"	),
	    'jump'		:	('J', "label"		),
	    'none'		:	('R', ""			),
	  }
	
	class InvalidRegisterName(Exception):
		pass
		
	class WrongArgumentCount(Exception):
		pass
		
	class UnknownInstruction(Exception):
		pass
		
	class InvalidParameter(Exception):
		pass
		
	class SyntaxException(Exception):
		pass
		
	def __init__(self):
		self.encoder = InstructionEncoder(self)
		self.__initMetaData()
		
	def __initMetaData(self):
		self.asm_metadata = {}
		for attr in dir(self):
			if attr.startswith('ins_'):
				func_name = attr[4:]
				func = getattr(self, attr)
				
				if not func.__doc__:
					raise self.SyntaxException("Missing syntax data for instruction '%s'." % func_name)
				
				self.asm_metadata[attr] = self.__parseSyntaxData(func_name, func.__doc__)
		
	def __parseSyntaxData(self, func_name, docstring):
		opcode = None
		syntax = None
		encoding = None
		argcount = None

		for line in docstring.split('\n'):
			if not ':' in line: continue
			lname, contents = line.strip().split(':', 1)
			lname = lname.lower().strip()
			contents = contents.strip()

			if lname == "opcode":
				opcode = contents
			elif lname == "syntax":
				if contents.lower() in self.SYNTAX_DATA:
					encoding, syntax = self.SYNTAX_DATA[contents.lower()]
				else:
					syntax = contents
			elif lname == 'encoding' and encoding is None:
				encoding = contents

		if opcode is None:
			raise self.SyntaxException("Cannot resolve Opcode for instruction '%s'" % func_name)
		
		if encoding is None:
			raise self.SyntaxException("Cannot resolve encoding type for instruction '%s'" % func_name)
			
		if syntax is None:
			raise self.SyntaxException("Cannot find syntax information for instruction '%s'" % func_name)
			
		if argcount is None:
			argcount = len(syntax.split(',')) if syntax else 0

		return (encoding, argcount, opcode, syntax)
		
	def __checkArguments(self, args, count):
		if len(args) != count:
			raise self.WrongArgumentCount
			
	def _parseRegister(self, reg):
		if reg in RegisterBank.REGISTER_NAMES:
			return RegisterBank.REGISTER_NAMES[reg]

		reg_match = re.match(r'^\$(\d{1,2})$', reg)

		if not reg_match or not 0 <= int(reg_match.group(1)) < 32:
			raise self.InvalidRegisterName("Invalid register name (%s)" % reg)

		return int(reg_match.group(1))
			
	def _parseAddress(self, addr):
		if not isinstance(addr, str):
			raise self.InvalidParameter
			
		paren_match = re.match(r'(-?\w+)\((\$.*?)\)', addr)
		if not paren_match:
			raise self.InvalidParameter("Expected address definition in the form of 'immediate($register)'.")
			
		try:
			immediate = int(paren_match.group(1), 0)
			register = self._parseRegister(paren_match.group(2))
		except ValueError:
			raise self.InvalidParameter("Error when parsing composite address '%s': Invalid immediate value." % addr)
		except self.InvalidRegisterName:
			raise self.InvalidParameter("Error when parsing composite address '%s': Invalid register value." % addr)
			
		return (immediate, register)
		
		
	def __call__(self, func, args):
		func = 'ins_' + func
		
		if not hasattr(self, func):
			raise self.UnknownInstruction("Unknown instruction: '%s'" % func)
			
		if func in self.asm_metadata:
			argcount = self.asm_metadata[func][1]
			if argcount is not None:
				self.__checkArguments(args, argcount)
			
		return getattr(self, func)(args)
		
	def resolveLabels(self, func, labels):
		data = func._inst_bld_tmp
		
		func_name = data[1]
		label = data[2]
		
		if label not in labels:
			return False
		
		func.label_address = labels[label]
		
		if data[0] == 'jump':
			self.encoder(func, func_name, imm = u32(func.label_address >> 2), label = label)
		elif data[0] == 'branch': # TODO: encoding for branch instructions
			self.encoder(func, func_name, s = data[3], t = data[4], imm = 0xDEAD)
		
		delattr(func, '_inst_bld_tmp')
		return True

############################################################
###### Templates
############################################################
	def arith_TEMPLATE(self, func_name, args, _lambda_f):
		reg_d = self._parseRegister(args[0])
		reg_s = self._parseRegister(args[1])
		reg_t = self._parseRegister(args[2])
		
		def _asm_arith(b): 
			b[reg_d] = _lambda_f(b[reg_s], b[reg_t])
			
		self.encoder(_asm_arith, func_name, d = reg_d, s = reg_s, t = reg_t)
		return _asm_arith
		
	def shift_TEMPLATE(self, func_name, args, shift_imm, _lambda_f):
		reg_d = self._parseRegister(args[0])
		reg_t = self._parseRegister(args[1])
		reg_s = 0
		shift = 0
		
		if shift_imm:
			shift = int(args[2], 0)
			def _asm_shift(b):
				b[reg_d] = _lambda_f(b[reg_t], shift)
						
		else:
			reg_s = self._parseRegister(args[2])
			def _asm_shift(b):
				b[reg_d] = _lambda_f(b[reg_t], b[reg_s])
		
		self.encoder(_asm_shift, func_name, d = reg_d, t = reg_t, s = reg_s, shift = shift)
		return _asm_shift
		
		
	def imm_TEMPLATE(self, func_name, args, _lambda_f):			
		reg_t = self._parseRegister(args[0])
		reg_s = self._parseRegister(args[1])

		try:
			immediate = int(args[2], 0)
		except ValueError:
			raise self.InvalidParameter

		def _asm_imm(b):
			b[reg_t] = _lambda_f(b[reg_s], immediate)
			
		self.encoder(_asm_imm, func_name, s = reg_s, t = reg_t, imm = immediate)
		return _asm_imm
		
	def branch_TEMPLATE(self, func_name, label, s, t, _lambda_f, link = False):
		reg_s = self._parseRegister(s)
		reg_t = self._parseRegister(t) if isinstance(t, str) else t

		def _asm_branch(b):
			if _lambda_f(b[reg_s], b[reg_t]):
				if link: b[31] = b.PC
				b.PC = _asm_branch.label_address
			
		setattr(_asm_branch, 'label_address', None)
		setattr(_asm_branch, '_inst_bld_tmp', ('branch', func_name, label, reg_s, reg_t))
		return _asm_branch
		
	def storeload_TEMPLATE(self, func_name, args, size, unsigned = False):		
		imm, reg_s = self._parseAddress(args[1])
		reg_t = self._parseRegister(args[0])
		
		_sign_f = (lambda i, size: i) if unsigned else extsgn
		
		if func_name[0] == 'l': # load instruction
			def _asm_storeload(b):
				b[reg_t] = _sign_f(b.memory[(imm + s32(b[reg_s])), size], size)
		elif func_name[0] == 's': # store instruction
			def _asm_storeload(b):
				b.memory[(imm + s32(b[reg_s])), size] = b[reg_t]
				
		self.encoder(_asm_storeload, func_name, t = reg_t, s = reg_s, imm = imm)
		return _asm_storeload
		
############################################################
###### Integer arithmetic
############################################################			
	def ins_add(self, args, unsigned = False):
		"""
			Opcode: 100000
			Syntax: ArithLog
		"""
		add_name = 'addu' if unsigned else 'add'
		add_func = (lambda a, b: a + b) if unsigned else (lambda a, b: s32(a) + s32(b))
		
		return self.arith_TEMPLATE(add_name, args, add_func)
		
	def ins_addu(self, args):
		"""
			Opcode: 100001
			Syntax: ArithLog
		"""
		return self.ins_add(args, True)
		
	def ins_addi(self, args):
		"""
			Opcode: 001000
			Syntax: ArithLogI
		"""
		return self.imm_TEMPLATE('addi', args, lambda a, b: s32(a) + b)

	def ins_addiu(self, args):
		"""
			Opcode: 001001
			Syntax: ArithLogI
		"""
		return self.imm_TEMPLATE('addiu', args, lambda a, b: u32(a) + b)
		
	def ins_div(self, args, unsigned = False):
		"""
			Opcode: 011010
			Syntax: DivMult
		"""		
		sign = u32 if unsigned else s32
		div_name = 'divu' if unsigned else 'div'
		 
		reg_s = self._parseRegister(args[0])
		reg_t = self._parseRegister(args[1])

		def _asm_div(b):
			b.HI = sign(b[reg_s]) % sign(b[reg_t])
			b.LO = sign(b[reg_s]) // sign(b[reg_t])
			
		self.encoder(_asm_div, div_name, t = reg_t, s = reg_s)

		return _asm_div
	
	def ins_divu(self, args):
		"""
			Opcode: 011011
			Syntax: DivMult
		"""
		return self.ins_div(args, True)

	def ins_mult(self, args, unsigned = False):
		"""
			Opcode: 011000
			Syntax: DivMult
		"""
		sign = u32 if unsigned else s32
		mult_name = 'multu' if unsigned else 'mult'
		
		reg_s = self._parseRegister(args[0])
		reg_t = self._parseRegister(args[1])
	
		def _asm_mult(b):
			result = sign(b[reg_s]) * sign(b[reg_t])
			b.HI = (result >> 32) & 0xFFFFFFFF
			b.LO = result & 0xFFFFFFFF
			
		self.encoder(_asm_mult, mult_name, s = reg_s, t = reg_t)
				
		return _asm_mult
		
	def ins_multu(self, args):
		"""
			Opcode: 011001
			Syntax: DivMult
		"""
		return self.ins_mult(args, True)
		
	def ins_sub(self, args, unsigned = False):
		"""
			Opcode: 100010
			Syntax: ArithLog
		"""
		sub_name = 'subu' if unsigned else 'sub'
		sub_func = (lambda a, b: a - b) if unsigned else (lambda a, b: s32(a) - s32(b))
		
		return self.arith_TEMPLATE(sub_name, args, sub_func)

	def ins_subu(self, args):
		"""
			Opcode: 100011
			Syntax: ArithLog
		"""
		return self.ins_sub(args, True)			
			
############################################################
###### Bitwise logic
############################################################	
	def ins_and(self, args):
		"""
			Opcode: 100100
			Syntax: ArithLog
		"""
		return self.arith_TEMPLATE('and', args, lambda a, b: a & b)
		
	def ins_andi(self, args):
		"""
			Opcode: 001100
			Syntax: ArithLogI
		"""
		return self.imm_TEMPLATE('andi', args, lambda a, b: a & b)
		
	def ins_nor(self, args):
		"""
			Opcode: 100111
			Syntax: ArithLog
		"""
		return self.arith_TEMPLATE('nor', args, lambda a, b: ~(a | b))
	
	def ins_or(self, args):
		"""
			Opcode: 100101
			Syntax: ArithLog
		"""
		return self.arith_TEMPLATE('or', args, lambda a, b: a | b)

	def ins_ori(self, args):
		"""
			Opcode: 001101
			Syntax: ArithLogI
		"""
		return self.imm_TEMPLATE('ori', args, lambda a, b: a | b)
		
	def ins_xor(self, args):
		"""
			Opcode: 100110
			Syntax: ArithLog
		"""
		return self.arith_TEMPLATE('xor', args, lambda a, b: a ^ b)
	
	def ins_xori(self, args):
		"""
			Opcode: 001110
			Syntax: ArithLogI
		"""
		return self.imm_TEMPLATE('xori', args, lambda a, b: a ^ b)
	
############################################################
###### Bitwise shifts
############################################################
# shifts with immediate
	def ins_sll(self, args):
		"""
			Opcode: 000000
			Syntax: Shift
		"""
		return self.shift_TEMPLATE('sll', args, True, lambda a, b: a << b)
	
	def ins_srl(self, args):
		"""
			Opcode: 000010
			Syntax: Shift
		"""
		return self.shift_TEMPLATE('srl', args, True, lambda a, b: a >> b)
		
	def ins_sra(self, args):
		"""
			Opcode: 000011
			Syntax: Shift
		"""
		return self.shift_TEMPLATE('sra', args, True, lambda a, b: s32(a) >> b)

# shifts with register
	def ins_sllv(self, args):
		"""
			Opcode: 000100
			Syntax: ShiftV
		"""
		return self.shift_TEMPLATE('sllv', args, False, lambda a, b: a << b)

	def ins_srlv(self, args):
		"""
			Opcode: 000110
			Syntax: ShiftV
		"""
		return self.shift_TEMPLATE('srlv', args, False, lambda a, b: a >> b)

	def ins_srav(self, args):
		"""
			Opcode: 000111
			Syntax: ShiftV
		"""
		return self.shift_TEMPLATE('srav', args, False, lambda a, b: s32(a) >> b)
		

############################################################
###### Set-if
############################################################		
	def ins_slt(self, args):
		"""
			Opcode: 101010
			Syntax: ArithLog
		"""
		return self.arith_TEMPLATE('slt', args, lambda a, b: 1 if s32(a) < s32(b) else 0)
		
	def ins_sltu(self, args):
		"""
			Opcode: 101001
			Syntax: ArithLog
		"""
		return self.arith_TEMPLATE('sltu', args, lambda a, b: 1 if u32(a) < u32(b) else 0)
		
	def ins_sltiu(self, args):
		"""
			Opcode: 001001
			Syntax: ArithLogI
		"""
		return self.imm_TEMPLATE('sltiu', args, lambda a, b: 1 if u32(a) < b else 0)
		
	def ins_slti(self, args):
		"""
			Opcode: 001010
			Syntax: ArithLog
		"""
		return self.imm_TEMPLATE('slti', args, lambda a, b: 1 if s32(a) < b else 0)


############################################################
###### Branching
############################################################		
	def ins_beq(self, args):
		"""
			Opcode: 000100
			Syntax: Branch
		"""
		return self.branch_TEMPLATE('beq', args[2], args[0], args[1], lambda a, b: a == b)
		
	def ins_bne(self, args):
		"""
			Opcode: 000101
			Syntax: Branch
		"""
		return self.branch_TEMPLATE('bne', args[2], args[0], args[1], lambda a, b: a != b)
		
	def ins_bgez(self, args):
		"""
			Opcode: 000001
			Syntax: BranchZ
		"""
		return self.branch_TEMPLATE('bgez', args[1], args[0], 0x1, lambda a, b: a >= 0)
		
	def ins_bgezal(self, args):
		"""
			Opcode: 000001
			Syntax: BranchZ
		"""
		return self.branch_TEMPLATE('bgezal', args[1], args[0], 0x11, lambda a, b: a >= 0, True)
		
	def ins_bgtz(self, args):
		"""
			Opcode: 000111
			Syntax: BranchZ
		"""
		return self.branch_TEMPLATE('bgtz', args[1], args[0], 0, lambda a, b: a > 0)
		
	def ins_blez(self, args):
		"""
			Opcode: 000110
			Syntax: BranchZ
		"""
		return self.branch_TEMPLATE('blez', args[1], args[0], 0, lambda a, b: a <= 0)

	def ins_bltz(self, args):
		"""
			Opcode: 000001
			Syntax: BranchZ
		"""
		return self.branch_TEMPLATE('bltz', args[1], args[0], 0, lambda a, b: a < 0)

	def ins_bltzal(self, args):
		"""
			Opcode: 000001
			Syntax: BranchZ
		"""
		return self.branch_TEMPLATE('bltzal', args[1], args[0], 0x10, lambda a, b: a < 0, True)


############################################################
###### Memory/data loading
############################################################
	def ins_lui(self, args):
		"""
			Opcode: 001111
			Syntax: LoadI
		"""
		reg_t = self._parseRegister(args[0])
		
		try:
			value = int(args[2], 0) & 0xFFFF
		except ValueError:
			raise self.InvalidParameter
		
		def _asm_lui(b):
			b[reg_t] = (value << 16)
			
		self.encoder(_asm_lui, 'lui', t = reg_t, imm = value)
			
		return _asm_lui
		
	def ins_lb(self, args):
		"""
			Opcode: 100000
			Syntax: LoadStore
		"""
		return self.storeload_TEMPLATE('lb', args, 1)
		
	def ins_lbu(self, args):
		"""
			Opcode: 100100
			Syntax: LoadStore
		"""
		return self.storeload_TEMPLATE('lbu', args, 1, True)
		
	def ins_lh(self, args):
		"""
			Opcode: 100001
			Syntax: LoadStore
		"""
		return self.storeload_TEMPLATE('lh', args, 2)
		
	def ins_lhu(self, args):
		"""
			Opcode: 100101
			Syntax: LoadStore
		"""
		return self.storeload_TEMPLATE('lhu', args, 2, True)
		
	def ins_lw(self, args):
		"""
			Opcode: 100011
			Syntax: LoadStore
		"""
		return self.storeload_TEMPLATE('lw', args, 4)
	
	def ins_sb(self, args):
		"""
			Opcode: 101000
			Syntax: LoadStore
		"""
		return self.storeload_TEMPLATE('sb', args, 1)
		
	def ins_sh(self, args):
		"""
			Opcode: 101001
			Syntax: LoadStore
		"""
		return self.storeload_TEMPLATE('sh', args, 2)

	def ins_sw(self, args):
		"""
			Opcode: 101011
			Syntax: LoadStore
		"""
		return self.storeload_TEMPLATE('sw', args, 4)

############################################################
###### Jumps
############################################################

	def ins_j(self, args, link = False):
		"""
			Opcode: 000010
			Syntax: Jump
		"""
		label = args[0]
		
		jmp_name = 'jal' if link else 'j'
		
		def _asm_j(b):
			if link: b[31] = b.PC
			b.PC = _asm_j.label_address
		
		setattr(_asm_j, 'label_address', None)
		setattr(_asm_j, '_inst_bld_tmp', ('jump', jmp_name, label))
		return _asm_j
		
	def ins_jr(self, args, link = False):
		"""
			Opcode: 001000
			Syntax: JumpR
		"""
		reg_s = self._parseRegister(args[0])
		
		jr_name = 'jalr' if link else 'jr'
		
		def _asm_jr(b):
			if link: b[31] = b.PC
			b.PC = b[reg_s]
		
		self.encoder(_asm_jr, jr_name, s = reg_s)
		return _asm_jr
		
	def ins_jal(self, args):
		"""
			Opcode: 000011
			Syntax: Jump
		"""
		return self.ins_j(args, True)

	def ins_jalr(self, args):
		"""
			Opcode: 001001
			Syntax: JumpR
		"""
		return self.ins_jr(args, True)

############################################################
###### Special register movement
############################################################
	def ins_mflo(self, args):
		"""
			Opcode: 010010
			Syntax: MoveFrom
		"""
		reg_d = self._parseRegister(args[0])
		
		def _asm_mflo(b):
			b[reg_d] = b.LO
		
		self.encoder(_asm_mflo, 'mflo', d = reg_d)
		return _asm_mflo
		
	def ins_mfhi(self, args):
		"""
			Opcode: 010000
			Syntax: MoveFrom
		"""
		reg_d = self._parseRegister(args[0])

		def _asm_mfhi(b):
			b[reg_d] = b.HI

		self.encoder(_asm_mfhi, 'mfhi', d = reg_d)
		return _asm_mfhi
		
	def ins_mtlo(self, args):
		"""
			Opcode: 010011
			Syntax: MoveTo
		"""
		reg_s = self._parseRegister(args[0])

		def _asm_mtlo(b):
			b.LO = b[reg_s]

		self.encoder(_asm_mtlo, 'mtlo', s = reg_s)
		return _asm_mtlo
		
	def ins_mthi(self, args):
		"""
			Opcode: 010001
			Syntax: MoveTo
		"""
		reg_s = self._parseRegister(args[0])

		def _asm_mthi(b):
			b.HI = b[reg_s]

		self.encoder(_asm_mthi, 'mthi', s = reg_s)
		return _asm_mthi
		
############################################################
###### Kernel/misc instructions
############################################################ 
	def ins_nop(self, args):
		"""
			Opcode: 000000
			Syntax: None
		"""		
		def _asm_nop(b):
			pass
		
		self.encoder(_asm_nop, 'nop')
		return _asm_nop
		
	def ins_syscall(self, args):
		"""
			Opcode: 100110
			Syntax: None
		"""
		def _asm_syscall(b):
			pass
		
		self.encoder(_asm_syscall, 'syscall')
		return _asm_syscall