#!/usr/bin/env python3
                                                                                                   

                                                                                                                        
                                                                                                                         
                                                                                                                    
                                                                                                                                   
                                                                                                                        
                                                                                                                        
                                                                                                                           
                                                                                                                        
                                                                                                   
                                                                                                                            
                                                                   

                                                                          
                                                                                                                   
                                                                                                           
                                                                                                         
   
import builtins
import json
import resource
import sys

ALLOWED_ROOTS = {'numpy', 'scipy', 'math', 'cmath', 'functools', 'itertools', 'collections', 'operator', 'typing', 'warnings', 'decimal', 'fractions', 'statistics'}
REMOVED = {'open', 'exec', 'eval', 'compile', 'input', 'breakpoint', 'help', 'exit', 'quit', 'globals', 'vars', 'memoryview', '__loader__', '__spec__'}
_real_import = builtins.__import__


def limited_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level != 0 or name.split('.')[0] not in ALLOWED_ROOTS:
        raise ImportError(f'import of {name!r} is not permitted in discovered_law (allowed: {", ".join(sorted(ALLOWED_ROOTS))})')
    return _real_import(name, globals, locals, fromlist, level)


def safe_builtins():
    table = {k: v for k, v in vars(builtins).items() if k not in REMOVED}
    table['__import__'] = limited_import
    return table


def _deny_ffi(event, args):
    if event.startswith('ctypes.') or event.startswith('cffi.'):
        raise PermissionError(f'native FFI is disabled for Player code ({event})')


def install_ffi_guard():
    pass                                                                                                                   
                                                                                                                                
                                                                                                                     
    sys.addaudithook(_deny_ffi)


def plain(value):
    if hasattr(value, 'tolist'):
        return value.tolist()
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    raise TypeError(f'unsupported return type {type(value).__name__}')


def main():
    for limit, value in ((resource.RLIMIT_CPU, 900), (resource.RLIMIT_FSIZE, 1 << 20)):
        try:
            resource.setrlimit(limit, (value, value))
        except (ValueError, OSError):
            pass
    import ctypes                                                                                                                
    import numpy                                                               
    import scipy              
    install_ffi_guard()
    namespace = None
    out = sys.stdout
    for line in sys.stdin:
        try:
            request = json.loads(line)
            op = request['op']
            if op == 'compile':
                namespace = {'__builtins__': safe_builtins(), '__name__': 'discovered_law'}
                exec(builtins.compile(request['source'], '<discovered_law>', 'exec'), namespace)
                reply = {'ok': True, 'law': callable(namespace.get('discovered_law')), 'fit': callable(namespace.get('fit_parameters'))}
            elif op == 'law':
                reply = {'ok': True, 'value': plain(namespace['discovered_law'](*request.get('args', []), **request.get('kwargs', {})))}
            elif op == 'fit_parameters':
                reply = {'ok': True, 'value': plain(namespace['fit_parameters']())}
            else:
                reply = {'ok': False, 'error': 'unknown op'}
        except BaseException as error:                                     
            reply = {'ok': False, 'error': f'{type(error).__name__}: {error}'[:2000]}
        out.write(json.dumps(reply) + '\n')
        out.flush()


if __name__ == '__main__':
    main()
