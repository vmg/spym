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

from spym.vm.exceptions import * #EXCEPTION_HANDLER, EXCEPTION_HANDLER_ADDR, MIPS_Exception
from spym.common.utils import _debug, buildLineOfCode

class VirtualMachine(object):
	
	SCREEN = 'screen'
	KEYBOARD = 'keyboard'
	
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
	
	class RuntimeVMException(Exception): pass
	class ConfigVMException(Exception): pass
	
	def __init__(self, assembly, 
					runAsKernel = False,
					defaultMemoryMappedIO = False,
					memoryMappedDevices = {},
					virtualSyscalls = True,
					exceptionHandler = None, 
					loadAsBuffer = False, 
					enablePseudoInsts = True, 
					memoryBlockSize = 32, 
					verboseSteps = False,
					debugPoints = []):
					
		self.enablePseudoInsts = enablePseudoInsts
		self.memoryBlockSize = memoryBlockSize
		self.assembly = assembly
		self.loadAsBuffer = loadAsBuffer
		self.exceptionHandler = exceptionHandler
		self.verboseSteps = verboseSteps
		self.deviceInformation = memoryMappedDevices
		self.runAsKernel = runAsKernel
		self.virtualSyscalls = virtualSyscalls
		self.defaultMemoryMappedIO = defaultMemoryMappedIO
		self.debugPoints = debugPoints
		
		self.breakpointed = False
		self.started = False
		
		if defaultMemoryMappedIO:
			from spym.vm.devices import TerminalScreen, TerminalKeyboard 
			self.deviceInformation[self.SCREEN] = TerminalScreen
			self.deviceInformation[self.KEYBOARD] = TerminalKeyboard
			
		# TODO: assert when having memory-mapped keyboards/screens and using
		# syscalls to read or print shit.
		
		if not loadAsBuffer and not os.path.isfile(assembly):
			raise IOError("Invalid assembly file.")
			
		if exceptionHandler and not os.path.isfile(exceptionHandler):
			raise IOError("Invalid exception/trap file.")
		
		self.__initialize()
		
	def __clock(self, curtime):
		if (curtime - self.cpu_timer) * 1000 >= 10.0:
			self.cpu_timer = curtime
			self.regBank.CP0.Count += 1
			if self.regBank.CP0.Count == self.regBank.CP0.Compare:
				self.regBank.CP0.Count = 0
				raise MIPS_Exception('INT', int_id = 5)
				
	def __runDevices(self):
		for device in self.devices_list:
			device.tick()
				
	def __vm_loop(self):
		while self.running:
			try:
#				self.__clock(time.clock())
				self.__runDevices()

				oldPC = self.regBank.PC
				instruction = self.memory.getInstruction(self.regBank.PC)
				
				if not instruction:
					_debug("Attempted to execute non-instruction at 0x%08X\n" % self.regBank.PC)
					break
					
				if self.verboseSteps:
					_debug(buildLineOfCode(self.regBank.PC, instruction))
					
				if self.regBank.PC in self.debugPoints:
					_debug(str(self.regBank))
				
				instruction(self.regBank)
				
				if oldPC == self.regBank.PC:
					self.regBank.PC += 0x4
			
			except MIPS_Exception as cur_exception:
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
			
		self.regBank.PC = self.parser.global_labels['__start'] # load PC with the default start
		
		if not self.runAsKernel:
			self.regBank.CP0.Status |= 0x2 # enter user mode
			
		self.regBank.CP0.Compare = 1500 # clock ticks until next interrupt
		self.regBank[29] = 0x80000000 - 0xC # stack pointer -- set a tad lower to fake argc and argv
		
		self.started = True
		self.running = True
		self.breakpointed = False
		
		self.cpu_timer = time.clock()
		self.__vm_loop()
		
		return 1 if self.breakpointed else 0	
				
	def processException(self, exception):
		if exception.code not in self.EXCEPTIONS:
			raise self.RuntimeVMException("Unknown MIPS exception raised.")
			
		if self.verboseSteps:
			_debug("[ EXCEPTION]    Raised MIPS exception '%s' (%s).\n" % (exception.code, exception.debug_msg))
						
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
			elif self.virtualSyscalls:
				raise self.RuntimeVMException("Virtualized SYSCALLS are not implemented yet.")
			
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
		# core elements
		from spym.vm.memory import MemoryManager
		self.memory = MemoryManager(self, self.memoryBlockSize)
		
		from spym.vm.assembler import AssemblyParser
		self.parser = AssemblyParser(self.memory, self.enablePseudoInsts)

		from spym.vm.regbank import RegisterBank		
		self.regBank = RegisterBank(self.memory)
		
		# device initialization
		self.devices_list = []
		device_kb = None
		device_scr = None
		
		for (device_name, device) in self.deviceInformation.items():
			device_params = {}
			
			if isinstance(device, tuple):
				device, device_params = device
	
			device_instance = device(len(self.devices_list), **device_params)
			
			for memory_address in device_instance._memory_map():
				self.memory.devices_memory_map[memory_address] = device_instance
			
			self.devices_list.append(device_instance)
			
			if device_name == self.KEYBOARD:
				device_kb = device_instance
			elif device_name == self.SCREEN:
				device_scr = device_instance
			
		if not self.virtualSyscalls and (not device_kb or not device_scr):
			raise self.ConfigVMException("Virtualized syscalls are disabled but there are no memory-mapped devices able to emulate their implementation.")	
		
		# assembly loading / parsing
		if self.exceptionHandler:
			self.parser.parseFile(self.exceptionHandler)
		else:
			if not self.virtualSyscalls:
				keyboard_address = min(device_kb._memory_map())
				screen_address = min(device_scr._memory_map())
				ktext = getKernelText(True, True, screen_address, keyboard_address)
			else:
				ktext = getKernelText(True, False)
				
			self.parser.parseBuffer(ktext)
		
		if self.loadAsBuffer:
			self.parser.parseBuffer(self.assembly)
		else:
			self.parser.parseFile(self.assembly)
		
		self.parser.resolveGlobalDependencies()
		
	def reset(self):
		del(self.parser)
		del(self.memory)
		del(self.regBank)
		del(self.devices_list)
		
		self.started = False
		self.breakpointed = False
		self.__initialize()
		
	def debugPrintAll(self, labels = True, memory = True, regbank = True):
		if memory:
			_debug(str(self.memory))
		
		if labels:
			label_output = "Defined global labels:\n"
			for (label, address) in self.parser.global_labels.items():
				label_output += "    [0x%08x]: '%s'\n" % (address, label)
			label_output += "\n\n"
		
			_debug(label_output)
			
		if regbank:
			_debug(str(self.regBank))
