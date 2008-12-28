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

import os.path
import time

from spym.vm.memory import MemoryManager
from spym.vm.assembler import AssemblyParser
from spym.vm.regbank import RegisterBank
from spym.vm.exceptions import EXCEPTION_HANDLER, EXCEPTION_HANDLER_ADDR, MIPS_Exception

from spym.common.utils import _debug

class VirtualMachine(object):
	
	EXCEPTIONS = {
		'INT' 	: 0,	# interrupt (hw or sw)
		'TLBPF' : 1,	# TLB: write attempt in protected page
		'TLBML' : 2,	# TLB: inst read attempt in prot. page
		'TLBMS'	: 3,	# TLB: data read attempt in prot. page
		'ADDRL'	: 4,	# address error on read
		'ADDRS' : 5,	# address error on store
		'IBUS'	: 6,	# bus error on inst. search
		'DBUS'	: 7,	# bus error on read/store
		'SYSCALL' : 8,	# system call
		'BKPT'	: 9,	# breakpoint
		'RI'	: 10,	# reserved instruction
		'CU'	: 11,	# coprocessor disabled
		'OVF'	: 12,	# overflow
	}
	
	class RuntimeVMException(Exception):
		pass
		
	def __init__(self, assembly, exceptionHandler = None, loadAsBuffer = False, enablePseudoInsts = True, memoryBlockSize = 32, verboseSteps = False):
		self.enablePseudoInsts = enablePseudoInsts
		self.memoryBlockSize = memoryBlockSize
		self.assembly = assembly
		self.loadAsBuffer = loadAsBuffer
		self.exceptionHandler = exceptionHandler
		self.verboseSteps = verboseSteps
		
		self.breakpointed = False
		self.started = False
		
		if not loadAsBuffer and not os.path.isfile(assembly):
			raise IOError("Invalid assembly file.")
			
		if exceptionHandler and not os.path.isfile(exceptionHandler):
			raise IOError("Invalid exception/trap file.")
		
		self.__initialize()
		
	def __printStep(self, address, instruction):
		output = "[0x%08X]    " % (address)
		output += "0x%08X  " % instruction.mem_content
		text_output = instruction.text.ljust(30) + "; " + (instruction.orig_text if hasattr(instruction, 'orig_text') else "")
		
		_debug(output + text_output + '\n')
		
	def __clock(self, curtime):
		if (curtime - self.cpu_timer) * 1000 >= 10.0:
			self.cpu_timer = curtime
			self.regBank.CP0.Count += 1
			if self.regBank.CP0.Count == self.regBank.CP0.Compare:
				self.regBank.CP0.Count = 0
				raise MIPS_Exception('INT', int_id = 5)
				
	def __vm_loop(self):
		while self.running:
			try:
				self.__clock(time.clock())

				oldPC = self.regBank.PC
				instruction = self.memory.getInstruction(self.regBank.PC)
				
				if not instruction:
					_debug("Attempted to execute non-instruction at 0x%08X\n" % self.regBank.PC)
					break
					
				if self.verboseSteps:
					self.__printStep(self.regBank.PC, instruction)
				
				instruction(self.regBank)
				
				if oldPC == self.regBank.PC:
					self.regBank.PC += 0x4
				
			except MIPS_Exception, cur_exception:
				self.processException(cur_exception)
		
	def resume(self):
		if not self.started or not self.breakpointed:
			raise self.RuntimeVMException("Cannot resume execution -- execution not paused.")
			
		self.breakpointed = False
		self.running = True
		self.__vm_loop()
		
		return 1 if self.breakpointed else 0
			
	def run(self):
		if self.started or self.breakpointed:
			raise self.RuntimeVMException("Reset the Virtual Machine before running again the program.")
			
		if not '__start' in self.parser.global_labels:
			raise self.RuntimeVMException("Cannot find global '__start' label.")
			
		self.regBank.PC = self.parser.global_labels['__start']
		self.regBank.CP0.Status |= 0x2
		self.regBank.CP0.Compare = 1500
		self.regBank[29] = 0x80000000 - 0xC
		
		self.started = True
		self.running = True
		self.breakpointed = False
		
		self.cpu_timer = time.clock()
		self.__vm_loop()
		
		return 1 if self.breakpointed else 0	
				
	def processException(self, exception):
		if exception.code not in self.EXCEPTIONS:
			raise self.RuntimeVMException("Unknown MIPS exception raised.")
			
		_debug("DEBUG: Raised MIPS exception '%s'\n" % exception.code)
						
		code = self.EXCEPTIONS[exception.code]
		
		if code == 0: # interrupt raised
			int_id = exception.int_id
			
			if not 0 <= int_id <= 5:
				raise self.RuntimeVMException("Invalid interrupt source %d." % int_id)
			
			if (self.regBank.CP0.Status & 0x1) and (self.regBank.CP0.Status & (1 << (int_id + 8))):
				self.regBank.CP0.Cause |= (1 << (10 + int_id))
			else: return
			
		elif code == 4 or code == 5: # memory access error
			self.regBank.CP0.BadVAddr = exception.badaddr
			
		elif code == 8: # syscall, hook for 'exit' (10)
			if self.regBank[2] == 10:
				self.running = False
				
#			return
			
		elif code == 9: # breakpoint hook, don't handle by OS
			self.running = False
			self.breakpointed = True
			return
				
		self.regBank.CP0.Cause &= ~0x3C
		self.regBank.CP0.Cause |= (code << 2) # set exception code in the cause register
		
		self.regBank.CP0.Status &= ~0x1	# disable exceptions
		self.regBank.CP0.EPC = self.regBank.PC	# save old PC
		
		self.regBank.CP0.Status &= ~0x2	# enter kernel mode
		self.regBank.PC = EXCEPTION_HANDLER_ADDR # ...and jump to the exception handler
		
	def getAccessMode(self):
		return 'user' if self.regBank.CP0.getUserBit() else 'kernel'
		
	def __initialize(self):
		self.memory = MemoryManager(self, self.memoryBlockSize)
		
		self.parser = AssemblyParser(self.memory, self.enablePseudoInsts)
		self.regBank = RegisterBank(self.memory)
		
		if self.exceptionHandler:
			self.parser.parseFile(self.exceptionHandler)
		else:
			self.parser.parseBuffer(EXCEPTION_HANDLER)
		
		if self.loadAsBuffer:
			self.parser.parseBuffer(self.assembly)
		else:
			self.parser.parseFile(self.assembly)
		
		self.parser.resolveGlobalDependencies()
		
	def reset(self):
		del(self.parser)
		del(self.memory)
		del(self.regBank)
		
		self.started = False
		self.breakpointed = False
		self.__initialize()
		
	def debugPrintAll(self):
		_debug(str(self.memory))
		
		label_output = "Defined global labels:\n"
		for (label, address) in self.parser.global_labels.items():
			label_output += "    [0x%08x]: '%s'\n" % (address, label)
		label_output += "\n\n"
		
		_debug(label_output)
		_debug(str(self.regBank))
		