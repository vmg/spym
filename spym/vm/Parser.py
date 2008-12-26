from __future__ import with_statement

import re

from spym.vm.PseudoInstructions import PseudoInstBuilder
from spym.vm.RegBank import RegisterBank
from spym.vm.Instructions import InstBuilder
from spym.vm.Memory import MemoryManager
from spym.vm.Preprocessor import AssemblyPreprocessor

from spym.common.Utils import *
	
class AssemblyParser(object):
	"""Core for the assembly parsing routines."""
	
	TOKENIZER_REGEX = r"(?<![\(])[\s,]+(?!\s*?[\(\)])"
	
	SYNTAX_DATA = {
		'arithlog'	:	('R', ['$d', '$s', '$t'])
		'divmult' 	:	('R', ['$s', '$t'])
		'shift'		:	('R', ['$d', '$t', 'a'])
		'shiftv'	:	('R', ['$d', '$t', '$s'])
		'jumpr'		:	('R', ['$s'])
		'movefrom'	:	('R', ['$d'])
		'moveto'	:	('R', ['$s'])
		'arithlogi'	:	('I', ['$t', '$s', 'imm'])
		'loadi'		:	('I', ['$t', 'imm'])
		'branch'	:	('I', ['$s', '$t', 'label'])
		'branchz'	:	('I', ['$s', 'label'])
		'loadstore'	:	('I', ['$t', 'imm', '($s)'])
		'jump'		:	('J', ['label'])
		'none'		:	('R', [])
	}
		
	class LabelException(Exception):
		pass
		
	class SyntaxException(Exception):
		pass
		
	class ParserException(Exception):
		pass
	
	def __init__(self, vm_memory, enablePseudoInsts = True):
		self.memory = vm_memory
		
		self.preprocessor = AssemblyPreprocessor(self, vm_memory)
		self.builder = PseudoInstBuilder() if enablePseudoInsts else InstBuilder()
		self.global_labels = {}
		self.labels = {}
		
		self.parsedFiles = 0
		
		self._initSyntaxData()
		
	def _checkLabel(self, label):
		if label in self.labels:
			raise self.LabelException("Redefinition of label '%s'." % label)
		
		if not re.match(r'^[^\d]\w+$', label):
			raise self.LabelException("Malformed label.")
			
	def parseFile(self, filename):
		with open(filename, 'r') as asm_file:
			self._parse(filename, asm_file)
			
	def parseBuffer(self, buff):
		self._parse("_asm_buffer%02d" % self.parsedFiles, buff.split('\n'))
		
	def _parse(self, namespace, asm_contents):
		local_labels = {}
		local_instructions = []
		self.cur_address = 0x0
		
		for line in asm_contents:
			label, identifier, args = self._parseLine(line)
			args = args or []
			
			if label:
				self._checkLabel(label)
				local_labels[label] = self.cur_address
			
			if identifier:
				if identifier[0] == '.':
					self.cur_address = self.preprocessor(identifier, args, self.cur_address)
				else:
					inst_code = self.builder.buildFunction(identifier, args)
					if not isinstance(inst_code, list):
						inst_code = [inst_code, ]
						
					inst_code[0].func_dict['parsed_text'] = ""#identifier + " " + ", ".join(args)
					
					for inst in inst_code:
						if hasattr(inst, '_inst_bld_tmp'):
							local_instructions.append(inst)
											
						self.memory[self.cur_address] = inst
						self.cur_address += 0x4
						
		self.parsedFiles += 1
		
		for instruction in local_instructions:
			self.builder.completeFunction(instruction, local_labels)
		
		for (label, address) in self.global_labels.items():
			if address is None:
				if label not in local_labels:
					raise self.LabelException("Missing globally defined label '%s'" % label)

				self.global_labels[label] = local_labels[label]
			
	def resolveGlobalDependencies(self):
		for instruction in self.memory.getInstructionData():
			if hasattr(instruction, '_inst_bld_tmp') and not self.builder.completeFunction(instruction, self.global_labels):
				raise self.LabelException("Cannot resolve label in instruction '%s'" % str(instruction))
				
	def _parseInstruction(self, identifier, args):
		if identifier not in self.parsed_syntax_data:
			raise self.ParserException("Unknown instruction: '%s" % identifier)
			
		encoding, syntax, opcode = self.parsed_syntax_data[identifier]
		
		if len(syntax) != len(args):
			raise self.ParserException("Instruction %s takes %d parameters." % identifier)
		
		parsed_args = []
		encoder_args = {}

		for (arg_data, argument) in zip(syntax, args):
			if arg_data == 'imm':
				try:
					parsed_args.append(int(argument, 0))
				except ValueError:
					raise self.ParserException("Error when parsing %s as integer immediate." % argument)
				
			elif arg_data[0] == '$':
				reg = self._parseRegister(argument)
				parsed_args.append()
			elif arg_data[0] == '(' and arg_data[-1] == ')':
				parsed_args.append(self._parseRegister(argument[1:-1]))
			elif arg_data == 'label':
				parsed_args.append(argument)
								
		instruction_closure = self.builder.buildFunction(identifier, tuple(parsed_args))
		
		instruction_closure.func_dict['mem_content'] = self.encoder(encoding, opcode, )
			
	def _parseRegister(self, reg):
		if reg in RegisterBank.REGISTER_NAMES:
			return RegisterBank.REGISTER_NAMES[reg]

		reg_match = re.match(r'^\$(\d{1,2})$', reg)

		if not reg_match or not 0 <= int(reg_match.group(1)) < 32:
			raise self.ParserException("Invalid register name (%s)" % reg)

		return int(reg_match.group(1))
		
	def _parseLine(self, line):
		line_label = None
		line_id = None
		line_args = None
		
		line = line.split('#', 1)[0].strip()
		
		if ':' in line:
			line_label, line = map(str.strip, line.split(':', 1))
		
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
	
	def _parseSyntaxData(self, docstring):
		opcode = None
		syntax = None
		encoding = None
		
		for line in docstring:
			if not ':' in line: continue
			lname, contents = line.strip().split(':', 1)
			lname = lname.lower().strip()
			contents = contents.strip()
			
			if lname == "opcode":
				opcode = contents
			elif lname == "syntax":
				if contents in self.SYNTAX_DATA:
					encoding, syntax = self.SYNTAX_DATA[contents]
				else
					syntax = self._parseSyntaxFormat(contents)
		
		if opcode is None or syntax is None or encoding is None:
			raise self.SyntaxException("Missing syntax data.")		
		
		return (encoding, syntax, opcode)
		
	def _initSyntaxData(self):
		self.syntax_data = {}
		
		for attr in dir(self.builder):
			if attr.startswith('ins_'):
				func_name = attr[4:]
				func = getattr(self.builder, attr)
				
				if not func.__doc__:
					raise self.SyntaxException("Missing syntax data for instruction '%s'." % func_name)
					
				self.parsed_syntax_data[func_name] = self._parseSyntaxData(func.__doc__)