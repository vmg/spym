# Copyright (c) 2009 Vicent Marti
# 
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

class RegisterBank(object):
    REGISTER_NAMES = {
        "$zero" : 0, "$at" : 1,
        "$v0" : 2, "$v1" : 3,
        "$a0" : 4, "$a1" : 5,
        "$a2" : 6, "$a3" : 7,
        "$t0" : 8, "$t1" : 9,
        "$t2" : 10, "$t3" : 11,
        "$t4" : 12, "$t5" : 13,
        "$t6" : 14, "$t7" : 15,
        "$t8" : 24, "$t9" : 25,
        "$s0" : 16, "$s1" : 17,
        "$s2" : 18, "$s3" : 19,
        "$s4" : 20, "$s5" : 21,
        "$s6" : 22, "$s7" : 23,
        "$k0" : 26, "$k1" : 27,
        "$gp" : 28, "$sp" : 29,
        "$fp" : 30, "$ra" : 31
    }
        
    class CoprocessorZero(object):
        STATUS_USER_MASK = 0x0002
        REGISTER_NAMES = {
            8   : 'BadVAddr',
            9   : 'Count',
            11  : 'Compare',
            12  : 'Status',
            13  : 'Cause',
            14  : 'EPC',
            16  : 'Config',
        }
        
        def __init__(self):
            self.BadVAddr   = 0x0
            self.Count      = 0x0
            self.Compare    = 0x0
            self.Status     = 0x0
            self.Cause      = 0x0
            self.EPC        = 0x0
            self.Config     = 0x0
                    
        def getUserBit(self):
            return self.Status & self.STATUS_USER_MASK
            
        def __getitem__(self, item):
            assert(self.getUserBit() == 0)
                
            if item in self.REGISTER_NAMES:
                return getattr(self, self.REGISTER_NAMES[item])
            
            elif isinstance(attr, str) and hasattr(self, item):
                return getattr(self, item)
                
            return 0x0
        
        def __setitem__(self, item, data):
            assert(self.getUserBit() == 0)
                
            data = data & 0xFFFFFFFF
                
            if item in self.REGISTER_NAMES:
                setattr(self, self.REGISTER_NAMES[item], data)
            elif hasattr(self, item):
                setattr(self, item, data)
    
    def __init__(self, vm_memory):
        self.std_registers = 32 * [0, ]
        self.HI = 0x0
        self.LO = 0x0
        self.PC = 0x0
        
        self.CP0 = self.CoprocessorZero()
        self.memory = vm_memory
        
    def __getitem__(self, item):
        return self.std_registers[item] if item else 0
            
    def __setitem__(self, item, value):
        if item: self.std_registers[item] = value & 0xFFFFFFFF
        
    def __str__(self):
        regbank_output = "MIPS R2000 Register Bank\n"
        
        regbank_output += (
            "HI: 0x%08X  |  LO: 0x%08X  |  PC: 0x%08X" %
                (self.HI, self.LO, self.PC)).center(74)
                
        regbank_output += '\n'
        
        for i in range(len(self.std_registers)):
            regbank_output += ("$%d: " % i).rjust(5)
            regbank_output += "0x%08X" % self.std_registers[i]
            regbank_output += "\n" if i % 4 == 3 else "  |  "

        return regbank_output
