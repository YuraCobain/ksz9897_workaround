#!/usr/bin/python3

import subprocess
import argparse
from collections import deque

KSZ9897_BUS=0
KSZ9897_ADDR=0x5f
KSZ9897_16B_LEN=2

i2cset_cmd = 'i2ctransfer -y 0 w{}@0x5f {}' 
i2cget_cmd = 'i2ctransfer -y 0 r{}@0x5f ' 

GLOBAL_REG_16B_DATA = 0xff
GLOBAL_REG_8B_DATA = 0xfe
MMD_1 = 0x01
MMD_7 = 0x07
MMD_1C = 0x1c

MODE = 'apply'

ksz_workaround = {
    'module_1_workaround' : 
    {
        MMD_1 : [(0x6f, 0xdd0b), (0x8f, 0x6032), (0x9d, 0x248c), (0x75, 0x0060), (0xd3, 0x7777)],
        MMD_1C : [(0x06, 0x3008), (0x08, 0x2001)]
    },
    'module_2_workaround' : 
    {
        MMD_1C : [(0x04, 0x00d0)]    
    },
    'module_3_workaround' :
    {
        MMD_7 : [(0x3c, 0x0000)]    
    },

    'module_7_workaround' :
    {
        MMD_1C : [(0x13, 0x6eff), (0x14, 0xe6ff), (0x15, 0x6eff), (0x16, 0xe6ff), (0x17, 0x00ff),
                  (0x18, 0x43ff), (0x19, 0xc3ff), (0x1a, 0x6fff), (0x1b, 0x07FF), (0x1c, 0x0fff),
                  (0x1d, 0xe7ff), (0x1e, 0xefff), (0x20, 0xeeee)]    
    },
    'module_10_workaround' : 
    {
        GLOBAL_REG_16B_DATA : [(0x03c0, 0x4090), (0x3c2, 0x0080), (0x03c4, 0x2000)]
    },
    'module_11_workaround' : 
    {
        GLOBAL_REG_8B_DATA : [(0x0331, 0xd0)]
    }
}

def eval_map(f, iterable):
    deque(map(f, iterable), maxlen=0)

def into_bytes(word):
    return divmod(word, 0x100)

def into_byte_str(word_arr):
    bstr = ''
    blen = 0
    for w in word_arr:
        barr = w.to_bytes(2, byteorder='big')
        bstr = bstr + ''.join( [ "0x%02x " % ord( b ) for b in barr.decode('latin1') ] )
        blen = blen + 2
    return bstr, blen

# transfer 16bit register and 8bit register value
def set_generic_reg_w_b(reg, val):
    bstr, blen = into_byte_str([reg])
    bstr = bstr + hex(val)
    blen = blen + 1

    cmd = i2cset_cmd.format(blen, bstr)

    print('set reg val: {}'.format(cmd))
    ret = subprocess.call(cmd, shell=True) 
    print('returned value:', ret)
    
# transfer 16bit register and 16bit register value
def set_generic_reg_w_w(reg, val):
    bstr, blen = into_byte_str([reg, val])

    cmd = i2cset_cmd.format(blen, bstr)

    print('set reg val: {}'.format(cmd))
    ret = subprocess.call(cmd, shell=True) 
    print('returned value:', ret)
    
# read 16bit register value
def get_generic_reg_w():
    cmd = i2cget_cmd.format(KSZ9897_16B_LEN)
    print('get reg val: {}'.format(cmd))
    ret = subprocess.check_output(cmd, shell=True) 
    print('returned value:', ret.decode("latin1"))

    return ret.decode("latin1")

WORKAROUND_KEY_IDX = 0
WORKAROUND_VAL_IDX = 1
def get_workaround_key_val(workaround):
    key = workaround[WORKAROUND_KEY_IDX]
    val = workaround[WORKAROUND_VAL_IDX]

    return key, val
 
class ksz_port:
    _port_reg_mmd_select = 0x011a
    _port_reg_mmd_write = 0x011c
    _mmd_dev_reg = 0x0000
    _mmd_dev_val = 0x4000
    
    def __init__(self, port, mmd):
        self._port_reg_mmd_select = self._port_reg_mmd_select | ( port << 12 )
        self._port_reg_mmd_write = self._port_reg_mmd_write | ( port << 12 )
        self._mmd_dev_reg = self._mmd_dev_reg | mmd
        self._mmd_dev_val = self._mmd_dev_val | mmd

    def __select_reg(self, reg):
        # select desire register on mmd 

        # 1 - indirect select register address on mmd dev
        set_generic_reg_w_w(self._port_reg_mmd_select, self._mmd_dev_reg)
        set_generic_reg_w_w(self._port_reg_mmd_write, reg)

        # 2 - indirect select register value on mmd dev
        set_generic_reg_w_w(self._port_reg_mmd_select, self._mmd_dev_val)

    def set_reg(self, reg, val):
        self.__select_reg(reg)
        # set desire value on selected register
        set_generic_reg_w_w(self._port_reg_mmd_write, val)

    def set_reg(self, reg_val_pair):
        self.__select_reg(reg_val_pair[0])
        # set desire value on selected register
        set_generic_reg_w_w(self._port_reg_mmd_write, reg_val_pair[1])

def apply_mmd_workaround(mmd, workaround):
    for p in range(1,6):
        print("applying fixup for mmd {} on port {}".format(mmd, p))
        port_dev = ksz_port(p, mmd)
        eval_map(port_dev.set_reg, workaround)
   
def get_register_setter(data_width):
    if data_width == GLOBAL_REG_16B_DATA:
        return set_generic_reg_w_w
    elif data_width == GLOBAL_REG_8B_DATA:
        return set_generic_reg_w_b

    return lambda x,y: None 

def apply_global_reg_work_around(data_width, workaround):
    print("apply fixup on global reg: {} width mode {}".format(workaround, data_width))
    setter = get_register_setter(data_width)
    eval_map(lambda item: setter(item[0], item[1]), workaround)

def get_handler(htype):
    if htype >= GLOBAL_REG_8B_DATA:
       return lambda fixup: apply_global_reg_work_around(htype, fixup)
    else:
       return lambda fixup: apply_mmd_workaround(htype, fixup)

def apply_workaround(workaround):
    # get fixup type(mmd or global) and fixup settings itself
    htype, fixup = get_workaround_key_val(workaround)

    #execute specific handler
    get_handler(htype)(fixup)
    
def apply_module_workaround(module):
    module_name, module_workarounds = get_workaround_key_val(module)

    print("applying {}".format(module_name))
    eval_map(apply_workaround, module_workarounds.items()) 

def parse_args():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-a', '--apply', dest = 'apply', action = 'store_true', help = 'apply workaround immediately')
    group.add_argument('-g', '--generate', dest = 'generate', action = 'store_true', help = 'generate bash script to apply workarounds')
  
    return vars(parser.parse_args())

def run_fixer():
    global MODE
    args = parse_args()
    
    if args['apply'] == True:
        MODE = 'apply'
    elif args['generate'] == True:
        MODE = 'generate'
    
    eval_map(apply_module_workaround, ksz_workaround.items())
        

if __name__ == '__main__':
    run_fixer()
