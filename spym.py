#!/usr/bin/python

import os, sys
import spym

from optparse import OptionParser


if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option("-b",
            "--break",
            action = 'append',
            type = 'int',
            dest = 'breakpoints',
            default = [],
            help = "Specify a breakpoint to stop execution at.")

    parser.add_option("-p",
            "--pseudoinsts",
            action = 'store_true',
            dest = 'enable_pseudoinsts',
            default = True,
            help = "Enable pseudoinstructions")

    parser.add_option("-P",
            "--no-pseudoinsts",
            action = 'store_false',
            dest = 'enable_pseudoinsts',
            help = "Enable pseudoinstructions")

    parser.add_option("-v",
            "--verbose",
            action = 'store_true',
            dest = 'verbose',
            default = False,
            help = "Print information for each executed instruction.")
    
    parser.add_option("-e",
            "--exceptions",
            action = 'store_true',
            dest = 'exceptions',
            default = True,
            help = "Load full exception handler.")

    parser.add_option("-E",
            "--no-exceptions",
            action = 'store_false',
            dest = 'exceptions',
            help = "Do not load the custom exception handler.")

    parser.add_option("-i",
            "--mapped-io",
            action = 'store_true',
            dest = 'mapped_io',
            default = True,
            help = "Enabled memory mapped I/O devices.")

    parser.add_option("-I",
            "--no-mapped-io",
            action = 'store_false',
            dest = 'mapped_io',
            help = "Disabled memory mapped I/O devices.")

    parser.add_option("-d",
            "--delay-slots",
            action = 'store_true',
            dest = 'delay_slots',
            default = True,
            help = "Enable delay slots on branch/load instructions.")
    
    parser.add_option("-D",
            "--no-delay-slots",
            action = 'store_false',
            dest = 'delay_slots',
            help = "Disable delay slots on branch/load instructions.")

    parser.add_option("-m",
            "--mem-block-size",
            action = 'store',
            dest = 'block_size',
            type = 'int',
            default = '32',
            help = "Sets the memory block size in bytes.")

    parser.add_option("-c",
            "--cache",
            action = 'store_true',
            dest = 'enable_cache',
            default = True,
            help = "Enable the standard MIPS R2000 Cache")

    parser.add_option("-C",
            "--no-cache",
            action = 'store_false',
            dest = 'enable_cache',
            help = "Disable the standard MIPS R2000 Cache")

    (opts, args) = parser.parse_args(sys.argv[1:])

    vm = spym.VirtualMachine(
            enableDevices = opts.mapped_io,
            enableExceptions = opts.exceptions,
            enablePseudoInsts = opts.enable_pseudoinsts,
            verboseSteps = opts.verbose,
            debugPoints = opts.breakpoints,
            enableDelaySlot = opts.delay_slots,
            enableCache = opts.enable_cache)

    if not args:
        assembly = sys.stdin.read()
        vm.load(assembly, True)
    else:
        for asm in args:
            vm.load(asm, False)

    vm.run()

