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

import unittest
import testcommon

from spym.vm import MemoryManager, AssemblyParser

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
