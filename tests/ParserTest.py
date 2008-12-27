import unittest
import testcommon

from spym.vm.Memory import MemoryManager
from spym.vm.Parser import AssemblyParser

class TestParser(unittest.TestCase):
	def setUp(self):
		self.memory = MemoryManager(None, 32)
		self.parser = AssemblyParser(self.memory, False)
	
	def _runAndPrint(self, program):
		self.parser.parseBuffer(program)
		
	def testTokenizer(self):
		testdata = [
			('t $32, $20, 0($32)', 				['$32', '$20', '0($32)']),
			('t $32 $20 0($32)', 				['$32', '$20', '0($32)']),
			('t $32, $20 0($32)',	 			['$32', '$20', '0($32)']),
			('t $32    ,    $20    ,   0($32)', ['$32', '$20', '0($32)']),
			('t $32    \t\t $20 \t\t 0($32)', 	['$32', '$20', '0($32)']),
			("t 0x8, 32, 2,      'a'", 		['0x8', '32', '2', "'a'"]),
			('t $32, $20, label($32)', 		['$32', '$20', 'label($32)']),
			('t $32, $20 # 0($32)', 			['$32', '$20']),
			('t #$32, $20, 0($32)',				None),
		]
		
		for (line, result) in testdata:
			_, _, tokens = self.parser._AssemblyParser__parseLine(line)
			self.assertEqual(tokens, result)
	
	def testCommentParser(self):
		self._runAndPrint(
"""
	# testing this shit...

#### don't want comments...

	# dont' want # comments.. #
#	a  			#
	#
	#
""")
		
	def testSimplePreprocessor(self):
		self._runAndPrint(
"""
	.data
	.word 0x1
	.ascii "testing shit shittehr"
""")
	

	def testMediumPreprocessor(self):
		self._runAndPrint(
"""
	.data 0x1000ABC0
	.word 0x1, 0xAABBCCDD, -1, -8
	.byte 0x8, 'a', 'b'
	.half 0xEEEE, 0x88, 0x99
	.word 0x12345678
	.align 2
	.asciiz "SIMPLE, TEST"
""")

if __name__ == '__main__':
	unittest.main()