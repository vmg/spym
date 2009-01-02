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
import re, os
from spym.vm.preprocessor import AssemblyPreprocessor
from spym.vm.pseudoinstructions import PseudoInstructionAssembler
from spym.vm.instructions import InstructionAssembler
from spym.common.utils import _debug

class AssemblyParser(object):
	"""Core for the assembly parsing routines."""
	
	TOKENIZER_REGEX = r"(?<![\(])[\s,]+(?!\s*?[\(\)])"
		
	class ParsingFailed(Exception):
		pass
	
	class ParserException(Exception):
		pass
	
	def __init__(self, vm_memory, enablePseudoInsts = True):
		self.memory = vm_memory.main_memory
	
		self.preprocessor = AssemblyPreprocessor(self, self.memory)
		
		if enablePseudoInsts:
			self.instruction_assembler = PseudoInstructionAssembler(self)
		else:
			self.instruction_assembler = InstructionAssembler(self)
			
		self.global_labels = {}
		self.labels = {}
		
		self.parsedFiles = 0
		
	def __checkLabel(self, label):
		if label in self.labels:
			raise self.ParserException("Redefinition of label '%s'." % label)
		
		if not re.match(r'^[^\d]\w+$', label):
			raise self.ParserException("Malformed label.")
			
	def parse(self, asm):
		if os.path.isfile(asm):
			self.parseFile(asm)
		else:
			self.parseBuffer(asm)
			
	def parseFile(self, filename):
		with open(filename, 'r') as asm_file:
			self.__parse(filename, asm_file)
			
	def parseBuffer(self, buff):
		self.__parse("_asm_buffer%02d" % self.parsedFiles, buff.split('\n'))
		
	def __parse(self, namespace, asm_contents):
		self.local_labels = {}
		local_instructions = []
		self.cur_address = 0x0
		
		for (line_no, line) in enumerate(asm_contents):
			line_no = line_no + 1
			label, identifier, args = self.__parseLine(line)
			args = args or []
			
			try:
				if label:
					self.__checkLabel(label)
					self.local_labels[label] = self.cur_address
			
				if identifier:
					if identifier[0] == '.':
						old_line_start = self.cur_address
						
						new_line_start, self.cur_address = self.preprocessor(
							identifier, args, self.cur_address)
						
						for (l, a) in self.local_labels.items():
							if a == old_line_start:
								self.local_labels[l] = new_line_start

					else:
						inst_code = self.instruction_assembler(identifier, args)
						if not isinstance(inst_code, list):
							inst_code = [inst_code, ]

						setattr(inst_code[0], 'orig_text', 
							"%03d:  %s" % (line_no, line.strip()))
					
						for inst in inst_code:
							if hasattr(inst, '_inst_bld_tmp'):
								local_instructions.append(self.cur_address)
											
							self.memory[self.cur_address, 4] = inst
							self.cur_address += 0x4
					
			except (self.ParserException, 
					AssemblyPreprocessor.PreprocessorException, 
					InstructionAssembler.InstructionAssemblerException) 
					as parsing_exception:
					
				raise self.ParsingFailed("\nLINE %d:\t%s\n  %s" % (
					line_no, line.strip(), parsing_exception))
						
		self.parsedFiles += 1
		
		for inst_address in local_instructions:
			self.memory[inst_address, 4] = \
				self.instruction_assembler.resolveLabels(
					self.memory[inst_address, 4], 
					inst_address, 
					self.local_labels)
		
		for (label, address) in self.global_labels.items():
			if address is None:
				if label not in self.local_labels:
					raise self.LabelException(
						"Missing globally defined label '%s'" % label)

				self.global_labels[label] = self.local_labels[label]
			
	def resolveGlobalDependencies(self):
		for (inst_address, instruction) in self.memory.getInstructionData():
			if hasattr(instruction, '_inst_bld_tmp'):
				
				new_instruction = self.instruction_assembler.resolveLabels(
					instruction, 
					inst_address, 
					self.global_labels)
				
				if hasattr(new_instruction, '_inst_bld_tmp'):
					raise self.ParserException(
						"Cannot resolve label in instruction '%s' @ %08X" % (
							str(instruction._inst_bld_tmp), inst_address))
					
				self.memory[inst_address, 4] = new_instruction
		
	def __parseLine(self, line):
		line_label = None
		line_id = None
		line_args = None
		
		line = line.split('#', 1)[0].strip()
		
		if ':' in line:
			line_label, line = line.split(':', 1)
			line_label = line_label.strip()
			line = line.strip()
		
		line_tokens = line.split(None, 1)
		
		if line_tokens:
			line_id = line_tokens[0].lower()
		
			if len(line_tokens) > 1:
				if line_id == '.ascii' or line_id == '.asciiz':
					line_args = [line_tokens[1].strip(), ]
				else:
					#line_args = map(str.strip, line_tokens[1].split(','))
					line_args = re.split(self.TOKENIZER_REGEX, line_tokens[1])
		
		return (line_label, line_id, line_args)
		
