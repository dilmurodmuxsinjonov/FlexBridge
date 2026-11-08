"""Strict PDF parsing in a killable, resource-limited production child process."""
import io
import multiprocessing
import os
from pypdf import PdfReader, overwrite_configuration
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject, StreamObject
from app.core.config import FORBIDDEN_PDF_TOKENS

MAX_STREAM=20*1024*1024

def inspect_pdf(raw):
    if len(raw)>MAX_STREAM or not raw.startswith(b'%PDF-'): raise ValueError('INVALID_PDF')
    overwrite_configuration(disable_legacy_handling=True,zlib_maximum_output_length=MAX_STREAM,
        lzw_maximum_output_length=MAX_STREAM,run_length_maximum_output_length=MAX_STREAM,
        array_based_stream_maximum_output_length=MAX_STREAM,maximum_declared_stream_length=MAX_STREAM,
        jbig2_maximum_output_length=MAX_STREAM,brotli_maximum_output_length=MAX_STREAM,
        dictionary_maximum_element_count=5000,array_maximum_element_count=5000)
    reader=PdfReader(io.BytesIO(raw),strict=True)
    if reader.is_encrypted: raise ValueError('ENCRYPTED_PDF_NOT_ALLOWED')
    if len(reader.pages)>50: raise ValueError('PDF_PAGE_LIMIT')
    visited=set(); nodes=0; streams=0
    def visit(obj,depth=0):
        nonlocal nodes,streams
        if depth>100: raise ValueError('PDF_DEPTH_LIMIT')
        if isinstance(obj,IndirectObject):
            identity=(obj.idnum,obj.generation)
            if identity in visited: return
            visited.add(identity); obj=obj.get_object()
        nodes+=1
        if nodes>5000: raise ValueError('PDF_OBJECT_LIMIT')
        if isinstance(obj,NameObject) and str(obj) in FORBIDDEN_PDF_TOKENS: raise ValueError('PDF_ACTIVE_CONTENT')
        if isinstance(obj,StreamObject):
            streams+=len(obj.get_data())
            if streams>MAX_STREAM: raise ValueError('PDF_STREAM_LIMIT')
        if isinstance(obj,DictionaryObject):
            for k,v in obj.items(): visit(k,depth+1);visit(v,depth+1)
        elif isinstance(obj,ArrayObject):
            for v in obj: visit(v,depth+1)
    for generation,objects in reader.xref.items():
        for number in objects:
            if number and generation!=65535: visit(IndirectObject(number,generation,reader))
    for number in reader.xref_objStm: visit(IndirectObject(number,0,reader))
    return {'pages':len(reader.pages),'objects':nodes,'uncompressed_bytes':streams}

def _child(raw,pipe):
    try:
        if os.name=='posix':
            import resource
            resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
            resource.setrlimit(resource.RLIMIT_CPU,(20,20))
        elif os.environ.get('FLEXBRIDGE_ENV')=='production':
            raise RuntimeError('Production PDF sandbox requires Linux resource limits')
        pipe.send((True,inspect_pdf(raw)))
    except Exception as exc:
        pipe.send((False,type(exc).__name__))
    finally: pipe.close()

def validate_pdf(raw,timeout=30):
    ctx=multiprocessing.get_context('spawn')
    parent,child=ctx.Pipe(duplex=False)
    process=ctx.Process(target=_child,args=(raw,child));process.start();child.close()
    try:
        if not parent.poll(timeout): raise ValueError('PDF_SCAN_TIMEOUT')
        try: ok,value=parent.recv()
        except EOFError: raise ValueError('PDF_SCAN_PROCESS_FAILED')
        if not ok: raise ValueError('INVALID_PDF_STRUCTURE')
        return value
    finally:
        parent.close()
        if process.is_alive(): process.kill()
        process.join()
