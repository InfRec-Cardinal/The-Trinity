 
                                           
 
                                                                  
 
                     
 

from thrift.Thrift import TType, TMessageType, TFrozenDict, TException, TApplicationException
from thrift.protocol.TProtocol import TProtocolException
from thrift.TRecursive import fix_spec

import sys
import phyre.interface.shared.ttypes

from thrift.transport import TTransport
all_structs = []


class BodyType(object):
    STATIC = 1
    DYNAMIC = 2

    _VALUES_TO_NAMES = {
        1: "STATIC",
        2: "DYNAMIC",
    }

    _NAMES_TO_VALUES = {
        "STATIC": 1,
        "DYNAMIC": 2,
    }


class ShapeType(object):
    UNDEFINED = 0
    BALL = 1
    BAR = 2
    JAR = 3
    STANDINGSTICKS = 4

    _VALUES_TO_NAMES = {
        0: "UNDEFINED",
        1: "BALL",
        2: "BAR",
        3: "JAR",
        4: "STANDINGSTICKS",
    }

    _NAMES_TO_VALUES = {
        "UNDEFINED": 0,
        "BALL": 1,
        "BAR": 2,
        "JAR": 3,
        "STANDINGSTICKS": 4,
    }


class UserInputStatus(object):
    UNDEFINED = 0
    NO_OCCLUSIONS = 1
    HAD_OCCLUSIONS = 2

    _VALUES_TO_NAMES = {
        0: "UNDEFINED",
        1: "NO_OCCLUSIONS",
        2: "HAD_OCCLUSIONS",
    }

    _NAMES_TO_VALUES = {
        "UNDEFINED": 0,
        "NO_OCCLUSIONS": 1,
        "HAD_OCCLUSIONS": 2,
    }


class Vector(object):
    pass               
        
        
       


    def __init__(self, x=None, y=None,):
        self.x = x
        self.y = y

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
                if ftype == TType.DOUBLE:
                    self.x = iprot.readDouble()
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.DOUBLE:
                    self.y = iprot.readDouble()
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
        oprot.writeStructBegin('Vector')
        if self.x is not None:
            oprot.writeFieldBegin('x', TType.DOUBLE, 1)
            oprot.writeDouble(self.x)
            oprot.writeFieldEnd()
        if self.y is not None:
            oprot.writeFieldBegin('y', TType.DOUBLE, 2)
            oprot.writeDouble(self.y)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        if self.x is None:
            raise TProtocolException(message='Required field x is unset!')
        if self.y is None:
            raise TProtocolException(message='Required field y is unset!')
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class IntVector(object):
    pass               
        
        
       


    def __init__(self, x=None, y=None,):
        self.x = x
        self.y = y

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
                    self.x = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.I32:
                    self.y = iprot.readI32()
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
        oprot.writeStructBegin('IntVector')
        if self.x is not None:
            oprot.writeFieldBegin('x', TType.I32, 1)
            oprot.writeI32(self.x)
            oprot.writeFieldEnd()
        if self.y is not None:
            oprot.writeFieldBegin('y', TType.I32, 2)
            oprot.writeI32(self.y)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        if self.x is None:
            raise TProtocolException(message='Required field x is unset!')
        if self.y is None:
            raise TProtocolException(message='Required field y is unset!')
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class Polygon(object):
    pass               
               
       


    def __init__(self, vertices=None,):
        self.vertices = vertices

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
                if ftype == TType.LIST:
                    self.vertices = []
                    (_etype3, _size0) = iprot.readListBegin()
                    for _i4 in range(_size0):
                        _elem5 = Vector()
                        _elem5.read(iprot)
                        self.vertices.append(_elem5)
                    iprot.readListEnd()
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
        oprot.writeStructBegin('Polygon')
        if self.vertices is not None:
            oprot.writeFieldBegin('vertices', TType.LIST, 1)
            oprot.writeListBegin(TType.STRUCT, len(self.vertices))
            for iter6 in self.vertices:
                iter6.write(oprot)
            oprot.writeListEnd()
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        if self.vertices is None:
            raise TProtocolException(message='Required field vertices is unset!')
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class Circle(object):
    pass               
             
       


    def __init__(self, radius=None,):
        self.radius = radius

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
                if ftype == TType.DOUBLE:
                    self.radius = iprot.readDouble()
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
        oprot.writeStructBegin('Circle')
        if self.radius is not None:
            oprot.writeFieldBegin('radius', TType.DOUBLE, 1)
            oprot.writeDouble(self.radius)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        if self.radius is None:
            raise TProtocolException(message='Required field radius is unset!')
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class Shape(object):
    pass               
              
             
       


    def __init__(self, polygon=None, circle=None,):
        self.polygon = polygon
        self.circle = circle

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
                if ftype == TType.STRUCT:
                    self.polygon = Polygon()
                    self.polygon.read(iprot)
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.STRUCT:
                    self.circle = Circle()
                    self.circle.read(iprot)
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
        oprot.writeStructBegin('Shape')
        if self.polygon is not None:
            oprot.writeFieldBegin('polygon', TType.STRUCT, 1)
            self.polygon.write(oprot)
            oprot.writeFieldEnd()
        if self.circle is not None:
            oprot.writeFieldBegin('circle', TType.STRUCT, 2)
            self.circle.write(oprot)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class Body(object):
    pass               
               
               
            
             
            
                
               
       


    def __init__(self, position=None, bodyType=None, angle=0, shapes=None, color=None, shapeType=0, diameter=None,):
        self.position = position
        self.bodyType = bodyType
        self.angle = angle
        self.shapes = shapes
        self.color = color
        self.shapeType = shapeType
        self.diameter = diameter

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
                if ftype == TType.STRUCT:
                    self.position = Vector()
                    self.position.read(iprot)
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.I32:
                    self.bodyType = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 3:
                if ftype == TType.DOUBLE:
                    self.angle = iprot.readDouble()
                else:
                    iprot.skip(ftype)
            elif fid == 4:
                if ftype == TType.LIST:
                    self.shapes = []
                    (_etype10, _size7) = iprot.readListBegin()
                    for _i11 in range(_size7):
                        _elem12 = Shape()
                        _elem12.read(iprot)
                        self.shapes.append(_elem12)
                    iprot.readListEnd()
                else:
                    iprot.skip(ftype)
            elif fid == 5:
                if ftype == TType.I32:
                    self.color = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 6:
                if ftype == TType.I32:
                    self.shapeType = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 7:
                if ftype == TType.DOUBLE:
                    self.diameter = iprot.readDouble()
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
        oprot.writeStructBegin('Body')
        if self.position is not None:
            oprot.writeFieldBegin('position', TType.STRUCT, 1)
            self.position.write(oprot)
            oprot.writeFieldEnd()
        if self.bodyType is not None:
            oprot.writeFieldBegin('bodyType', TType.I32, 2)
            oprot.writeI32(self.bodyType)
            oprot.writeFieldEnd()
        if self.angle is not None:
            oprot.writeFieldBegin('angle', TType.DOUBLE, 3)
            oprot.writeDouble(self.angle)
            oprot.writeFieldEnd()
        if self.shapes is not None:
            oprot.writeFieldBegin('shapes', TType.LIST, 4)
            oprot.writeListBegin(TType.STRUCT, len(self.shapes))
            for iter13 in self.shapes:
                iter13.write(oprot)
            oprot.writeListEnd()
            oprot.writeFieldEnd()
        if self.color is not None:
            oprot.writeFieldBegin('color', TType.I32, 5)
            oprot.writeI32(self.color)
            oprot.writeFieldEnd()
        if self.shapeType is not None:
            oprot.writeFieldBegin('shapeType', TType.I32, 6)
            oprot.writeI32(self.shapeType)
            oprot.writeFieldEnd()
        if self.diameter is not None:
            oprot.writeFieldBegin('diameter', TType.DOUBLE, 7)
            oprot.writeDouble(self.diameter)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        if self.position is None:
            raise TProtocolException(message='Required field position is unset!')
        if self.bodyType is None:
            raise TProtocolException(message='Required field bodyType is unset!')
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class AbsoluteConvexPolygon(object):
    pass               
               
       


    def __init__(self, vertices=None,):
        self.vertices = vertices

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
                if ftype == TType.LIST:
                    self.vertices = []
                    (_etype17, _size14) = iprot.readListBegin()
                    for _i18 in range(_size14):
                        _elem19 = Vector()
                        _elem19.read(iprot)
                        self.vertices.append(_elem19)
                    iprot.readListEnd()
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
        oprot.writeStructBegin('AbsoluteConvexPolygon')
        if self.vertices is not None:
            oprot.writeFieldBegin('vertices', TType.LIST, 1)
            oprot.writeListBegin(TType.STRUCT, len(self.vertices))
            for iter20 in self.vertices:
                iter20.write(oprot)
            oprot.writeListEnd()
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class CircleWithPosition(object):
    pass               
               
             
       


    def __init__(self, position=None, radius=None,):
        self.position = position
        self.radius = radius

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
                if ftype == TType.STRUCT:
                    self.position = Vector()
                    self.position.read(iprot)
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.DOUBLE:
                    self.radius = iprot.readDouble()
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
        oprot.writeStructBegin('CircleWithPosition')
        if self.position is not None:
            oprot.writeFieldBegin('position', TType.STRUCT, 1)
            self.position.write(oprot)
            oprot.writeFieldEnd()
        if self.radius is not None:
            oprot.writeFieldBegin('radius', TType.DOUBLE, 2)
            oprot.writeDouble(self.radius)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class UserInput(object):
    pass               
               
            
                           
       


    def __init__(self, polygons=None, balls=None, flattened_point_list=None,):
        self.polygons = polygons
        self.balls = balls
        self.flattened_point_list = flattened_point_list

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
                if ftype == TType.LIST:
                    self.polygons = []
                    (_etype24, _size21) = iprot.readListBegin()
                    for _i25 in range(_size21):
                        _elem26 = AbsoluteConvexPolygon()
                        _elem26.read(iprot)
                        self.polygons.append(_elem26)
                    iprot.readListEnd()
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.LIST:
                    self.balls = []
                    (_etype30, _size27) = iprot.readListBegin()
                    for _i31 in range(_size27):
                        _elem32 = CircleWithPosition()
                        _elem32.read(iprot)
                        self.balls.append(_elem32)
                    iprot.readListEnd()
                else:
                    iprot.skip(ftype)
            elif fid == 3:
                if ftype == TType.LIST:
                    self.flattened_point_list = []
                    (_etype36, _size33) = iprot.readListBegin()
                    for _i37 in range(_size33):
                        _elem38 = iprot.readI32()
                        self.flattened_point_list.append(_elem38)
                    iprot.readListEnd()
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
        oprot.writeStructBegin('UserInput')
        if self.polygons is not None:
            oprot.writeFieldBegin('polygons', TType.LIST, 1)
            oprot.writeListBegin(TType.STRUCT, len(self.polygons))
            for iter39 in self.polygons:
                iter39.write(oprot)
            oprot.writeListEnd()
            oprot.writeFieldEnd()
        if self.balls is not None:
            oprot.writeFieldBegin('balls', TType.LIST, 2)
            oprot.writeListBegin(TType.STRUCT, len(self.balls))
            for iter40 in self.balls:
                iter40.write(oprot)
            oprot.writeListEnd()
            oprot.writeFieldEnd()
        if self.flattened_point_list is not None:
            oprot.writeFieldBegin('flattened_point_list', TType.LIST, 3)
            oprot.writeListBegin(TType.I32, len(self.flattened_point_list))
            for iter41 in self.flattened_point_list:
                oprot.writeI32(iter41)
            oprot.writeListEnd()
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class Scene(object):
    pass               
             
                        
            
             
                        
       


    def __init__(self, bodies=None, user_input_bodies=None, width=None, height=None, user_input_status=0,):
        self.bodies = bodies
        self.user_input_bodies = user_input_bodies
        self.width = width
        self.height = height
        self.user_input_status = user_input_status

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
                if ftype == TType.LIST:
                    self.bodies = []
                    (_etype45, _size42) = iprot.readListBegin()
                    for _i46 in range(_size42):
                        _elem47 = Body()
                        _elem47.read(iprot)
                        self.bodies.append(_elem47)
                    iprot.readListEnd()
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.LIST:
                    self.user_input_bodies = []
                    (_etype51, _size48) = iprot.readListBegin()
                    for _i52 in range(_size48):
                        _elem53 = Body()
                        _elem53.read(iprot)
                        self.user_input_bodies.append(_elem53)
                    iprot.readListEnd()
                else:
                    iprot.skip(ftype)
            elif fid == 3:
                if ftype == TType.I32:
                    self.width = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 4:
                if ftype == TType.I32:
                    self.height = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 5:
                if ftype == TType.I32:
                    self.user_input_status = iprot.readI32()
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
        oprot.writeStructBegin('Scene')
        if self.bodies is not None:
            oprot.writeFieldBegin('bodies', TType.LIST, 1)
            oprot.writeListBegin(TType.STRUCT, len(self.bodies))
            for iter54 in self.bodies:
                iter54.write(oprot)
            oprot.writeListEnd()
            oprot.writeFieldEnd()
        if self.user_input_bodies is not None:
            oprot.writeFieldBegin('user_input_bodies', TType.LIST, 2)
            oprot.writeListBegin(TType.STRUCT, len(self.user_input_bodies))
            for iter55 in self.user_input_bodies:
                iter55.write(oprot)
            oprot.writeListEnd()
            oprot.writeFieldEnd()
        if self.width is not None:
            oprot.writeFieldBegin('width', TType.I32, 3)
            oprot.writeI32(self.width)
            oprot.writeFieldEnd()
        if self.height is not None:
            oprot.writeFieldBegin('height', TType.I32, 4)
            oprot.writeI32(self.height)
            oprot.writeFieldEnd()
        if self.user_input_status is not None:
            oprot.writeFieldBegin('user_input_status', TType.I32, 5)
            oprot.writeI32(self.user_input_status)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        if self.width is None:
            raise TProtocolException(message='Required field width is unset!')
        if self.height is None:
            raise TProtocolException(message='Required field height is unset!')
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class Solution(object):
    pass               
             
       


    def __init__(self, points=None,):
        self.points = points

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
                if ftype == TType.LIST:
                    self.points = []
                    (_etype59, _size56) = iprot.readListBegin()
                    for _i60 in range(_size56):
                        _elem61 = IntVector()
                        _elem61.read(iprot)
                        self.points.append(_elem61)
                    iprot.readListEnd()
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
        oprot.writeStructBegin('Solution')
        if self.points is not None:
            oprot.writeFieldBegin('points', TType.LIST, 1)
            oprot.writeListBegin(TType.STRUCT, len(self.points))
            for iter62 in self.points:
                iter62.write(oprot)
            oprot.writeListEnd()
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class Image(object):
    pass               
             
             
            
       


    def __init__(self, values=None, height=None, width=None,):
        self.values = values
        self.height = height
        self.width = width

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
                if ftype == TType.LIST:
                    self.values = []
                    (_etype66, _size63) = iprot.readListBegin()
                    for _i67 in range(_size63):
                        _elem68 = iprot.readI32()
                        self.values.append(_elem68)
                    iprot.readListEnd()
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.I32:
                    self.height = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 3:
                if ftype == TType.I32:
                    self.width = iprot.readI32()
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
        oprot.writeStructBegin('Image')
        if self.values is not None:
            oprot.writeFieldBegin('values', TType.LIST, 1)
            oprot.writeListBegin(TType.I32, len(self.values))
            for iter69 in self.values:
                oprot.writeI32(iter69)
            oprot.writeListEnd()
            oprot.writeFieldEnd()
        if self.height is not None:
            oprot.writeFieldBegin('height', TType.I32, 2)
            oprot.writeI32(self.height)
            oprot.writeFieldEnd()
        if self.width is not None:
            oprot.writeFieldBegin('width', TType.I32, 3)
            oprot.writeI32(self.width)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)
all_structs.append(Vector)
Vector.thrift_spec = (
    None,     
    (1, TType.DOUBLE, 'x', None, None, ),     
    (2, TType.DOUBLE, 'y', None, None, ),     
)
all_structs.append(IntVector)
IntVector.thrift_spec = (
    None,     
    (1, TType.I32, 'x', None, None, ),     
    (2, TType.I32, 'y', None, None, ),     
)
all_structs.append(Polygon)
Polygon.thrift_spec = (
    None,     
    (1, TType.LIST, 'vertices', (TType.STRUCT, [Vector, None], False), None, ),     
)
all_structs.append(Circle)
Circle.thrift_spec = (
    None,     
    (1, TType.DOUBLE, 'radius', None, None, ),     
)
all_structs.append(Shape)
Shape.thrift_spec = (
    None,     
    (1, TType.STRUCT, 'polygon', [Polygon, None], None, ),     
    (2, TType.STRUCT, 'circle', [Circle, None], None, ),     
)
all_structs.append(Body)
Body.thrift_spec = (
    None,     
    (1, TType.STRUCT, 'position', [Vector, None], None, ),     
    (2, TType.I32, 'bodyType', None, None, ),     
    (3, TType.DOUBLE, 'angle', None, 0, ),     
    (4, TType.LIST, 'shapes', (TType.STRUCT, [Shape, None], False), None, ),     
    (5, TType.I32, 'color', None, None, ),     
    (6, TType.I32, 'shapeType', None, 0, ),     
    (7, TType.DOUBLE, 'diameter', None, None, ),     
)
all_structs.append(AbsoluteConvexPolygon)
AbsoluteConvexPolygon.thrift_spec = (
    None,     
    (1, TType.LIST, 'vertices', (TType.STRUCT, [Vector, None], False), None, ),     
)
all_structs.append(CircleWithPosition)
CircleWithPosition.thrift_spec = (
    None,     
    (1, TType.STRUCT, 'position', [Vector, None], None, ),     
    (2, TType.DOUBLE, 'radius', None, None, ),     
)
all_structs.append(UserInput)
UserInput.thrift_spec = (
    None,     
    (1, TType.LIST, 'polygons', (TType.STRUCT, [AbsoluteConvexPolygon, None], False), None, ),     
    (2, TType.LIST, 'balls', (TType.STRUCT, [CircleWithPosition, None], False), None, ),     
    (3, TType.LIST, 'flattened_point_list', (TType.I32, None, False), None, ),     
)
all_structs.append(Scene)
Scene.thrift_spec = (
    None,     
    (1, TType.LIST, 'bodies', (TType.STRUCT, [Body, None], False), None, ),     
    (2, TType.LIST, 'user_input_bodies', (TType.STRUCT, [Body, None], False), None, ),     
    (3, TType.I32, 'width', None, None, ),     
    (4, TType.I32, 'height', None, None, ),     
    (5, TType.I32, 'user_input_status', None, 0, ),     
)
all_structs.append(Solution)
Solution.thrift_spec = (
    None,     
    (1, TType.LIST, 'points', (TType.STRUCT, [IntVector, None], False), None, ),     
)
all_structs.append(Image)
Image.thrift_spec = (
    None,     
    (1, TType.LIST, 'values', (TType.I32, None, False), None, ),     
    (2, TType.I32, 'height', None, None, ),     
    (3, TType.I32, 'width', None, None, ),     
)
fix_spec(all_structs)
del all_structs
