 
                                           
 
                                                                  
 
                     
 

from thrift.Thrift import TType, TMessageType, TFrozenDict, TException, TApplicationException
from thrift.protocol.TProtocol import TProtocolException
from thrift.TRecursive import fix_spec

import sys

from thrift.transport import TTransport
all_structs = []


class Color(object):
    WHITE = 0
    BLACK = 6
    GRAY = 5
    GREEN = 2
    BLUE = 3
    PURPLE = 4
    RED = 1
    LIGHT_RED = 7

    _VALUES_TO_NAMES = {
        0: "WHITE",
        6: "BLACK",
        5: "GRAY",
        2: "GREEN",
        3: "BLUE",
        4: "PURPLE",
        1: "RED",
        7: "LIGHT_RED",
    }

    _NAMES_TO_VALUES = {
        "WHITE": 0,
        "BLACK": 6,
        "GRAY": 5,
        "GREEN": 2,
        "BLUE": 3,
        "PURPLE": 4,
        "RED": 1,
        "LIGHT_RED": 7,
    }


class Error_message(TException):
    pass               
              
               
       


    def __init__(self, errorNo=None, errorMsg=None,):
        self.errorNo = errorNo
        self.errorMsg = errorMsg

    def read(self, iprot):
        if iprot._fast_decode is not None and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None:
            iprot._fast_decode(self, iprot, [self.__class__, self.thrift_spec])
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 1:
                if ftype == TType.I32:
                    self.errorNo = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.STRING:
                    self.errorMsg = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                else:
                    iprot.skip(ftype)
            else:
                iprot.skip(ftype)
            iprot.readFieldEnd()
        iprot.readStructEnd()

    def write(self, oprot):
        if oprot._fast_encode is not None and self.thrift_spec is not None:
            oprot.trans.write(oprot._fast_encode(self, [self.__class__, self.thrift_spec]))
            return
        oprot.writeStructBegin('Error_message')
        if self.errorNo is not None:
            oprot.writeFieldBegin('errorNo', TType.I32, 1)
            oprot.writeI32(self.errorNo)
            oprot.writeFieldEnd()
        if self.errorMsg is not None:
            oprot.writeFieldBegin('errorMsg', TType.STRING, 2)
            oprot.writeString(self.errorMsg.encode('utf-8') if sys.version_info[0] == 2 else self.errorMsg)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        return

    def __str__(self):
        return repr(self)

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)
all_structs.append(Error_message)
Error_message.thrift_spec = (
    None,     
    (1, TType.I32, 'errorNo', None, None, ),     
    (2, TType.STRING, 'errorMsg', 'UTF8', None, ),     
)
fix_spec(all_structs)
del all_structs
