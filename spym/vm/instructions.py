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

import re
from spym.vm.regbank import RegisterBank
from spym.vm.exceptions import MIPS_Exception
from spym.common.utils import _debug, u32, s32, extsgn

class InstructionAssembler(object):
	
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
	
	LOADSTORE_ADDRESS_REGEX = r'(-?(?:0x)?[\da-fA-F]+)\((\$.*?)\)'
	BRANCH_ENCODING_MOD = 0x4
	JAL_OFFSET = 0x4
		
	class SyntaxException(Exception):
		pass
		
	class InstructionAssemblerException(Exception):
		pass
		
	def __init__(self, parser):
		self.parser = parser
		
		from spym.common.encoder import InstructionEncoder
		self.encoder = InstructionEncoder(self)
		
		self.assembler_register_protected = True
		self.__initMetaData()
		
	def __initMetaData(self):
		self.asm_metadata = {}
		for attr in dir(self):
			if attr.startswith('ins_') or attr.startswith('pins_'):
				func_type, func_name = attr.split('_', 1)
				func = getattr(self, attr)
				
				if not func.__doc__:
					raise self.SyntaxException("Missing syntax data for instruction '%s'." % func_name)
				
				self.asm_metadata[attr] = self.__parseSyntaxData(func_name, func.__doc__, (func_type == 'pins'))
		
	def __parseSyntaxData(self, func_name, docstring, pseudo):
		opcode = None
		fcode = None
		syntax = None
		encoding = None
		argcount = None
		custom_syntax = False

		for line in docstring.split('\n'):
			if not ':' in line: continue
			lname, contents = line.strip().split(':', 1)
			lname = lname.lower().strip()
			contents = contents.strip()
	
			if lname == "opcode":
				opcode = contents
			elif lname == "fcode":
				fcode = contents
			elif lname == "syntax":
				if contents.lower() in self.SYNTAX_DATA:
					encoding, syntax = self.SYNTAX_DATA[contents.lower()]
				else:
					syntax = contents
					custom_syntax = True
			elif lname == 'encoding' and encoding is None:
				encoding = contents

		if opcode is None and not pseudo:
			raise self.SyntaxException("Cannot resolve Opcode for instruction '%s'" % func_name)
		
		if encoding is None and not pseudo:
			raise self.SyntaxException("Cannot resolve encoding type for instruction '%s'" % func_name)
			
		if fcode is None and encoding == 'R':
			raise self.SyntaxException("Missing function code for 'r' encoding instruction '%s'" % func_name)
			
		if syntax is None:
			raise self.SyntaxException("Cannot find syntax information for instruction '%s'" % func_name)
			
		if argcount is None:
			if custom_syntax:
				if not syntax.startswith(func_name):
					raise self.SyntaxException("Malformed syntax definition. Expecting instruction syntax in the ")
				else:
					syntax = syntax[len(func_name):]
					syntax.strip()

			argcount = len(syntax.split(',')) if syntax else 0

		return (encoding, argcount, opcode, fcode, syntax)
		
	def _checkArguments(self, args, count):
		if len(args) != count:
			raise self.InstructionAssemblerException("Wrong argument count in instruction.")
			
	def _parseRegister(self, reg):
		if reg in RegisterBank.REGISTER_NAMES:
			return RegisterBank.REGISTER_NAMES[reg]

		reg_match = re.match(r'^\$(\d{1,2})$', reg)
		register_id = int(reg_match.group(1)) if reg_match else -1

		if not 0 <= register_id < 32:
			raise self.InstructionAssemblerException("Invalid register name (%s)" % reg)
			
		if register_id == 1 and self.assembler_register_protected:
			raise self.InstructionAssemblerException("The $1 register is reserver for assembler operations.")

		return register_id
		
	def _parseImmediate(self, imm):
		if len(imm) == 3 and imm[0] == "'" and imm[2] == "'":
			return ord(imm[1])
			
		try:
			imm = int(imm, 0)
		except (ValueError, TypeError):
			raise self.InstructionAssemblerException("Invalid immediate value '%s'." % imm)
			
		return imm
		
			
	def _parseAddress(self, addr):
		if not isinstance(addr, str):
			raise self.InvalidParameter
			
		paren_match = re.match(self.LOADSTORE_ADDRESS_REGEX, addr)
		if not paren_match:
			raise self.InstructionAssemblerException("Wrong argument: Expected address definition in the form of 'immediate($register)'.")
			
		try:
			immediate = int(paren_match.group(1), 0)
			register = self._parseRegister(paren_match.group(2))
		except ValueError:
			raise self.InstructionAssemblerException("Error when parsing composite address '%s': Invalid immediate value." % addr)
		except self.InvalidRegisterName:
			raise self.InstructionAssemblerException("Error when parsing composite address '%s': Invalid register value." % addr)
			
		return (immediate, register)
		
		
	def __call__(self, func, args):
		func = 'ins_' + func
		
		if not hasattr(self, func):
			raise self.InstructionAssemblerException("Unknown instruction: '%s'" % func)
			
		argcount = self.asm_metadata[func][1]
		self._checkArguments(args, argcount)
			
		return getattr(self, func)(args)
		
	def resolveLabels(self, func, func_addr, labels):
		data = func._inst_bld_tmp
		
		func_name = data[1]
		label = data[2]
		
		if label not in labels:
			return False
		
		func.label_address = labels[label]
		
		if data[0] == 'jump':
			self.encoder(func, func_name, 
				imm = u32(func.label_address >> 2), 
				label = label)

		elif data[0] == 'branch':
			self.encoder(func, func_name, 
				s = data[3], 
				t = data[4], 
				imm = u32((func.label_address - func_addr + self.BRANCH_ENCODING_MOD) >> 2), 
				label = label)
		
		delattr(func, '_inst_bld_tmp')
		return True

############################################################
###### Templates
############################################################
	def arith_TEMPLATE(self, func_name, args, _lambda_f, overflow = True):
		reg_d = self._parseRegister(args[0])
		reg_s = self._parseRegister(args[1])
		reg_t = self._parseRegister(args[2])
		
		def _asm_arith(b): 
			result = _lambda_f(b[reg_s], b[reg_t])
			
#			if overflow and result & (1 << 32):
#				raise MIPS_Exception('OVF')
				
			b[reg_d] = result
			
		self.encoder(_asm_arith, func_name, d = reg_d, s = reg_s, t = reg_t)
		return _asm_arith
		
	def shift_TEMPLATE(self, func_name, args, shift_imm, _lambda_f):
		reg_d = self._parseRegister(args[0])
		reg_t = self._parseRegister(args[1])
		reg_s = 0
		shift = 0
		
		if shift_imm:
			shift = self._parseImmediate(args[2])
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
		immediate = self._parseImmediate(args[2])

		def _asm_imm(b):
			b[reg_t] = _lambda_f(b[reg_s], immediate)
			
		self.encoder(_asm_imm, func_name, s = reg_s, t = reg_t, imm = immediate)
		return _asm_imm
		
	def branch_TEMPLATE(self, func_name, label, s, t, _lambda_f, link = False):
		reg_s = self._parseRegister(s)
		reg_t = self._parseRegister(t) if isinstance(t, str) else t

		def _asm_branch(b):
			if _lambda_f(s32(b[reg_s]), s32(b[reg_t])):
				if link: b[31] = b.PC + self.JAL_OFFSET
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
				b[reg_t] = _sign_f(b.memory[(imm + u32(b[reg_s])), size], size)
		elif func_name[0] == 's': # store instruction
			def _asm_storeload(b):
				b.memory[(imm + u32(b[reg_s])), size] = b[reg_t]
				
		self.encoder(_asm_storeload, func_name, t = reg_t, s = reg_s, imm = imm)
		return _asm_storeload
		
############################################################
###### Integer arithmetic
############################################################			
	def ins_add(self, args, unsigned = False):
		"""
			Opcode: 000000
			Fcode:  100000
			Syntax: ArithLog
		"""
		add_name = 'addu' if unsigned else 'add'
		add_func = (lambda a, b: a + b) if unsigned else (lambda a, b: s32(a) + s32(b))
		
		return self.arith_TEMPLATE(add_name, args, add_func)
		
	def ins_addu(self, args):
		"""
			Opcode: 000000
			Fcode: 100001
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
			Opcode: 000000
			Fcode: 011010
			Syntax: DivMult
		"""		
		sign = u32 if unsigned else s32
		div_name = 'divu' if unsigned else 'div'
		 
		reg_s = self._parseRegister(args[0])
		reg_t = self._parseRegister(args[1])

		def _asm_div(b):
			try:
				b.LO, b.HI = divmod(sign(b[reg_s]), sign(b[reg_t]))
			except ZeroDivisionError:
				raise MIPS_Exception('OVF')
			
		self.encoder(_asm_div, div_name, t = reg_t, s = reg_s)

		return _asm_div
	
	def ins_divu(self, args):
		"""
			Opcode: 000000
			Fcode: 011011
			Syntax: DivMult
		"""
		return self.ins_div(args, True)

	def ins_mult(self, args, unsigned = False):
		"""
			Opcode: 000000
			Fcode: 011000
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
			Opcode: 000000
			Fcode: 011001
			Syntax: DivMult
		"""
		return self.ins_mult(args, True)
		
	def ins_sub(self, args, unsigned = False):
		"""
			Opcode: 000000
			Fcode: 100010
			Syntax: ArithLog
		"""
		sub_name = 'subu' if unsigned else 'sub'
		sub_func = (lambda a, b: a - b) if unsigned else (lambda a, b: s32(a) - s32(b))
		
		return self.arith_TEMPLATE(sub_name, args, sub_func)

	def ins_subu(self, args):
		"""
			Opcode: 000000
			Fcode: 100011
			Syntax: ArithLog
		"""
		return self.ins_sub(args, True)			
			
############################################################
###### Bitwise logic
############################################################	
	def ins_and(self, args):
		"""
			Opcode: 000000
			Fcode: 100100
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
			Opcode: 000000
			Fcode: 100111
			Syntax: ArithLog
		"""
		return self.arith_TEMPLATE('nor', args, lambda a, b: ~(a | b))
	
	def ins_or(self, args):
		"""
			Opcode: 000000
			Fcode: 100101
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
			Opcode: 000000
			Fcode: 100110
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
			Fcode: 000000
			Syntax: Shift
		"""
		return self.shift_TEMPLATE('sll', args, True, lambda a, b: a << b)
	
	def ins_srl(self, args):
		"""
			Opcode: 000000
			Fcode: 000010
			Syntax: Shift
		"""
		return self.shift_TEMPLATE('srl', args, True, lambda a, b: a >> b)
		
	def ins_sra(self, args):
		"""
			Opcode: 000000
			Fcode: 000011
			Syntax: Shift
		"""
		return self.shift_TEMPLATE('sra', args, True, lambda a, b: s32(a) >> b)

# shifts with register
	def ins_sllv(self, args):
		"""
			Opcode: 000000
			Fcode: 000100
			Syntax: ShiftV
		"""
		return self.shift_TEMPLATE('sllv', args, False, lambda a, b: a << b)

	def ins_srlv(self, args):
		"""
			Opcode: 000000
			Fcode: 000110
			Syntax: ShiftV
		"""
		return self.shift_TEMPLATE('srlv', args, False, lambda a, b: a >> b)

	def ins_srav(self, args):
		"""
			Opcode: 000000
			Fcode: 000111
			Syntax: ShiftV
		"""
		return self.shift_TEMPLATE('srav', args, False, lambda a, b: s32(a) >> b)
		

############################################################
###### Set-if
############################################################		
	def ins_slt(self, args):
		"""
			Opcode: 000000
			Fcode: 101010
			Syntax: ArithLog
		"""
		return self.arith_TEMPLATE('slt', args, lambda a, b: 1 if s32(a) < s32(b) else 0)
		
	def ins_sltu(self, args):
		"""
			Opcode: 000000
			Fcode: 101001
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
			Opcode: 000000
			Fcode: 001010
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
		immediate = self._parseImmediate(args[1]) & 0xFFFF
		
		def _asm_lui(b):
			b[reg_t] = (immediate << 16)
			
		self.encoder(_asm_lui, 'lui', t = reg_t, imm = immediate)
			
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
			if link: b[31] = b.PC + self.JAL_OFFSET
			b.PC = _asm_j.label_address
		
		setattr(_asm_j, 'label_address', None)
		setattr(_asm_j, '_inst_bld_tmp', ('jump', jmp_name, label))
		return _asm_j
		
	def ins_jr(self, args, link = False):
		"""
			Opcode: 000000
			Fcode: 001000
			Syntax: JumpR
		"""
		reg_s = self._parseRegister(args[0])
		
		jr_name = 'jalr' if link else 'jr'
		
		def _asm_jr(b):
			if link: b[31] = b.PC + self.JAL_OFFSET
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
			Opcode: 000000
			Fcode: 001001
			Syntax: JumpR
		"""
		return self.ins_jr(args, True)

############################################################
###### Special register movement
############################################################
	def ins_mflo(self, args):
		"""
			Opcode: 000000
			Fcode: 010010
			Syntax: MoveFrom
		"""
		reg_d = self._parseRegister(args[0])
		
		def _asm_mflo(b):
			b[reg_d] = b.LO
		
		self.encoder(_asm_mflo, 'mflo', d = reg_d)
		return _asm_mflo
		
	def ins_mfhi(self, args):
		"""
			Opcode: 000000
			Fcode: 010000
			Syntax: MoveFrom
		"""
		reg_d = self._parseRegister(args[0])

		def _asm_mfhi(b):
			b[reg_d] = b.HI

		self.encoder(_asm_mfhi, 'mfhi', d = reg_d)
		return _asm_mfhi
		
	def ins_mtlo(self, args):
		"""
			Opcode: 000000
			Fcode: 010011
			Syntax: MoveTo
		"""
		reg_s = self._parseRegister(args[0])

		def _asm_mtlo(b):
			b.LO = b[reg_s]

		self.encoder(_asm_mtlo, 'mtlo', s = reg_s)
		return _asm_mtlo
		
	def ins_mthi(self, args):
		"""
			Opcode: 000000
			Fcode: 010001
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
			Fcode: 000000
			Syntax: None
		"""		
		def _asm_nop(b):
			pass
		
		self.encoder(_asm_nop, 'nop')
		return _asm_nop
		
	def ins_mfc0(self, args):
		"""
			Opcode: 010000
			Fcode: 000000
			Syntax: mfc0 $t, $d
			Encoding: R
		"""
		reg_t = self._parseRegister(args[0])
		reg_d = self._parseRegister(args[1])
		
		def _asm_mfc0(b):
			if b.CP0.getUserBit():
				raise MIPS_Exception('RI')
			b[reg_t] = b.CP0[reg_d]
		
		self.encoder(_asm_mfc0, 'mfc0', t = reg_t, d = reg_d)
		return _asm_mfc0
	
	def ins_mtc0(self, args):
		"""
			Opcode: 010000
			Fcode: 000000
			Syntax: mtc0 $d, $t
			Encoding: R
		"""
		reg_t = self._parseRegister(args[0])
		reg_d = self._parseRegister(args[1])

		def _asm_mtc0(b):
			if b.CP0.getUserBit():
				raise MIPS_Exception('RI')
			b.CP0[reg_d] = b[reg_t]
		
		self.encoder(_asm_mtc0, 'mtc0', s = 4, d = reg_d, t = reg_t)
		return _asm_mtc0
		
	def ins_rfe(self, args):
		"""
			Opcode: 010000
			Fcode:	010000
			Syntax: None
		"""
		
		def _asm_rfe(b):
			if b.CP0.getUserBit():
				raise MIPS_Exception('RI')
			
			lowbits = b.CP0.Status & 0x3F # get the lowest 6 bits
			b.CP0.Status &= ~0x3F		  # clear the SIX lowest bits
			
			# shift them right, but put back only 4 lower bits (to bring 0s from the right) 
			b.CP0.Status |= (lowbits >> 2) & 0xF
			
		self.encoder(_asm_rfe, 'rfe', s = 0x10)
		setattr(_asm_rfe, '_delay', True)
		
		return _asm_rfe
		
	def ins_syscall(self, args):
		"""
			Opcode: 000000
			Fcode: 100110
			Syntax: None
		"""
		def _asm_syscall(b):
			raise MIPS_Exception("SYSCALL")
		
		self.encoder(_asm_syscall, 'syscall')
		return _asm_syscall
		