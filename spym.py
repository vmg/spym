#!/usr/bin/python

import os, sys
import spym

from optparse import OptionParser


if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option("-b", "--break", action = 'append', type = 'int', dest = 'breakpoints', default = [],
            help = "Specify a breakpoint to stop execution at.")

    parser.add_option("-p", "--pseudoinsts", action = 'store_true', dest = 'enable_pseudoinsts', default = True,
            help = "Enable pseudoinstructions")

    parser.add_option("-P", "--no-pseudoinsts", action = 'store_false', dest = 'enable_pseudoinsts',
            help = "Enable pseudoinstructions")

    parser.add_option("-v", "--verbose", action = 'store_true', dest = 'verbose', default = False,
            help = "Print information for each executed instruction.")
    
    parser.add_option("-e", "--exceptions", action = 'store_true', dest = 'exceptions', default = True,
            help = "Load full exception handler.")

    parser.add_option("-E", "--no-exceptions", action = 'store_false', dest = 'exceptions',
            help = "Do not load the custom exception handler.")

    parser.add_option("-i", "--mapped-io", action = 'store_true', dest = 'mapped_io', default = True,
            help = "Enabled memory mapped I/O.")

    parser.add_option("-I", "--no-mapped-io", action = 'store_false', dest = 'mapped_io',
            help = "Disabled memory mapped I/O.")

    (opts, args) = parser.parse_args(sys.argv[1:])

    if not args:
        assembly = sys.stdin.read()
        loadAsBuffer = True
    else:
        assembly = args
        loadAsBuffer = False

    vm = spym.VirtualMachine(assembly,
            loadAsBuffer = loadAsBuffer,
            defaultMemoryMappedIO = opts.mapped_io,
            enableExceptions = opts.exceptions,
            virtualSyscalls = not opts.mapped_io,
            enablePseudoInsts = opts.enable_pseudoinsts,
            verboseSteps = opts.verbose,
            debugPoints = opts.breakpoints)

    vm.run()

