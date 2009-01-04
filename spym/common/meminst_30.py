class MemoryInstruction(int):
  def __init__(self, number):
    self._vm_asm = None
    self.text = ''
    self.orig_text = ''
    self._delay = False