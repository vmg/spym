class MIPS_Exception(Exception):
	def __init__(self, code, int_id = None, badaddr = None, debug_msg = ''):
		self.code = code
		self.int_id = int_id
		self.badaddr = badaddr
		self.debug_msg = debug_msg

EXCEPTION_HANDLER_ADDR 	= 0x80000080
SYSCALL_HANDLER_ADDR 	= 0x80010000

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
# Define the exception handling code.  This must go first!

	.kdata
__m1_:	.asciiz "  Exception "
__m2_:	.asciiz " occurred and ignored\n"
__e0_:	.asciiz "  [Interrupt] "
__e1_:	.asciiz	"  [TLB]"
__e2_:	.asciiz	"  [TLB]"
__e3_:	.asciiz	"  [TLB]"
__e4_:	.asciiz	"  [Address error in inst/data fetch] "
__e5_:	.asciiz	"  [Address error in store] "
__e6_:	.asciiz	"  [Bad instruction address] "
__e7_:	.asciiz	"  [Bad data address] "
__e8_:	.asciiz	"  [Error in syscall] "
__e9_:	.asciiz	"  [Breakpoint] "
__e10_:	.asciiz	"  [Reserved instruction] "
__e11_:	.asciiz	""
__e12_:	.asciiz	"  [Arithmetic overflow] "
__e13_:	.asciiz	"  [Trap] "
__e14_:	.asciiz	""
__e15_:	.asciiz	"  [Floating point] "
__e16_:	.asciiz	""
__e17_:	.asciiz	""
__e18_:	.asciiz	"  [Coproc 2]"
__e19_:	.asciiz	""
__e20_:	.asciiz	""
__e21_:	.asciiz	""
__e22_:	.asciiz	"  [MDMX]"
__e23_:	.asciiz	"  [Watch]"
__e24_:	.asciiz	"  [Machine check]"
__e25_:	.asciiz	""
__e26_:	.asciiz	""
__e27_:	.asciiz	""
__e28_:	.asciiz	""
__e29_:	.asciiz	""
__e30_:	.asciiz	"  [Cache]"
__e31_:	.asciiz	""
__excp:	.word __e0_, __e1_, __e2_, __e3_, __e4_, __e5_, __e6_, __e7_, __e8_, __e9_
	.word __e10_, __e11_, __e12_, __e13_, __e14_, __e15_, __e16_, __e17_, __e18_,
	.word __e19_, __e20_, __e21_, __e22_, __e23_, __e24_, __e25_, __e26_, __e27_,
	.word __e28_, __e29_, __e30_, __e31_
s1:	.word 0
s2:	.word 0

# This is the exception handler code that the processor runs when
# an exception occurs. It only prints some information about the
# exception, but can server as a model of how to write a handler.
#
# Because we are running in the kernel, we can use $k0/$k1 without
# saving their old values.

	.ktext %(exception_handler_address)08X

	.set noat
	move $k1 $at		# Save $at
	.set at
	sw $v0 s1		# Not re-entrant and we can't trust $sp
	sw $a0 s2		# But we need to use these registers

	mfc0 $k0 $13		# Cause register
	srl $t0 $k0 2		# Extract ExcCode Field
	andi $t0 $t0 0x1f
	
	beq $t0, 0x8, %(syscall_jump_label)s # if code is 0x8, handle the syscall

	# Print information about exception.
	#
	li $v0 4		# syscall 4 (print_str)
	la $a0 __m1_
	syscall

	li $v0 1		# syscall 1 (print_int)
	srl $a0 $k0 2		# Extract ExcCode Field
	andi $a0 $a0 0x1f
	syscall

	li $v0 4		# syscall 4 (print_str)
	andi $a0 $k0 0x3c
	lw $a0 __excp($a0)
	nop
	syscall

	bne $k0 0x18 ok_pc	# Bad PC exception requires special checks
	nop

	mfc0 $a0 $14		# EPC
	andi $a0 $a0 0x3	# Is EPC word-aligned?
	beq $a0 0 ok_pc
	nop

	li $v0 10		# Exit on really bad PC
	syscall

ok_pc:
	li $v0 4		# syscall 4 (print_str)
	la $a0 __m2_
	syscall

	srl $a0 $k0 2		# Extract ExcCode Field
	andi $a0 $a0 0x1f
	bne $a0 0 ret		# 0 means exception was an interrupt
	nop

# Interrupt-specific code goes here!
# Don't skip instruction at EPC since it has not executed.

ret:
# Return from (non-interrupt) exception. Skip offending instruction
# at EPC to avoid infinite loop.
#
	lw $v0 s1		# Restore other registers
	lw $a0 s2

ret_fromsyscall:
	mfc0 $k0 $14		# Bump EPC register
	addiu $k0 $k0 4		# Skip faulting instruction
				# (Need to handle delayed branch case here)
	mtc0 $k0 $14

# Restore registers and reset procesor state

	.set noat
	move $at $k1		# Restore $at
	.set at

	mtc0 $0 $13		# Clear Cause register

	mfc0 $k0 $12		# Set Status register
	ori  $k0 0x1		# Interrupts enabled
	mtc0 $k0 $12

# Return sequence for MIPS-I (R2000):
	rfe
	jr $k0	 
	nop

# Standard startup code.  Invoke the routine "main" with arguments:
#	main(argc, argv, envp)
#
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

def getKernelText(exception_handler = True, syscall_handler = True, memmap_screen = 0x0, memmap_keyboard = 0x0):
	kernel_text = ""
	
	if exception_handler:
		kernel_text += EXCEPTION_HANDLER % {
			'exception_handler_address' : EXCEPTION_HANDLER_ADDR,
			'syscall_handler_address' : SYSCALL_HANDLER_ADDR,
			'syscall_jump_label' : 'syscall_handler' if syscall_handler else 'ret'
		}

	if syscall_handler:
		kernel_text += SYSCALL_HANDLER % {
			'syscall_handler_address' : SYSCALL_HANDLER_ADDR,
			'memmap_io_SCREEN' : memmap_screen, 
			'memmap_io_KEYBOARD' : memmap_keyboard
		}
		
	return kernel_text