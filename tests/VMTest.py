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

from spym.vm.core import VirtualMachine
from spym.vm.devices import TerminalKeyboard, TerminalScreen

class GlobalASMTests(unittest.TestCase):
	def _runTest(self, asm, lab = True):
		devicedata = [
			(TerminalScreen, {'delayed_io' : False})
		]
		
		vm = VirtualMachine(asm, devices = devicedata, loadAsBuffer = lab, enablePseudoInsts = True, verboseSteps = False, runAsKernel = True)
		vm.run()
#		vm.debugPrintAll()
		
	def XXXtestASM2(self):
		self._runTest('testprogram.s', False)
		
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
	li $7, 4
	lw $5, bdata+4($7)
	addi $4, $3, 2
	add $3, $7, 0x7FFFABC0
	
	li $7, 'X'
	sb $7, +0xFFFF000C
	
	jr $ra
""")

if __name__ == '__main__':
	unittest.main()
