import unittest
import testcommon

from spym.vm.Instructions import InstBuilder
from spym.common.InstEncoder import InstructionEncoder


class TestInstructionEncoding(unittest.TestCase):
	def setUp(self):
		self.builder = InstBuilder()
		
	# def testAllPossibleEncodings(self):
	# 	for ins in dir(self.builder):
	# 		ins = ins.split('_')
	# 		if len(ins) == 2 and ins[0] == 'ins':
	# 			self.builder.encoder(ins[1])

	# no longer needed
	# def testMetaDataGeneration(self):				
	# 	for ins in dir(self.builder):
	# 		if ins.startswith('ins_'):
	# 			func = getattr(self.builder, ins)
	# 			self.assertEqual(func.opcode, InstructionEncoder.OPCODES[ins[4:]], "Opcode difference in instruction %s" % ins)
			
if __name__ == '__main__':
	unittest.main()