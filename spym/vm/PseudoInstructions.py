from spym.vm.Instructions import InstBuilder
from spym.common.Utils import *

class PseudoInstBuilder(InstBuilder):
	
	IMM_PSEUDOINS = {
		'add' 	: 2, 	'addu' 	: 2,	
		'and' 	: 2,	'nor' 	: 2,
		'or' 	: 2,	'sub' 	: 2,
		'subu' 	: 2,	'xor' 	: 2,
		'stl' 	: 2,	'stlu' 	: 2,
		'beq' 	: 1,	'bne' 	: 1,
	}
		
	def imm_pins_TEMPLATE(self, args, imm_parameter):
		try:
			self._parseRegister(args[imm_parameter])
		except self.InvalidParameter:
			immediate = int(args[imm_parameter])
			args[imm_parameter] = '$1'
			return args, self.pins_li(['$1', immediate])
			
		return args, []
		
	def __call__(self, func, args):
		if func in self.IMM_PSEUDOINS:
			args, _asm_immFunc = self.imm_pins_TEMPLATE(args, self.IMM_PSEUDOINS[func])
			return _asm_immFunc + [InstBuilder.__call__(self, func, args),]
			
		if hasattr(self, 'pins_' + func):
			return getattr(self, 'pins_' + func)(args)
			
		return InstBuilder.__call__(self, func, args)

	def pins_abs(self, args): # (x ^ (x>>31)) - (x>>31)
		return [
			self.ins_sra(['$1', args[1], 31]),		# sra $1, src1, 31
			self.ins_xor([args[0], '$1', args[1]]),	# xor des, $1, src1
			self.ins_sub([args[0], args[0], '$1'])
		]
		
	def pins_div(self, args, unsigned = False):
		if len(args) == 2:
			return InstBuilder.ins_div(self, args, unsigned)
			
		args, _asm_immFunc = self.imm_pins_TEMPLATE(args, 2)
		
		return _asm_immFunc + [
			InstBuilder.ins_div(self, args[1:], unsigned), # do the normal division with src1 and src2
			self.ins_mflo([args[0]]),				 # move from LO to des the result	
		]
		
	def pins_mul(self, args, unsigned = False):
		args, _asm_immFunc = self.imm_pins_TEMPLATE(args, 2)
		
		return _asm_immFunc + [
			self.ins_mult(args[1:], unsigned), # do the normal division with src1 and src2
			self.ins_mflo([args[0]]),				 # move from LO to des the result	
		]
		
	def pins_neg(self, args):
		return [
			self.ins_sub([args[0], '$0', args[1]]),
		]
		
	def pins_negu(self, args):
		return [
			self.ins_sub([args[0], '$0', args[1]], True),
		]
	
	def pins_not(self, args):
		return [
			self.ins_nor([args[0], args[1], args[1]]),
		]
		
	def pins_beqz(self, args):
		return [
			self.ins_beq([args[0], '$0', args[1]]),
		]
		
	def pins_bnez(self, args):
		return [
			self.ins_bne([args[0], '$0', args[1]]),
		]
		
	def pins_li(self, args):
		try:
			immediate = int(args[1], 0)
			lower = immediate & 0xFFFF
			upper = (immediate >> 16) & 0xFFFF
			
		except ValueError:
			raise InstBuilder.InvalidParameter("Invalid immediate value.")
			
		if upper:
			return [
				self.ins_ori([args[0], args[0], str(lower)]),
				self.ins_lui([args[0], str(upper)])
			]
		else:
			return [
				self.ins_ori([args[0], '$0', str(lower)]),
			]
			
