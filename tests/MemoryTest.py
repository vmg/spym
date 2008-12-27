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

from spym.vm import MemoryManager, MIPS_Exception

class TestMemoryManager(unittest.TestCase):
	def setUp(self):
		self.memory = MemoryManager(None, 32)
		self.memory.clear()
		
	def testInnerConsistency(self):
		for i in range(0, 128, 4):
			self.memory[i] = 0xFF000000
		
		self.assertEqual(len(self.memory.memory), 4)
		
		self.memory[128] = 0x0
		self.assertEqual(len(self.memory.memory), 5)
		
	def testSimpleAllocation(self):
		self.memory[0x00000004] = 0x2
		self.assertEqual(self.memory[0x4], 0x2)
		
		self.memory[0x0008, 2] = 0xFFFF
		self.memory[0x000A, 2] = 0xAAAA
		self.assertEqual(self.memory[0x0008, 4], 0xAAAAFFFF)
		
		self.memory[0x0010, 1] = 0xAAFF
		self.memory[0x0011, 1] = 0xEEEE
		self.assertEqual(self.memory[0x0010, 4], 0x0000EEFF)
		
		self.memory[0x0002] = 0xABCD0A0A
		self.assertEqual(self.memory[0x0002], 0x0A0A)
		
	def testMemoryBounds(self):
		self.assertRaises(MIPS_Exception, self.memory.__getitem__, 0xFFFFFFFF0)
		self.assertEqual(self.memory[0xFFFFFFFF], 0)
		
	def testAlignmentChecks(self):
		self.assertRaises(MIPS_Exception, self.memory.getWord, 0x0003)
		self.assertRaises(MIPS_Exception, self.memory.getWord, 0x0002)
		self.assertRaises(MIPS_Exception, self.memory.getHalf, 0x0003)
		self.assertRaises(MIPS_Exception, self.memory.getWord, 0x0001)
		
		self.assertRaises(MIPS_Exception, self.memory.setWord, 0x0003, 0xFFFF)
		self.assertRaises(MIPS_Exception, self.memory.setWord, 0x0002, 0xFFFF)
		self.assertRaises(MIPS_Exception, self.memory.setHalf, 0x0003, 0xFFFF)
		self.assertRaises(MIPS_Exception, self.memory.setWord, 0x0001, 0xFFFF)
		
		self.assertEqual(self.memory.getWord(0x0000), 0)
		self.assertEqual(self.memory.getHalf(0x0002), 0)
		self.assertEqual(self.memory.getByte(0x0003), 0)
		
		
if __name__ == '__main__':
	unittest.main()
