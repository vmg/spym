import unittest
import testcommon

from spym.vm.Instructions import InstBuilder
from spym.common.InstEncoder import InstructionEncoder


class TestInstructionEncoding(unittest.TestCase):
	def setUp(self):
		self.encoder = InstructionEncoder()
		
	def testAllPossibleEncodings(self):
		for ins in dir(InstBuilder):
			ins = ins.split('_')
			if len(ins) == 2 and ins[0] == 'ins':
				self.encoder(ins[1])
				
	def testInstArrayConsistency(self):
		list_len = (len(InstructionEncoder.INSTRUCTIONS_R) + 
					len(InstructionEncoder.INSTRUCTIONS_J) +
					len(InstructionEncoder.INSTRUCTIONS_I))
		
		dict_len = len(InstructionEncoder.OPCODES)
		
		self.assertEqual(list_len, dict_len)
		
	def testMissingInstImplementations(self):
		for ins in InstructionEncoder.OPCODES.keys():
			if not hasattr(InstBuilder, 'ins_' + ins):
				self.fail("Missing instruction implementation: '%s'" % ins)
				

if __name__ == '__main__':
	unittest.main()