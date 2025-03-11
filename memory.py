# -*- coding: utf-8 -*-
from typing import Union
import struct
import roms

# ** Memory
mem = memoryview(bytearray(65536))
mem_rw = [False, True, True, True]


#0xffff +--------+--------+--------+--------+--------+--------+--------+--------+
#       | Bank 0 | Bank 1 | Bank 2 | Bank 3 | Bank 4 | Bank 5 | Bank 6 | Bank 7 |
#       |        |        |(also at|        |        |(also at|        |        |
#       |        |        | 0x8000)|        |        | 0x4000)|        |        |
#       |        |        |        |        |        | screen |        | screen |
#0xc000 +--------+--------+--------+--------+--------+--------+--------+--------+
#       | Bank 2 |        Any one of these pages may be switched in.
#       |        |
#       |        |
#       |        |
#0x8000 +--------+
#       | Bank 5 |
#       |        |
#       |        |
#       | screen |
#0x4000 +--------+--------+
#       | ROM 0  | ROM 1  | Either ROM may be switched in.
#       |        |        |
#       |        |        |
#       |        |        |
#0x0000 +--------+--------+
banks = [0,0,0,0,0,0,0,0,0]
banks[0] = memoryview(bytearray([0] * 16384))
banks[1] = memoryview(bytearray([0] * 16384))
banks[2] = memoryview(bytearray([0] * 16384))
banks[3] = memoryview(bytearray([0] * 16384))
banks[4] = memoryview(bytearray([0] * 16384))
banks[5] = memoryview(bytearray([0] * 16384))
banks[6] = memoryview(bytearray([0] * 16384))
banks[7] = memoryview(bytearray([0] * 16384))

currentbank = 0
currentrom = 0
currentscreen = 0
bankingenabled = 1

# Word access
wstruct = struct.Struct('<H')
# Signed byte access
signedbyte = struct.Struct('<b')


def pokew(addr: int, word):
    global mem

    if addr % 0x4000 == 0x3fff:
        if mem_rw[addr//0x4000]:
            mem[addr] = word % 256
        addr = (addr + 1) % 65536
        if mem_rw[addr//0x4000]:
            mem[addr] = word >> 8
    else:
        if mem_rw[addr//0x4000]:
            wstruct.pack_into(mem, addr, word)


def peekw(addr: int) -> int:
    global mem

    if addr == 65535:
        return (mem[65535] | (mem[0] << 8)) % 65536

    return wstruct.unpack_from(mem, addr)[0]


def pokeb(addr: int, byte):
    try:
        if mem_rw[addr//0x4000]:
            mem[addr] = byte
    except Exception as error:
        print(addr, byte, type(addr), type(byte))
        raise error


def peekb(addr: int) -> int:
    return mem[addr]


def peeksb(addr: int) -> int:
    return signedbyte.unpack_from(mem, addr)[0]



#0xffff +--------+--------+--------+--------+--------+--------+--------+--------+
#       | Bank 0 | Bank 1 | Bank 2 | Bank 3 | Bank 4 | Bank 5 | Bank 6 | Bank 7 |
#       |        |        |(also at|        |        |(also at|        |        |
#       |        |        | 0x8000)|        |        | 0x4000)|        |        |
#       |        |        |        |        |        | screen |        | screen |
#0xc000 +--------+--------+--------+--------+--------+--------+--------+--------+
#       | Bank 2 |        Any one of these pages may be switched in.
#       |        |
#       |        |
#       |        |
#0x8000 +--------+
#       | Bank 5 |
#       |        |
#       |        |
#       | screen |
#0x4000 +--------+--------+
#       | ROM 0  | ROM 1  | Either ROM may be switched in.
#       |        |        |
#       |        |        |
#       |        |        |
#0x0000 +--------+--------+
#
#
#The byte output will be interpreted as follows:
#
#Bits 0-2: RAM page (0-7) to map into memory at 0xc000.
#
#Bit 3: Select normal (0) or shadow (1) screen to be displayed. The normal screen is in bank 5, whilst the shadow screen is in bank 7. Note that this does not affect the memory between 0x4000 and 0x7fff, which is always bank 5.
#
#Bit 4: ROM select. ROM 0 is the 128k editor and menu system; ROM 1 contains 48K BASIC.
#
#Bit 5: If set, memory paging will be disabled and further output to this port will be ignored until the computer is reset.
#
#   5  4  3 2 1 0    
#   32 16 8 4 2 1
#   
    
def memorySwitch (banknum: int):
    global currentrom
    global mem
    global banks
    global currentbank
    global currentscreen
    global bankingenabled

    bank = banknum & 7      #Bits 0-2: RAM page (0-7) to map into memory at 0xc000.

    screen = banknum & 8    #Bit 3: Select normal (0) or shadow (1) screen to be displayed. The normal screen is in bank 5, whilst the shadow screen is in bank 7. Note that this does not affect the memory between 0x4000 and 0x7fff, which is always bank 5.
    if screen == 8:
        screen = 1

    
    rom = banknum & 16      #Bit 4: ROM select. ROM 0 is the 128k editor and menu system; ROM 1 contains 48K BASIC.
    if rom == 16:
        rom = 1


    disable = banknum & 32  #Bit 5: If set, memory paging will be disabled and further output to this port will be ignored until the computer is reset.
    if disable == 32:
        disable = 1


    
    if bankingenabled == 1:
        # Disable
        if disable != 0:
            bankingenabled = 0

        # ROM switch?
        if currentrom != rom:
            switchROM(rom)
            currentrom = rom

        # Screen Switch
        if currentscreen != screen:
            match screen:
                case 0:
                    banks[7][0:] = mem[0x4000:0x4000 + 16384]
                    mem[0x4000:0x4000 + 16384] = banks[5][0:]
                case 1:
                    banks[5][0:] = mem[0x4000:0x4000 + 16384]
                    mem[0x4000:0x4000 + 16384] = banks[7][0:]       
            currentscreen = screen

        # bank switch?
        if currentbank != bank:
            # Put the bank back that is being 'swapped out'
            match currentbank:
                case 2:
                    #print ("2:0x8000")
                    banks[2][0:] = mem[0x8000:0x8000 + 16384]
                case 5:
                    #print ("5:0x4000")
                    banks[5][0:] = mem[0x4000:0x4000 + 16384]
                case _:
                    #print ("out: ", currentbank)
                    banks[currentbank][0:] = mem[0xc000:0xc000 + 16384]
            currentbank = bank

            # copy in bank that is being 'swapped in'
            mem[0xc000:0xc000 + 16384] = banks[bank][0:]


def switchROM ( romnum: int):
    match romnum:
        case 0:
            mem[0:16384] = roms.rom128_0[0:]
        case 1:
            mem[0:16384] = roms.rom128_1[0:]
    


if __name__ == '__main__':
    pokeb(100000, 111)
    print('DONE')
