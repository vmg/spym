import unittest
import testcommon

#from spym.vm.VirtualMachine import VirtualMachine
from spym.vm import VirtualMachine

class GlobalASMTests(unittest.TestCase):
	def _runTest(self, asm):
		vm = VirtualMachine(asm, loadAsBuffer = True, enablePseudoInsts = True)
		vm.run()
		vm.debugPrintAll()
		
	def testASM1(self):
		self._runTest(
"""
.data
bdata: 
	.word 0xAA, 0xBBBB, 0xCCCCCC, 0xDDDDDDDD

.data 0x10040020
	.space 128
	
	.globl main

.text
main:
	ori $3, $0, 8
	addi $4, $3, 2
""")

if __name__ == '__main__':
	unittest.main()
