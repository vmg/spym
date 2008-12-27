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