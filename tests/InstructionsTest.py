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
from spym.vm.RegBank import RegisterBank
from spym.vm.Memory import MemoryManager
from spym.common.Utils import *

class TestInstructionClosures(unittest.TestCase):
	def setUp(self):
		self.memory = MemoryManager(None, 32)
		
		self.bank = RegisterBank(self.memory)
		self.bank[1] = 0xFFFF
		self.bank[2] = 0xABAB
		self.bank[3] = 1
		self.bank[4] = 5
		self.bank[5] = 8
		self.bank[6] = -5
		self.bank[7] = -8
		self.bank[8] = 4
		self.bank[9] = 0x0010
		self.bank[10] = 0x0020
		
		self.ib = InstBuilder()
	
	def testParameterCount(self):
		argList1 = ['$3']
		argList2 = ['$4', '$3']
		argList3 = ['$2', '$9', '$1']
		argList4 = ['$1', '$2', '$3', '$4']
		
		# integer-arithmetical
		self.assertRaises(InstBuilder.WrongArgumentCount, self.ib, 'add', argList1)
		self.assertRaises(InstBuilder.WrongArgumentCount, self.ib, 'add', argList2)
		self.assertRaises(InstBuilder.WrongArgumentCount, self.ib, 'add', argList4)
		self.assertRaises(InstBuilder.WrongArgumentCount, self.ib, 'addu', argList1)
		self.assertRaises(InstBuilder.WrongArgumentCount, self.ib, 'add', argList4)
		self.assertRaises(InstBuilder.WrongArgumentCount, self.ib, 'div', argList1)
		self.assertRaises(InstBuilder.WrongArgumentCount, self.ib, 'div', argList3)
		self.assertRaises(InstBuilder.WrongArgumentCount, self.ib, 'mult', argList1)
		self.assertRaises(InstBuilder.WrongArgumentCount, self.ib, 'mult', argList3)
		self.assertRaises(InstBuilder.WrongArgumentCount, self.ib, 'sub', argList1)
		self.assertRaises(InstBuilder.WrongArgumentCount, self.ib, 'sub', argList4)
		
	def testLoadStoreInstructions(self):
		# check for parameter correctness
		self.assertRaises(InstBuilder.InvalidParameter, self.ib.ins_sw, ['$3', 'lol($30)'])
		self.assertRaises(InstBuilder.InvalidParameter, self.ib.ins_sh, ['$4', '00a($ra)'])
		self.assertRaises(InstBuilder.InvalidParameter, self.ib.ins_lw, ['$5', '01($ro)'])
		self.assertRaises(InstBuilder.InvalidParameter, self.ib.ins_lb, ['$6', '000005(30)'])
		self.assertRaises(InstBuilder.InvalidRegisterName, self.ib.ins_sw, ['$ras', '14($30)'])
		self.assertRaises(InstBuilder.InvalidRegisterName, self.ib.ins_sw, ['ras', '1($30)'])
		
		self.ib.ins_sw(['$1', '0($9)'])(self.bank)
		self.assertEqual(self.memory[0x0010, 4], 0xFFFF)
		
		self.ib.ins_sw(['$0', '0($9)'])(self.bank)
		self.assertEqual(self.memory[0x0010, 4], 0x0)
		
		self.ib.ins_sw(['$2', '4($9)'])(self.bank)
		self.assertEqual(self.memory[0x0014, 4], 0xABAB)
		
		self.ib.ins_sw(['$2', '-4($9)'])(self.bank)
		self.assertEqual(self.memory[0x000C, 4], 0xABAB)
		
		unaligned_closure = self.ib.ins_sw(['$1', '1($9)'])
		self.assertRaises(MemoryManager.UnalignedMemoryAccess, unaligned_closure, self.bank)
		
		unaligned_closure = self.ib.ins_sw(['$1', '2($9)'])
		self.assertRaises(MemoryManager.UnalignedMemoryAccess, unaligned_closure, self.bank)
		
		unaligned_closure = self.ib.ins_sw(['$1', '-1($9)'])
		self.assertRaises(MemoryManager.UnalignedMemoryAccess, unaligned_closure, self.bank)
		
		# self.ib.ins_sw(['$1', '0($9)'])(self.bank)
		# self.assertEqual(memory[0x0010, 4], 0xFFFF)
		# 
		# self.ib.ins_sw(['$1', '0($9)'])(self.bank)
		# self.assertEqual(memory[0x0010, 4], 0xFFFF)
		
	def testSetIfClosure_functionality(self):
		# slt
		self.ib.ins_slt(['$10', '$6', '$4'])(self.bank)
		self.assertEqual(self.bank[10], 1)
		
		self.ib.ins_slt(['$10', '$4', '$6'])(self.bank)
		self.assertEqual(self.bank[10], 0)
		
		self.ib.ins_slt(['$10', '$4', '$5'])(self.bank)
		self.assertEqual(self.bank[10], 1)
		
		self.ib.ins_slt(['$10', '$5', '$4'])(self.bank)
		self.assertEqual(self.bank[10], 0)
		
		self.ib.ins_slt(['$10', '$6', '$6'])(self.bank)
		self.assertEqual(self.bank[10], 0)
		
		self.ib.ins_slt(['$10', '$4', '$4'])(self.bank)
		self.assertEqual(self.bank[10], 0)
		
		# sltu
		self.ib.ins_sltu(['$10', '$6', '$4'])(self.bank)
		self.assertEqual(self.bank[10], 0)
		
		self.ib.ins_sltu(['$10', '$6', '$7'])(self.bank)
		self.assertEqual(self.bank[10], 0)
		
		# slti
		self.ib.ins_slti(['$10', '$5', '9'])(self.bank)
		self.assertEqual(self.bank[10], 1)
		
		self.ib.ins_slti(['$10', '$5', '8'])(self.bank)
		self.assertEqual(self.bank[10], 0)
		
		self.ib.ins_slti(['$10', '$5', '0'])(self.bank)
		self.assertEqual(self.bank[10], 0)
		
		self.ib.ins_slti(['$10', '$7', '0'])(self.bank)
		self.assertEqual(self.bank[10], 1)
		
		self.ib.ins_slti(['$10', '$7', '-9'])(self.bank)
		self.assertEqual(self.bank[10], 0)
		
		
		
	def testArithmeticalClosures_functionality(self):
		# add
		self.ib.ins_add(['$10', '$5', '$6'])(self.bank)
		self.assertEqual(self.bank[10], 3)
		
		self.ib.ins_add(['$10', '$5', '$3'])(self.bank)
		self.assertEqual(self.bank[10], 9)
		
		self.ib.ins_add(['$10', '$6', '$8'])(self.bank)
		self.assertEqual(s32(self.bank[10]), -1)
		
		# addu
		self.ib.ins_addu(['$10', '$7', '$4'])(self.bank)
		self.assertEqual(self.bank[10], 4294967293)
		
		# addi
		self.ib.ins_addi(['$10', '$5', '5'])(self.bank)
		self.assertEqual(self.bank[10], 13)
		
		self.ib.ins_addi(['$10', '$5', '-10'])(self.bank)
		self.assertEqual(s32(self.bank[10]), -2)
		
		# div
		self.ib.ins_div(['$5', '$8'])(self.bank)
		self.assertEqual(self.bank.HI, 0)
		self.assertEqual(self.bank.LO, 2)
		
		self.ib.ins_div(['$5', '$4'])(self.bank)
		self.assertEqual(self.bank.HI, 3)
		self.assertEqual(self.bank.LO, 1)
		
		self.ib.ins_div(['$7', '$8'])(self.bank)
		self.assertEqual(self.bank.HI, 0)
		self.assertEqual(s32(self.bank.LO), -2)
		
		# divu
		self.ib.ins_divu(['$5', '$8'])(self.bank)
		self.assertEqual(self.bank.HI, 0)
		self.assertEqual(self.bank.LO, 2)
		
		self.ib.ins_divu(['$7', '$2'])(self.bank)
		self.assertEqual(self.bank.HI, 26978)
		self.assertEqual(self.bank.LO, 97730)
		
		# mult
		self.ib.ins_mult(['$4', '$5'])(self.bank)
		self.assertEqual(self.bank.HI, 0)
		self.assertEqual(self.bank.LO, 40)
		
		self.ib.ins_mult(['$6', '$5'])(self.bank)
		self.assertEqual(self.bank.HI, 0xFFFFFFFF)
		self.assertEqual(self.bank.LO, 0xffffffd8)
		
		self.ib.ins_mult(['$6', '$7'])(self.bank)
		self.assertEqual(self.bank.HI, 0)
		self.assertEqual(self.bank.LO, 40)
		
		# multu
		self.ib.ins_multu(['$4', '$5'])(self.bank)
		self.assertEqual(self.bank.HI, 0)
		self.assertEqual(self.bank.LO, 40)
		
		self.ib.ins_multu(['$7', '$8'])(self.bank)
		self.assertEqual(self.bank.HI, 0x3)
		self.assertEqual(self.bank.LO, 0xffffffe0)
		
		# sub
		self.ib.ins_sub(['$10', '$5', '$4'])(self.bank)
		self.assertEqual(self.bank[10], 3)
		
		self.ib.ins_sub(['$10', '$5', '$4'])(self.bank)
		self.assertEqual(self.bank[10], 3)
		
		self.ib.ins_sub(['$10', '$6', '$7'])(self.bank)
		self.assertEqual(s32(self.bank[10]), 3)

if __name__ == '__main__':
	unittest.main()
