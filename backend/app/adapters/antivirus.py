import os
import socket
import struct

def scan(raw:bytes)->None:
    host=os.environ.get('CLAMAV_HOST')
    if not host: raise RuntimeError('ClamAV is not configured')
    with socket.create_connection((host,int(os.environ.get('CLAMAV_PORT','3310'))),timeout=10) as sock:
        sock.settimeout(30)
        sock.sendall(b'zINSTREAM\0')
        for offset in range(0,len(raw),65536):
            chunk=raw[offset:offset+65536]
            sock.sendall(struct.pack('!I',len(chunk))+chunk)
        sock.sendall(b'\0\0\0\0')
        response=b''
        while b'\0' not in response and len(response)<4096:
            chunk=sock.recv(4096)
            if not chunk: break
            response+=chunk
    response=response.rstrip(b'\0\n')
    if response==b'stream: OK': return
    if response.endswith(b' FOUND'): raise ValueError('MALWARE_DETECTED')
    raise RuntimeError('Antivirus could not verify the object')
