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

import time
from spym.vm.exceptions import MIPS_Exception
from spym.common.utils import *
from spym.common.utils import _debug

class CPUClock(object):
	def __init__(self, int_level, frequency_hz = 1.0):
		self.loop_time = (1.0 / frequency_hz)
		self.timer = time.time()
		self.int_enable = 0
		self.clock_bit = 0
		
	def _memory_map(self):
		return (0xFFFF0010, )
		
	def tick(self):
		if time.time() - self.timer > self.loop_time:
			self.timer = time.time()
			self.clock_bit = 1
			
			if self.int_enable:
				raise MIPS_Exception('INT', int_id = self.int_level, debug_msg = 'Tick!')
			
	def __getitem__(self, addr):
		address, offset, size = breakAddress(addr)
		return 0x0 if offset else ((self.clock_bit << 1) | self.int_enable)
		
	def __setitem__(self, addr, value):
		address, offset, size = breakAddress(addr)
		if offset == 0:
			self.int_enable = value & 0x1
			self.clock_bit = (value >> 1) & 0x1