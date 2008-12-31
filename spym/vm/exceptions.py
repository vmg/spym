from spym.common.utils import _debug

class MIPS_Exception(Exception):
	def __init__(self, code, int_id = None, badaddr = None, debug_msg = ''):
		self.code = code
		self.int_id = int_id
		self.badaddr = badaddr
		self.debug_msg = debug_msg
		
		Exception.__init__(self, debug_msg)

EXCEPTION_HANDLER_ADDR 	= 0x80000080
SYSCALL_HANDLER_ADDR 	= 0x80001000
INTERRUPT_HANDLER_ADDR	= 0x80002000

SYSCALL_HANDLER = \
r"""
	.kdata
	
__syscall_int_data:
	.space 16							# 16 bytes for printing numbers
	
__syscall_ra_store:
	.word 0

	.ktext %(syscall_handler_address)08X
	
syscall_handler:
	sw $ra, __syscall_ra_store			# store RA, to return to the exception handler
	
	beq $v0, 0x1, syscall_print_int		# is print_int?
	beq $v0, 0x4, syscall_print_string	# is print_string?
	beq $v0, 0x5, syscall_read_int		# is read_int?
	beq $v0, 0x8, syscall_read_string
	j __sys_return						# ...we can't handle it yet otherwise
	
###################################################
### PRINT_INT (syscall code 1) PROCEDURE		###
###################################################
syscall_print_int:
	move $t1, $a0						# we are working on $t1 all the time, number to print is there
	bne $t1, $zero, __sys_int_nonzero	# if the number is not zero, then we need to to 'the long thing'
	 
	li $a0, '0'							# if the number is zero, just load the char for zero
	jal __sys_io_putchar				# ...and print it
	j __sys_return						# done.

__sys_int_nonzero:
	srl $t2, $t1, 31					# get the sign of the number in $t2
	beq $t2, $zero, __sys_int_positive	# if sign is zero, the number is positive, we can skip this
	
	li $a0, '-'							# otherwise, we have to print the negative sign. push it
	jal __sys_io_putchar				# and send it to memory
	neg $t1, $t1						# and continue working with the inverse of the number
	
__sys_int_positive:
	li $t2, 10							# load a 10 in $t2, we need it for mod operations
	li $t3, '0'							# we also need the 0 char to get other printable chars from it
	
	la $t4, __syscall_int_data			# load the address were we store numbers in reverse order
	addi $t4, 15						# move to the end of the char array, leave 1 char as NULL as string delimiter
	
__sys_int_mainloop:
	div $t1, $t2						# divide the number by 10
	mfhi $t5							# get the MOD10, i.e. the last decimal digit
	add $t5, $t5, $t3					# add the '0' char to get a char representation

	addi $t4, $t4, -1					# move back in the array one position
	sb $t5, 0($t4)						# store the char at the end of the number string

	mflo $t1							# get the actual division in $t1 to continue working on it
	bne $t1, $zero, __sys_int_mainloop	# if the div is 0, we are done, otherwise keep looping
		
	move $a0, $t4						# we now have a number string in $t5, move it to $a0
	j syscall_print_string 				# and print it like a normal string.


###################################################
### PRINT_STRING (syscall code 4) PROCEDURE		###
###################################################
syscall_print_string:
	move $t1, $a0						# work with $t1, not $a0... we need $a0 for proc calls
	
__sys_string_mainloop:
	lb $a0, 0($t1)						# load the next char to print (put in $a0 so it's ready for PUTCHAR)
	beq $a0, $zero, __sys_return		# if the char is NULL, we are done.
	
	jal __sys_io_putchar				# we are ready to print the char, do it...
	addi $t1, $t1, 1					# increment byte pointer
	j __sys_string_mainloop				# ..and go back to the start
	
###################################################
### READ_INT (syscall code 5) PROCEDURE			###
###################################################
syscall_read_int:
	li $t1, 0							# we are going to build up the number in $0
	li $t4, '0'							# used to build up characters
	li $t5, '9'							# used for range checking
	li $t6, 0							# sign of the number
	li $t7, 10							# load the value of 'newline' -- note: this is also used for multiplication

	jal __sys_io_getchar
	bne $v0, '-', __sys_intread_in_loop
	li $t6, 1
	
__sys_intread_loop:
	jal __sys_io_getchar

__sys_intread_in_loop:
	blt	$v0, $t4, __sys_intread_finish	# if CHAR is less than '0'... branch
	bgt $v0, $t5, __sys_intread_finish	# or CHAR is greater than '9' ... branch
	sub $v0, $v0, $t4					# char - '0' to turn into a number
	
	mult $t1, $t7						# multiply by 10
	mflo $t1
	add $t1, $t1, $v0					# add it to the current character
	j __sys_intread_loop
	
__sys_intread_finish:
	move $v0, $t1						# get the result INT in $v0 already
	beq $t6, $zero, __sys_return		# if the stored sign is 0, we are done
	
	neg $v0, $v0						# otherwise get the negative of the number
	j __sys_return

###################################################
### READ_STRING (syscall code 8) PROCEDURE		###
###################################################
syscall_read_string:
	move $t1, $a0						# $t0 now contains the pointer to the bffer
	move $t2, $a1						# $t1 now contains the buffer len
	li $t6, 10							# load up '\n' as a constant for comparision
	
	addi $t2, $t2, -1					# len - 1 to save up for terminating byte
	
__sys_stread_loop:
	jal __sys_io_getchar				# get new char in $v0
	beq $v0, $t6, __sys_stread_finish	# if the char is ENDLINE, finish
	sb $v0, 0($t1)						# store the char in our buffer
	
	addi $t1, $t1, 1					# increase buffer pointer
	addi $t2, $t2, -1					# decrease len counter
	
	bne $t2, $zero, __sys_stread_loop	# if buffer is zero, we cant't take more chars
	
__sys_stread_finish:
	sb $zero, 0($1)						# store NULL as terminating char
	j __sys_return						# done!

###################################################
### MEMORY MAPPED IO PROCEDURES					###
###################################################

# PUTCHAR($a0): Prints the given char on screen
# PARAMS: $a0 is the hex code of the char to print
__sys_io_putchar:
	li $t9, 0x%(memmap_io_SCREEN)08X		# load the address for the memory mapped screen
	
__sys_io_putchar_wait:
	lb 	$t3, 0($t9)						# load the Keyboard CONTROL (+0) register
	andi $t3, $t3, 0x1					# check for ready
	beq $t3, $zero, __sys_io_putchar_wait	# while not ready, keep trying
	
	sb 	$a0, 4($t9)						# put the character in Keyboard DATA (+4) register
	jr $ra
	
# GETCHAR() - $v0: Gets a character from the mapped keyboard
# RETURNS: read character in $v0
__sys_io_getchar:
	li $t9, 0x%(memmap_io_KEYBOARD)08X		# load address for keyboard
	
__sys_io_getchar_wait:
	lb $t3, 0($t9)							# poll the CONTROL register
	andi $t3, $t3, 0x1						# ...wait until ready...
	beq $t3, $zero, __sys_io_getchar_wait
	
	lbu $v0, 4($t9)							# load keypress from DATA register
	jr $ra									# return to function

__sys_return:
	lw $ra, __syscall_ra_store
	j ret_fromsyscall
"""

EXCEPTION_HANDLER = \
r"""
	.kdata
__register_storage:
	.space 192 # enough space for 3 reentrancy levels. COOL.

__exception_reentrant_ptr: 
	.word __register_storage

__interrupt_handlers_array:
	%(int_handler_addresses)s

	.ktext %(exception_handler_address)08X
###################################################
### CORE EXCEPTION HANDLER						###
###################################################
	la $k0, __exception_reentrant_ptr
	lw $k1, 0($k0)		# load the current reentrancy pointer

	# save all the important registers
	# Save parameter registers, and temporaries for
	# operations, and the RA so we can JAL
	#	0	4	8	12	16	20	24	28	32	36	40	44
	#	at	v0	a0	t0	t1	t2	t3	t4	t5	t6	t7	ra
	.set noat
	sw $at, 0($k1)		# Save $at
	.set at
	sw $v0, 4($k1)
	sw $a0, 8($k1)
	sw $t0, 12($k1)
	sw $t1, 16($k1)
	sw $t2, 20($k1)
	sw $t3, 24($k1)
	sw $t4, 28($k1)
	sw $t5, 32($k1)
	sw $t6, 36($k1)
	sw $t7, 40($k1)
	
	sw $sp, 44($k1)
	sw $fp,	48($k1)
	sw $ra,	52($k1)
	
	mfc0 $k0, $14
	sw $k0, 56($k1)
	
	mfc0 $k0, $8
	sw $k0, 60($k1)
	
	# increase reentrancy
	addi $k0, $k1, 64		# increase the reentrancy pointer by 64 to point to the next storage zone
	sw $k0, __exception_reentrant_ptr
	
	mfc0 $k0 $13		# Cause register
	srl $k0 $k0 2		# Extract ExcCode Field
	andi $k0 $k0 0x1f
	
	beq $k0, 0x8, %(syscall_jump_label)s # if code is 0x8, handle the syscall
	beq $k0, $0, interrupt_switcher	# if code is 0x0, handle the interrupt
#	j ret_fromexception
	
unhandled_exception:
# TODO: handle other exceptions; otherwise we just crash the VM
	li $v0, 17	# exit2 syscall
	move $a0, $k0 # exit with exception code as error code
	syscall


###################################################
### INTERRUPT SELECTION CODE					###
###################################################
interrupt_switcher:
	mfc0 $k0, $13	# load cause register
	srl $k0, $k0, 8	# move to lowest bit the start of PENDING INSTRUCTIONS
	li $t1, 0		# inst counter
	
__intswitch_loop:
	andi $t2, $k0, 0x1
	bne  $t2, $zero, __intswitch_found
	
	srl $k0, $k0, 1
	addi $t1, $t1, 1
	j __intswitch_loop
	
__intswitch_found:
	# $1 now contains the interrupt id (0-7)
	sll $t1, $t1, 2		# multiply by 4 to get the offset on the array
	la $k0, __interrupt_handlers_array # get the start of the array
	add $k0, $k0, $t1	# add the offset to the start address, store in $k0
	
	lw $k0, 0($k0) # get the word in the array with our jump address
	
	beq $k0, $0, ret_frominterrupt # if interrupt address is 0, skip handling
	jalr $k0			# jump to the handler code and link


###################################################
### EXCEPTION HANDLER CLEANUP/RESTORE			###
###################################################
# if we return from interrupt, we do not want to bump EPC, instruction hasn't been executed yet
ret_fromexception:
ret_frominterrupt:
	la $k0, __exception_reentrant_ptr
	lw $k1, 0($k0)		# load the current reentrancy pointer
	addi $k1, $k1, -64
	
	lw $v0 4($k1)		# Restore parameter registers
	lw $a0 8($k1)
	
	lw $k0, 56($k1)	# restore EPC even if we don't bump it!!
	mtc0 $k0 $14
	
	j ret_restoreall

# if we return from syscall, we don't need to restore $a0 and $v0 (those are interrupt params)
# we do need to skip the instruction
ret_fromsyscall:
	la $k0, __exception_reentrant_ptr
	lw $k1, 0($k0)		# load the current reentrancy pointer
	addi $k1, $k1, -64 # set to current
	
	lw $k0, 56($k1)	# restore EPC before bumping it!
	addiu $k0 $k0 4		# Skip faulting instruction
	mtc0 $k0 $14
	
ret_restoreall:
	lw $t0, 12($k1)
	lw $t1, 16($k1)
	lw $t2, 20($k1)
	lw $t3, 24($k1)
	lw $t4, 28($k1)
	lw $t5, 32($k1)
	lw $t6, 36($k1)
	lw $t7, 40($k1)
	
	lw $sp, 44($k1)
	lw $fp,	48($k1)
	lw $ra,	52($k1)

	lw $k0, 60($k1) # restore BadVAddr
	mtc0 $k0, $8

	mtc0 $0 $13		# Clear Cause register

	# since we are done with this exception,
	# the pointer may now point to the space
	# we were using... basically decreasing
	# the active pointer by 64
	sw $k1, __exception_reentrant_ptr # save the exception reentrancy pointer

	.set noat
	lw $at, 0($k1)		# Restore $at
	.set at				# WARNING: Do not use pseudoinsts until you quit the handler
	
	mfc0 $k0, $14		# take out the EPC, it should be restored by now
	
# Return sequence for MIPS-I (R2000):
	rfe				# leave excpetion handler, bits are shifted back and such
	jr $k0	 		# bang, jump back into code
	nop				# Note that this is hacked so RFE hits on a main instruction
					# and the JR hits on the delay slot (I'm hoping this works)
					# like this on a normal processor.

# Standard startup code.  Invoke the routine "main" with arguments:
#	main(argc, argv, envp)
	.text
	.globl __start
__start:
	lw $a0 0($sp)		# argc
	addiu $a1 $sp 4		# argv
	addiu $a2 $a1 4		# envp
	sll $v0 $a0 2
	addu $a2 $a2 $v0
	jal main
	nop

	li $v0 10
	syscall			# syscall 10 (exit)

	.globl __eoth
__eoth:
"""

def parseInterruptHandlers(handler_list):
	handler_text = \
	r"""
		.ktext %(int_handler_start)08X	
	""" % {'int_handler_start' : INTERRUPT_HANDLER_ADDR}
	
	label_names = ["0x0", ] * 8
	for (int_id, htext, hlabel) in handler_list:		
		if hlabel not in htext:
			htext = hlabel + ':\n\n' + htext

		label_names[int_id + 2] = hlabel
		handler_text += htext
	
	int_handler_addresses = ".word " + ", ".join(label_names)
	return handler_text, int_handler_addresses

def getKernelText(exception_handler = True, syscall_handler = True, interrupt_handlers = [], memmap_screen = 0x0, memmap_keyboard = 0x0):
	kernel_text = ""
	int_handler_addresses = ""
	
	if interrupt_handlers:
		handler_text, int_handler_addresses = parseInterruptHandlers(interrupt_handlers)
		kernel_text += handler_text
	
	if exception_handler:
		kernel_text += EXCEPTION_HANDLER % {
			'exception_handler_address' : EXCEPTION_HANDLER_ADDR,
			'syscall_handler_address' : SYSCALL_HANDLER_ADDR,
			'syscall_jump_label' : 'syscall_handler' if syscall_handler else 'unhandled_exception',
			'int_handler_addresses' : int_handler_addresses,
		}

	if syscall_handler:
		kernel_text += SYSCALL_HANDLER % {
			'syscall_handler_address' : SYSCALL_HANDLER_ADDR,
			'memmap_io_SCREEN' : memmap_screen, 
			'memmap_io_KEYBOARD' : memmap_keyboard
		}
		
	return kernel_text