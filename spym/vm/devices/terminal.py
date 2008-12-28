import os, sys, tty
from spym.vm.exceptions import MIPS_Exception
from spym.common.utils import *
from select import select

class NotTTYException(Exception): pass

class TerminalFile:
    def __init__(self,infile):
        if not infile.isatty():
            raise NotTTYException()
        self.file=infile

        #prepare for getch
        self.save_attr=tty.tcgetattr(self.file)
        newattr=self.save_attr[:]
        newattr[3] &= ~tty.ECHO & ~tty.ICANON
        tty.tcsetattr(self.file, tty.TCSANOW, newattr)

    def __del__(self):
        import tty  #required this import here
        tty.tcsetattr(self.file, tty.TCSADRAIN, self.save_attr)

    def getch(self):
        if select([self.file],[],[],0)[0]:
            c=self.file.read(1)
        else:
            c=''
        return c

class TerminalScreen(object):
	MAP_CTRL = 0xFFFF0008
	MAP_DATA = 0xFFFF000C
	
	SCREEN_WRITE_DELAY = 5
	
	def __init__(self, interrupt_level, stdout = None, delayed_io = True):
		self.control_register = 0x00000001
		self.data_register = 0x0
		self.delayed_io = delayed_io
		self.interrupt_level = interrupt_level
		
		self.stdout = stdout or sys.stdout
		
	def printCharacter(self):
		self.stdout.write(chr(self.data_register))
		self.control_register |= 0x1
		
		if self.control_register & 0x2:
			raise MIPS_Exception('INT', int_id = self.interrupt_level)
		
	def _memory_map(self):
		return (self.MAP_CTRL, self.MAP_DATA)

	def tick(self):
		if self.delayed_io and not self.control_register & 0x1:
			self.delay_count = self.delay_count - 1
			if not self.delay_count:
				self.printCharacter()
		
	def __setitem__(self, addr, data):
		address, offset, size = breakAddress(addr)
		
		if offset: return
		
		if address == self.MAP_DATA and self.control_register & 0x1: # ready?
			self.data_register = data & 0xFF
			
			if self.delayed_io:
				self.control_register &= ~0x1
				self.delay_count = self.SCREEN_WRITE_DELAY
			else:
				self.printCharacter()
				
		elif address == self.MAP_CTRL:
			self.control_register &= ~0x2
			self.control_register |= data & 0x2
		
	def __getitem__(self, addr):
		address, offset, size = breakAddress(addr)
		
		if offset: return 0x0
		
		if address == self.MAP_DATA:
			return self.data_register & 0xFF
		elif address == self.MAP_CTRL:
			return self.data_register & 0xFF
		
class TerminalKeyboard(object):
	MAP_DATA = 0xFFFF0003
	MAP_CTRL = 0xFFFF0000
	
	def __init__(self, interrupt_level, stdin = None):
		self.interrupt_level = interrupt_level
		self.control_register = 0x0
		self.data_register = 0x0
		
		self.terminal_io = TerminalFile(stdin or sys.stdin)
		
	def _memory_map(self):
		return (self.MAP_DATA, self.MAP_CTRL)
		
	def tick(self):
		# TODO: maybe make this blocking, i.e. don't allow to overwrite the character until
		# the current one has been read
		char_in = self.terminal_io.getch()
		
		if char_in:
			self.data_register = ord(char_in)
			self.control_register |= 0x1
			
			if self.control_register & 0x2:
				raise MIPS_Exception('INT', int_id = self.interrupt_level)
		
	def __setitem__(self, addr, data):
		address, offset, size = breakAddress(addr)
		
		if offset == 0 and address == self.MAP_CTRL:
			self.control_register &= ~0x2
			self.control_register |= data & 0x2
		
	def __getitem__(self, addr):
		address, offset, size = breakAddress(addr)
		if offset: return 0x0
		
		if address == self.MAP_DATA:
			self.control_register &= ~0x1
			return self.data_register & 0xFF
		
		elif address == self.MAP_CTRL:
			return self.data_register & 0xFF