#TOOL to call functions from memory to interject into Freecell.exe
import pymem
import pymem.memory
import pymem.process
import struct

#pm = pymem.Pymem('freecell.exe') variable for the actively used memory from freecell

#1004210 handles the type of card location coordinates
#1003CF0- handles the drawing 
def shell_code_create(hdc, a2, a3, a4, a5):
    in_a2 = a2
    in_a3 = a3
    in_a4 = a4
    in_a5 = a5
    
    shellcode = b''
    
    shellcode += b'\x68' + struct.pack('<I', in_a5)
    shellcode += b'\x68' + struct.pack('<I', in_a4)
    shellcode += b'\x68' + struct.pack('<I', in_a3)
    shellcode += b'\x68' + struct.pack('<I', in_a2)
    shellcode += b'\x68' + struct.pack('<I', hdc)
    
    shellcode += b'\xE8\x00\x00\x00\x00'  # placeholder
    
    #ret
    shellcode += b'\xC3'
    return shellcode

def Inject_shell_code(pm, a2,a3):
    
  #determining your computer setup you'll need to change the application path
    #pm= pymem.Pymem(r"C:\Users\ludlo\Downloads\Group Project_T2\Group Project_T2\freecell.exe.i64")
   
    #determine a5
    #accessing active dword_100844C value 
    address = 0x0100844C
    bytes = pm.read_bytes(address, 4)
    dword_100844C = struct.unpack('i', bytes)[0] 
    ##accessing active dword_100844C value 
    address = 0x01008DB0
    bytes = pm.read_bytes(address, 4)
    dword_1008DB0 = struct.unpack('i', bytes)[0] 
    #accessing active dword_100814C
    address = 0x0100814C
    bytes = pm.read_bytes(address, 4); 
    dword_100814C = struct.unpack('i',bytes)[0]
        
    #Paint.hdc
    address = 0x0019FDF0
    bytes = pm.read_bytes(address,4)
    Paint_hdc  = struct.unpack('<I', bytes)[0]
    #Movement inputs ideally a2,a3  
    """
    print("Enter a2 value: ")
    a2 = input()
    print("Enter a3 value: ")
    a3 = input()
    """
    #determine a4
    address = 0x01008AB0
    bytes = pm.read_byte(address, ((21*a2)+a3)  * 4)
    a4 = struct.unpack('i', bytes)[0]

    #checks to determine a5
    if(dword_100844C == 1 and a3 == dword_1008DB0 and  a2 == dword_100814C):
        a5 = 2;
    else:
        a5 = 0; 

    inject_shell = shell_code_create(Paint_hdc, a2, a3, a4, a5)
    inject_sz = len(inject_shell)

    alloc_address = pymem.memory.allocate_memory(pm.process_handle, inject_sz);

    if(alloc_address and inject_shell):
       pm.write_bytes(alloc_address, inject_shell, inject_sz)
    else:
       print("Injection failed")
        

def hex_dump_fo_cards(data, address):
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_bytes = ' '.join(f"{b:02X}" for b in chunk)
    return hex_bytes
    
def identify_message_box(pm):
    if(pm.read_bytes(0x0019F6D4, 2) == 0x88):
        pm.write_bytes(0x0019F6D4,b"\xC3",1)
        return
    else:
        #nothing
        return
    
    