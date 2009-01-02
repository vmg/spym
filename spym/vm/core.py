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

import os.path, time, sys, pdb

from spym.vm.exceptions import * #EXCEPTION_HANDLER, EXCEPTION_HANDLER_ADDR, MIPS_Exception
from spym.common.utils import _debug, buildLineOfCode, bin

class VirtualMachine(object):
	
	SCREEN = 'screen'
	KEYBOARD = 'keyboard'
	CLOCK = 'clock'
	L1_CACHE = 'l1cache'
	L2_CACHE = 'l2cache'
	
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
					debugPoints = [],
					standardInput = None,
					standardOutput = None,
					enableDelaySlot = True):
					
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
		self.enableDelaySlot = enableDelaySlot
		
		self.breakpointed = False
		self.started = False
		self.doStep = False
		
		self.stdout = standardOutput or sys.stdout
		self.stdin = standardInput or sys.stdin
		
		if defaultMemoryMappedIO:
			from spym.vm.devices import TerminalScreen, TerminalKeyboard 
			self.deviceInformation[self.SCREEN] = TerminalScreen
			self.deviceInformation[self.KEYBOARD] = TerminalKeyboard
			
		if self.CLOCK not in self.deviceInformation:
			from spym.vm.devices import CPUClock_TIMER
			self.deviceInformation[self.CLOCK] = CPUClock_TIMER

		if defaultMemoryMappedIO and virtualSyscalls:
			raise self.ConfigVMException(
				"Cannot virtualize I/O syscalls when memory mapped I/O\
				 is enabled.")
		
		if not loadAsBuffer and not os.path.isfile(assembly):
			raise self.ConfigVMException("Invalid assembly file.")
			
		if exceptionHandler and not os.path.isfile(exceptionHandler):
			raise self.ConfigVMException("Invalid exception/trap file.")
		
		self.__initialize()
		
	def __syscallVirtualization(self):
		# v0 should contain the code for the syscall
		syscall_code = self.regBank[2] 
		
		if syscall_code == 1:
			self.stdout.write(str(self.regBank[4]))
			
		elif syscall_code == 4:
			memory_ptr = self.regBank[4]
			
			while True:
				out_char = self.memory[memory_ptr, 1]
				if not out_char:
					break
					
				self.stdout.write(chr(out_char))
				memory_ptr += 1
		
		elif syscall_code == 5:
			number = self.stdin.readline(16)
			
			try:
				number = int(number, 0)
			except ValueError:
				raise self.RuntimeVMException(
					"Invalid integer in READ_INT syscall.")
				
			self.regBank[2] = number
		
		elif syscall_code == 8:
			in_str = self.stdin.readline(self.regBank[5])
			if in_str.endswith('\n'):
				in_str = in_str[0:-1]
				
			mem_ptr = self.regBank[4]
			
			for c in in_str:
				self.memory[mem_ptr, 1] = ord(c)
				mem_ptr += 1
				
			self.memory[mem_ptr, 1] = 0
		
		else:
			raise self.RuntimeVMException(
				"Unimplemented syscall code: %d" % syscall_code)
			
		# hack: stdout gets clogged with the charspam, 
		# flush it after each syscall
		self.stdout.flush() 
				
	def __runDevices(self):
		for device in self.devices_list:
			device.tick()
			
	def __runInstruction(self, instruction):
		if not hasattr(instruction, '_vm_asm'):
			raise self.RuntimeVMException(
				"Attempted to execute non-instruction at 0x%08X\n" % 
				self.regBank.PC)
			
		instruction._vm_asm(self.regBank)
				
	def __vm_loop(self):
		while self.running:
			try:				
				self.__runDevices()

				did_delay_slot = False
				oldPC = self.regBank.PC
				instruction = self.memory[self.regBank.PC, 4]
				
				# if the instruction does have a delay, and delay slots
				if (hasattr(instruction, '_delay') 
					and instruction._delay 
					and self.enableDelaySlot):
				# are enabled, we need to handle it...
					
					# what we are doing is fetching the instruction AFTER the 
					# current one (the one which should go into the delay 
					# slot) and executing it first...
					did_delay_slot = True
					delay_slot = self.memory[self.regBank.PC + 0x4, 4]
					
					if self.verboseSteps:
						_debug('[DELAYED BR]\n' + 
							buildLineOfCode(self.regBank.PC + 0x4, delay_slot))
					
					# if an exception is raised when executing the instruction
					# in the delay slot, we handle it like it was caused in 
					# the jump, then the handler should set the PC to execute 
					# the delay slot again hence we increase the PC to skip 
					# the delay slot, and continue the execution.
					try: self.__runInstruction(delay_slot)
					except MIPS_Exception as cur_exception:
						self.processException(cur_exception)
						self.regBank.PC += 0x4
						continue
					
				if self.verboseSteps:
					_debug(buildLineOfCode(self.regBank.PC, instruction))
					
				if self.regBank.PC in self.debugPoints or self.doStep:
					self.currentLine = buildLineOfCode(
						self.regBank.PC, instruction)
						
					pdb.set_trace()
					
				self.__runInstruction(instruction)
				
				if oldPC == self.regBank.PC:
					self.regBank.PC += 0x8 if did_delay_slot else 0x4
			
			except MIPS_Exception as cur_exception:
				self.processException(cur_exception)
		
	def resume(self):
		if not self.started or not self.breakpointed:
			raise self.RuntimeVMException(
				"Cannot resume execution -- execution not paused.")
			
		self.breakpointed = False
		self.running = True
		self.__vm_loop()
		
		return 1 if self.breakpointed else 0
			
	def run(self):
		if self.started or self.breakpointed:
			raise self.RuntimeVMException(
				"Reset the Virtual Machine before running again the program.")
			
		if not '__start' in self.parser.global_labels:
			raise self.RuntimeVMException(
				"Cannot find global '__start' label.")
			
		# load PC with the default start
		self.regBank.PC = self.parser.global_labels['__start'] 
		
		if not self.runAsKernel:
			# enter user mode
			self.regBank.CP0.Status |= 0x2 
		
		# enable all interrupt masks and the global interrupt switch
		self.regBank.CP0.Status |= 0xFF01 
			
		# clock ticks until next interrupt
		self.regBank.CP0.Compare = 1500 
		
		# stack pointer -- set a tad lower to fake argc and argv
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
			
		if self.verboseSteps:
			_debug("[ EXCEPTION]    Raised MIPS exception '%s' (%s).\n" % (
				exception.code, exception.debug_msg))
		
		code = self.EXCEPTIONS[exception.code]
		
		if code == 0: # interrupt raised
			int_id = exception.int_id
			
			if not 0 <= int_id <= 5:
				raise self.RuntimeVMException(
					"Invalid interrupt source %d." % int_id)
			
			# if the global interrupt enable is on, and the source is 
			# not masked, flag a cause bit
			if (self.regBank.CP0.Status & 0x1) and (
				self.regBank.CP0.Status & (1 << (int_id + 8))):
					
				self.regBank.CP0.Cause |= (1 << (10 + int_id))
			
			else: 
				return
			
		elif code == 4 or code == 5: # memory access error
			self.regBank.CP0.BadVAddr = exception.badaddr
			
		elif code == 8: # syscall, hook for 'exit' (10)
			if self.regBank[2] == 10:
				self.running = False
			elif self.regBank[2] == 17: # exit2
				self.running = False
				
				if self.regBank[4]:
					pdb.set_trace()
					raise self.RuntimeVMException(
						"Program terminated with error code %d" % 
							self.regBank[4])
				
			elif self.virtualSyscalls:
				self.__syscallVirtualization()
				self.regBank.PC += 0x4 # skip syscall instruction...
				return
			
		elif code == 9: # breakpoint hook, don't handle by OS
			self.running = False
			self.breakpointed = True
			return
				
		self.regBank.CP0.Cause &= ~0x3C
		
		# set exception code in the cause register
		self.regBank.CP0.Cause |= (code << 2) 
		
		# get the lowest 6 bits from Status
		lowbits = self.regBank.CP0.Status & 0x3F 
		# ...and clear them on the register
		self.regBank.CP0.Status &= ~0x3F 
		# load them back shifted, so two new zeros appear
		self.regBank.CP0.Status |= (lowbits << 2) & 0x3F 
		
		self.regBank.CP0.EPC = self.regBank.PC	# save old PC
		# ...and jump to the exception handler
		self.regBank.PC = EXCEPTION_HANDLER_ADDR 
		
	def getAccessMode(self):
		return 'user' if self.regBank.CP0.getUserBit() else 'kernel'
		
	def __initialize(self):
		# core elements
		from spym.vm.memory import MemoryManager
		
		cache_data = (
			{	# LEVEL 1 Data Cache	
				'cacheMapping' : 'direct',
				'numberOfLines' : 8, # 1024 lines = 32KB of data
			},
			{	# LEVEL 1 Code Cache	
				'cacheMapping' : 'direct',
				'numberOfLines' : 2048,	# 2048 lines = 64KB of code
			},
		)
		
		self.memory = MemoryManager(self, cache_data)
		
		from spym.vm.assembler import AssemblyParser
		self.parser = AssemblyParser(self.memory, self.enablePseudoInsts)

		from spym.vm.regbank import RegisterBank		
		self.regBank = RegisterBank(self.memory)
		
		# device initialization
		self.devices_list = []
		interrupt_handlers = []
		device_kb = None
		device_scr = None
		
		for (device_name, device) in self.deviceInformation.items():
			device_params = {}
			
			if isinstance(device, tuple):
				device, device_params = device
	
			device_instance = device(len(self.devices_list), **device_params)
			
			if (not hasattr(device_instance, 'tick') or 
				not hasattr(device_instance, '__getitem__') or 
				not hasattr(device_instance, '__setitem__')):
				raise self.ConfigVMException(
					"Device '%s' doesn't implement the standard Device Interface." 
						% device_name)
			
			if 	not hasattr(device_instance, '_memory_map'):
				raise self.ConfigVMException(
					"Device '%s' doesn't have memory mappings." % device_name)
			
			for memory_address in device_instance._memory_map:
				self.memory.devices_memory_map[memory_address] = device_instance
				
			if (hasattr(device_instance, '_interrupt_handler') and 
				hasattr(device_instance, '_interrupt_handler_label')):
				interrupt_handlers.append(
					(
						len(self.devices_list), 
						device_instance._interrupt_handler, 
						device_instance._interrupt_handler_label
					))
			
			self.devices_list.append(device_instance)
			
			if device_name == self.KEYBOARD:
				device_kb = device_instance
			elif device_name == self.SCREEN:
				device_scr = device_instance
			
		if not self.virtualSyscalls and (not device_kb or not device_scr):
			raise self.ConfigVMException(
				"""Virtualized syscalls are disabled but there 
				are no memory-mapped devices able to emulate their 
				implementation.""")	
		
		# assembly loading / parsing
		if self.exceptionHandler:
			self.parser.parseFile(self.exceptionHandler)
		else:
			if not self.virtualSyscalls:
				keyboard_address = min(device_kb._memory_map)
				screen_address = min(device_scr._memory_map)
				
				ktext = getKernelText(True, True, 
					interrupt_handlers, 
					screen_address, 
					keyboard_address)
			else:
				ktext = getKernelText(True, False, 
					interrupt_handlers)
				
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
			