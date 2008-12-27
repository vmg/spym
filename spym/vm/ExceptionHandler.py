

EXCEPTION_HANDLER_ADDR = 0x80000080

EXCEPTION_HANDLER = \
"""
	# Standard startup code.  Invoke the routine "main" with arguments:
	#	main(argc, argv, envp)
	#
		.text
		.globl __start
	__start:
		lw $a0, 0($sp)		# argc
		addiu $a1, $sp, 4		# argv
		addiu $a2, $a1, 4		# envp
		sll $v0, $a0, 2
		addu $a2, $a2, $v0
		jal main
		nop

		li $v0, 10
		syscall			# syscall 10 (exit)

		.globl __eoth
	__eoth:
"""
