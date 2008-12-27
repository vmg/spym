import os.path
import time

from spym.vm.Parser import AssemblyParser
from spym.vm.RegBank import RegisterBank
from spym.vm.Memory import MemoryManager
from spym.vm.ExceptionHandler import EXCEPTION_HANDLER
from spym.common.Utils import *


class VirtualMachine(object):
	class RuntimeVMException(Exception):
		pass
		
	class HardwareInterrupt(Exception):
		pass
		
	class SoftwareInterrupt(Exception):
		pass
		
	def __init__(self, assembly, exceptionHandler = None, loadAsBuffer = False, enablePseudoInsts = True, memoryBlockSize = 32):
		self.enablePseudoInsts = enablePseudoInsts
		self.memoryBlockSize = memoryBlockSize
		self.assembly = assembly
		self.loadAsBuffer = loadAsBuffer
		self.exceptionHandler = exceptionHandler
		
		self.breakpointed = False
		
		if not loadAsBuffer and not os.path.isfile(assembly):
			raise IOError("Invalid assembly file.")
			
		if exceptionHandler and not os.path.isfile(exceptionHandler):
			raise IOError("Invalid exception/trap file.")
		
		self.__initialize()
		
	def run(self):
		self.parser.resolveGlobalDependencies()
			
		if not '__start' in self.parser.global_labels:
			raise self.RuntimeVMException("Cannot find global '__start' label.")
			
		self.regBank.PC = self.parser.global_labels['__start']
		self.regBank.CP0.Status |= 0x2
		self.regBank.CP0.Compare = 50
		self.regBank[29] = 0x80000000 - 0xC
		
		timer = time.clock()
		
		while 1:
			instruction = self.memory.getInstruction(self.regBank.PC)
			self.regBank.PC += 0x4
			
#			print "Running instruction %s at %s" % (str(instruction), str(self.regBank.PC))
			
			if not instruction:
				break
#				raise self.RuntimeVMException("Attempted to execute non-instruction at %08X" % self.regBank.PC)
				
			try:
				if (time.clock() - timer) * 1000 >= 10.0:
					timer = time.clock()
					self.regBank.CP0.Count += 1
					if self.regBank.CP0.Count == self.regBank.CP0.Compare:
						self.regBank.CP0.Count = 0
						raise self.HardwareInterrupt
						
				instruction(self.regBank)
				
			except self.HardwareInterrupt:
				raise self.RuntimeVMException("Unhandled hardware interrupt.")
			
			except self.SoftwareInterrupt:
				raise self.RuntimeVMException("Unhandled software interrupt.")		
		
		
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
		
		
	def reset(self):
		del(self.parser)
		del(self.memory)
		del(self.regBank)
		
		self.__initialize()
		
	def debugPrintAll(self):
		print str(self.memory)
		
		print "Parsed labels:\n"
		for (label, address) in self.parser.labels.items():
			print "[0x%08x]: '%s'" % (address, label)
		print "\n"
		