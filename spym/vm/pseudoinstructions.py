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
from spym.vm.instructions import InstructionAssembler
from spym.common.utils import _debug

class PseudoInstructionAssembler(InstructionAssembler):
	
	IMM_PSEUDOINS = {
		'add' 	: 2, 	'addu' 	: 2,	
		'and' 	: 2,	'nor' 	: 2,
		'or' 	: 2,	'sub' 	: 2,
		'subu' 	: 2,	'xor' 	: 2,
		'stl' 	: 2,	'stlu' 	: 2,
		'beq' 	: 1,	'bne' 	: 1,
	}
	
	STORE_PSEUDOINS = ['sb', 'sh', 'sw', 'lb', 'lbu', 'lh', 'lhu', 'lw']
		
	def imm_pins_TEMPLATE(self, args, imm_parameter):
		try:
			self._parseRegister(args[imm_parameter])
		except self.InstructionAssemblerException:
			immediate = args[imm_parameter]
			args[imm_parameter] = '$1'
			return args, self.pins_li(['$1', immediate])
			
		return args, []
		
	def storeload_label_TEMPLATE(self, args):
		reg_t = args[0]
		mem_addr = args[1]

		# sw $2, ($d) ==> sw $2, 0($d)
		if re.match(self.LOADSTORE_ADDRESS_REGEX, mem_addr):
			return args, []
			
		if re.match(r'\(\$\w{1,2}\)', mem_addr):
			args[1] = "0" + mem_addr
			return args, []
			
		match = re.match(r'^(\w+)?([+-](?:0x)?[\da-fA-F]+)?(?:\((\$\w{1,2})\))?$', mem_addr)
		
		label_address 	= match.group(1)
		const_immediate = match.group(2)
		addr_register 	= match.group(3)
		
		if label_address:
			if label_address not in self.parser.local_labels:
				raise self.InstructionAssemblerException("Cannot resolve label in load/store instruction.")
			
			label_address = self.parser.local_labels[label_address]
		else:
			label_address = 0
			
		const_immediate = self._parseImmediate(const_immediate) if const_immediate else 0
		addr_register = self._parseRegister(addr_register) if addr_register else 0
		
		asm_output = self.pins_li(['$1', str(label_address + const_immediate)])
		
		if addr_register:
			asm_output.append(InstructionAssembler.__call__(self, 'add', ['$1', '$1', "$%d" % addr_register]))

		args[1] = "0($1)"
		return args, asm_output
		
		
	def __call__(self, func, args):
		pseudoinst_output = []
		self.assembler_register_protected = False # disable protection in $1 to encode pseudo-instructions
		
		if func in self.IMM_PSEUDOINS:
			args, _asm_immFunc = self.imm_pins_TEMPLATE(args, self.IMM_PSEUDOINS[func])
			pseudoinst_output += _asm_immFunc + [InstructionAssembler.__call__(self, func, args)]
		
		elif func in self.STORE_PSEUDOINS:
			args, _asm_addressLoad = self.storeload_label_TEMPLATE(args)
			pseudoinst_output += _asm_addressLoad + [InstructionAssembler.__call__(self, func, args)]
			
		elif hasattr(self, 'pins_' + func):
			func = 'pins_' + func
			argcount = self.asm_metadata[func][1]
			self._checkArguments(args, argcount)
			
			pseudoinst_output += getattr(self, func)(args)
		
		self.assembler_register_protected = True # enable $1 protection again	

		return pseudoinst_output or InstructionAssembler.__call__(self, func, args)

	def pins_abs(self, args): # (x ^ (x>>31)) - (x>>31)
		"""
		Desc: Sets $d to the absolute value of $s (assuming ca2)
		Syntax: abs $d, $s
		"""
		return [
			self.ins_sra(['$1', args[1], 31]),		# sra $1, src1, 31
			self.ins_xor([args[0], '$1', args[1]]),	# xor des, $1, src1
			self.ins_sub([args[0], args[0], '$1'])
		]
		
	def pins_div(self, args, unsigned = False):
		"""
		Desc: Sets $d to the quotient of $s and $t, skipping the HI/LO registers.
		Syntax: div $d, $s, $t
		"""
		if len(args) == 2:
			return InstructionAssembler.__call__(self, 'div', args)
			
		args, _asm_immFunc = self.imm_pins_TEMPLATE(args, 2)
		
		return _asm_immFunc + [
			InstructionAssembler.ins_div(self, args[1:], unsigned), # do the normal division with src1 and src2
			self.ins_mflo([args[0]]),				 # move from LO to des the result	
		]
		
	def pins_mul(self, args, unsigned = False):
		"""
		Desc: Sets $d to the lesser half (32 bits) of the product of $s and $t, skipping the HI/LO registers.
		Syntax: mul $d, $s, $t
		"""
		args, _asm_immFunc = self.imm_pins_TEMPLATE(args, 2)
		
		return _asm_immFunc + [
			self.ins_mult(args[1:], unsigned), # do the normal division with src1 and src2
			self.ins_mflo([args[0]]),				 # move from LO to des the result	
		]
		
	def pins_neg(self, args):
		"""
		Desc: Sets $d to the arithmetical negative of $s
		Syntax: neg $d, $s
		"""
		return [self.ins_sub([args[0], '$0', args[1]])]
		
	def pins_negu(self, args):
		"""
		Desc: Sets $d to the arithmetical negative of $s, assuming $s is positive.
		Syntax: negu $d, $s
		"""
		return [self.ins_sub([args[0], '$0', args[1]], True)]
	
	def pins_not(self, args):
		"""
		Desc: Sets $d to the logical negative (NOT) of $s
		Syntax: not $d, $s
		"""
		return [self.ins_nor([args[0], args[1], args[1]])]
		
	def pins_beqz(self, args):
		"""
		Desc: Branches to 'label' if $s is zero.
		Syntax: beqz $s, label
		"""
		return [self.ins_beq([args[0], '$0', args[1]])]
		
	def pins_bnez(self, args):
		"""
		Desc: Branches to 'label' if $s it not zero.
		Syntax: bnez $s, label
		"""
		return [self.ins_bne([args[0], '$0', args[1]])]
	
	def pins_move(self, args):
		"""
		Desc: Moves the contents of $s to $d.
		Syntax: move $d, $s
		"""
		return [self.ins_or([args[0], '$0', args[1]])]
		
	def pins_la(self, args):
		"""
		Desc: Loads the address of a previously defined label into $d.
		Syntax: la $d, label
		"""		
		if args[1] not in self.parser.local_labels:
			raise self.InstructionAssemblerException("Cannot resolve label in LA (load address) instruction.")

		args[1] = str(self.parser.local_labels[args[1]])
		return self.pins_li(args)
		
	def pins_li(self, args):
		"""
		Desc: Loads a 32 bits immediate into $d
		Syntax: li $d, imm
		"""
		immediate = self._parseImmediate(args[1])
		lower = immediate & 0xFFFF
		upper = (immediate >> 16) & 0xFFFF
			
		if upper:
			return [
				self.ins_lui([args[0], str(upper)]),
				self.ins_ori([args[0], args[0], str(lower)])
			]
		else:
			return [
				self.ins_ori([args[0], '$0', str(lower)]),
			]
			
