 
                                           
 
                                                                  
 
                     
 

from thrift.Thrift import TType, TMessageType, TFrozenDict, TException, TApplicationException
from thrift.protocol.TProtocol import TProtocolException
from thrift.TRecursive import fix_spec

import sys
import phyre.interface.shared.ttypes
import phyre.interface.scene.ttypes

from thrift.transport import TTransport
all_structs = []


class SpatialRelationship(object):
    NONE = 0
    ABOVE = 1
    BELOW = 2
    LEFT_OF = 3
    RIGHT_OF = 4
    TOUCHING_BRIEFLY = 5
    TOUCHING = 6
    INSIDE = 7
    NOT_TOUCHING = 8
    NOT_INSIDE = 9

    _VALUES_TO_NAMES = {
        0: "NONE",
        1: "ABOVE",
        2: "BELOW",
        3: "LEFT_OF",
        4: "RIGHT_OF",
        5: "TOUCHING_BRIEFLY",
        6: "TOUCHING",
        7: "INSIDE",
        8: "NOT_TOUCHING",
        9: "NOT_INSIDE",
    }

    _NAMES_TO_VALUES = {
        "NONE": 0,
        "ABOVE": 1,
        "BELOW": 2,
        "LEFT_OF": 3,
        "RIGHT_OF": 4,
        "TOUCHING_BRIEFLY": 5,
        "TOUCHING": 6,
        "INSIDE": 7,
        "NOT_TOUCHING": 8,
        "NOT_INSIDE": 9,
    }


class Task(object):
    pass               
             
            
              
              
                    
                  
                
                   
           
       


    def __init__(self, taskId=None, scene=None, bodyId1=None, bodyId2=None, relationships=None, description=None, solutions=None, phantomShape=None, tier=None,):
        self.taskId = taskId
        self.scene = scene
        self.bodyId1 = bodyId1
        self.bodyId2 = bodyId2
        self.relationships = relationships
        self.description = description
        self.solutions = solutions
        self.phantomShape = phantomShape
        self.tier = tier

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
                if ftype == TType.STRING:
                    self.taskId = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.STRUCT:
                    self.scene = phyre.interface.scene.ttypes.Scene()
                    self.scene.read(iprot)
                else:
                    iprot.skip(ftype)
            elif fid == 3:
                if ftype == TType.I32:
                    self.bodyId1 = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 4:
                if ftype == TType.I32:
                    self.bodyId2 = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 5:
                if ftype == TType.LIST:
                    self.relationships = []
                    (_etype3, _size0) = iprot.readListBegin()
                    for _i4 in range(_size0):
                        _elem5 = iprot.readI32()
                        self.relationships.append(_elem5)
                    iprot.readListEnd()
                else:
                    iprot.skip(ftype)
            elif fid == 6:
                if ftype == TType.STRING:
                    self.description = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                else:
                    iprot.skip(ftype)
            elif fid == 7:
                if ftype == TType.LIST:
                    self.solutions = []
                    (_etype9, _size6) = iprot.readListBegin()
                    for _i10 in range(_size6):
                        _elem11 = phyre.interface.scene.ttypes.UserInput()
                        _elem11.read(iprot)
                        self.solutions.append(_elem11)
                    iprot.readListEnd()
                else:
                    iprot.skip(ftype)
            elif fid == 8:
                if ftype == TType.STRUCT:
                    self.phantomShape = phyre.interface.scene.ttypes.Shape()
                    self.phantomShape.read(iprot)
                else:
                    iprot.skip(ftype)
            elif fid == 9:
                if ftype == TType.STRING:
                    self.tier = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
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
        oprot.writeStructBegin('Task')
        if self.taskId is not None:
            oprot.writeFieldBegin('taskId', TType.STRING, 1)
            oprot.writeString(self.taskId.encode('utf-8') if sys.version_info[0] == 2 else self.taskId)
            oprot.writeFieldEnd()
        if self.scene is not None:
            oprot.writeFieldBegin('scene', TType.STRUCT, 2)
            self.scene.write(oprot)
            oprot.writeFieldEnd()
        if self.bodyId1 is not None:
            oprot.writeFieldBegin('bodyId1', TType.I32, 3)
            oprot.writeI32(self.bodyId1)
            oprot.writeFieldEnd()
        if self.bodyId2 is not None:
            oprot.writeFieldBegin('bodyId2', TType.I32, 4)
            oprot.writeI32(self.bodyId2)
            oprot.writeFieldEnd()
        if self.relationships is not None:
            oprot.writeFieldBegin('relationships', TType.LIST, 5)
            oprot.writeListBegin(TType.I32, len(self.relationships))
            for iter12 in self.relationships:
                oprot.writeI32(iter12)
            oprot.writeListEnd()
            oprot.writeFieldEnd()
        if self.description is not None:
            oprot.writeFieldBegin('description', TType.STRING, 6)
            oprot.writeString(self.description.encode('utf-8') if sys.version_info[0] == 2 else self.description)
            oprot.writeFieldEnd()
        if self.solutions is not None:
            oprot.writeFieldBegin('solutions', TType.LIST, 7)
            oprot.writeListBegin(TType.STRUCT, len(self.solutions))
            for iter13 in self.solutions:
                iter13.write(oprot)
            oprot.writeListEnd()
            oprot.writeFieldEnd()
        if self.phantomShape is not None:
            oprot.writeFieldBegin('phantomShape', TType.STRUCT, 8)
            self.phantomShape.write(oprot)
            oprot.writeFieldEnd()
        if self.tier is not None:
            oprot.writeFieldBegin('tier', TType.STRING, 9)
            oprot.writeString(self.tier.encode('utf-8') if sys.version_info[0] == 2 else self.tier)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        if self.scene is None:
            raise TProtocolException(message='Required field scene is unset!')
        if self.bodyId1 is None:
            raise TProtocolException(message='Required field bodyId1 is unset!')
        if self.relationships is None:
            raise TProtocolException(message='Required field relationships is unset!')
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class TaskCollection(object):
    pass               
            
       


    def __init__(self, tasks=None,):
        self.tasks = tasks

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
                    self.tasks = []
                    (_etype17, _size14) = iprot.readListBegin()
                    for _i18 in range(_size14):
                        _elem19 = Task()
                        _elem19.read(iprot)
                        self.tasks.append(_elem19)
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
        oprot.writeStructBegin('TaskCollection')
        if self.tasks is not None:
            oprot.writeFieldBegin('tasks', TType.LIST, 1)
            oprot.writeListBegin(TType.STRUCT, len(self.tasks))
            for iter20 in self.tasks:
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


class TaskSimulation(object):
    pass               
                 
                
                      
                     
       


    def __init__(self, isSolution=None, sceneList=None, solvedStateList=None, stepsSimulated=None,):
        self.isSolution = isSolution
        self.sceneList = sceneList
        self.solvedStateList = solvedStateList
        self.stepsSimulated = stepsSimulated

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
                if ftype == TType.BOOL:
                    self.isSolution = iprot.readBool()
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.LIST:
                    self.sceneList = []
                    (_etype24, _size21) = iprot.readListBegin()
                    for _i25 in range(_size21):
                        _elem26 = phyre.interface.scene.ttypes.Scene()
                        _elem26.read(iprot)
                        self.sceneList.append(_elem26)
                    iprot.readListEnd()
                else:
                    iprot.skip(ftype)
            elif fid == 3:
                if ftype == TType.LIST:
                    self.solvedStateList = []
                    (_etype30, _size27) = iprot.readListBegin()
                    for _i31 in range(_size27):
                        _elem32 = iprot.readBool()
                        self.solvedStateList.append(_elem32)
                    iprot.readListEnd()
                else:
                    iprot.skip(ftype)
            elif fid == 4:
                if ftype == TType.I32:
                    self.stepsSimulated = iprot.readI32()
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
        oprot.writeStructBegin('TaskSimulation')
        if self.isSolution is not None:
            oprot.writeFieldBegin('isSolution', TType.BOOL, 1)
            oprot.writeBool(self.isSolution)
            oprot.writeFieldEnd()
        if self.sceneList is not None:
            oprot.writeFieldBegin('sceneList', TType.LIST, 2)
            oprot.writeListBegin(TType.STRUCT, len(self.sceneList))
            for iter33 in self.sceneList:
                iter33.write(oprot)
            oprot.writeListEnd()
            oprot.writeFieldEnd()
        if self.solvedStateList is not None:
            oprot.writeFieldBegin('solvedStateList', TType.LIST, 3)
            oprot.writeListBegin(TType.BOOL, len(self.solvedStateList))
            for iter34 in self.solvedStateList:
                oprot.writeBool(iter34)
            oprot.writeListEnd()
            oprot.writeFieldEnd()
        if self.stepsSimulated is not None:
            oprot.writeFieldBegin('stepsSimulated', TType.I32, 4)
            oprot.writeI32(self.stepsSimulated)
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


class TaskSimulationWithMeta(object):
    pass               
                 
                    
       


    def __init__(self, simulation=None, rendered_imgs=None,):
        self.simulation = simulation
        self.rendered_imgs = rendered_imgs

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
                    self.simulation = TaskSimulation()
                    self.simulation.read(iprot)
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.LIST:
                    self.rendered_imgs = []
                    (_etype38, _size35) = iprot.readListBegin()
                    for _i39 in range(_size35):
                        _elem40 = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                        self.rendered_imgs.append(_elem40)
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
        oprot.writeStructBegin('TaskSimulationWithMeta')
        if self.simulation is not None:
            oprot.writeFieldBegin('simulation', TType.STRUCT, 1)
            self.simulation.write(oprot)
            oprot.writeFieldEnd()
        if self.rendered_imgs is not None:
            oprot.writeFieldBegin('rendered_imgs', TType.LIST, 2)
            oprot.writeListBegin(TType.STRING, len(self.rendered_imgs))
            for iter41 in self.rendered_imgs:
                oprot.writeString(iter41.encode('utf-8') if sys.version_info[0] == 2 else iter41)
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


class Thumb(object):
    pass               
          
            
       


    def __init__(self, img=None, extra=None,):
        self.img = img
        self.extra = extra

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
                if ftype == TType.STRING:
                    self.img = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.STRING:
                    self.extra = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
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
        oprot.writeStructBegin('Thumb')
        if self.img is not None:
            oprot.writeFieldBegin('img', TType.STRING, 1)
            oprot.writeString(self.img.encode('utf-8') if sys.version_info[0] == 2 else self.img)
            oprot.writeFieldEnd()
        if self.extra is not None:
            oprot.writeFieldBegin('extra', TType.STRING, 2)
            oprot.writeString(self.extra.encode('utf-8') if sys.version_info[0] == 2 else self.extra)
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


class EvalData(object):
    pass               
                             
                                  
                             
                   
                        
                   
                    
                         
                    
                
                     
                
                      
                
       


    def __init__(self, attempts_to_solve_ball=None, attempts_to_solve_two_balls=None, attempts_to_solve_ramp=None, percent_ball=None, percent_two_balls=None, percent_ramp=None, solution_ball=None, solution_two_balls=None, solution_ramp=None, flag_ball=None, flag_two_balls=None, flag_ramp=None, known_solutions=None, num_tasks=None,):
        self.attempts_to_solve_ball = attempts_to_solve_ball
        self.attempts_to_solve_two_balls = attempts_to_solve_two_balls
        self.attempts_to_solve_ramp = attempts_to_solve_ramp
        self.percent_ball = percent_ball
        self.percent_two_balls = percent_two_balls
        self.percent_ramp = percent_ramp
        self.solution_ball = solution_ball
        self.solution_two_balls = solution_two_balls
        self.solution_ramp = solution_ramp
        self.flag_ball = flag_ball
        self.flag_two_balls = flag_two_balls
        self.flag_ramp = flag_ramp
        self.known_solutions = known_solutions
        self.num_tasks = num_tasks

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
                    self.attempts_to_solve_ball = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.I32:
                    self.attempts_to_solve_two_balls = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 3:
                if ftype == TType.I32:
                    self.attempts_to_solve_ramp = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 7:
                if ftype == TType.I32:
                    self.percent_ball = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 8:
                if ftype == TType.I32:
                    self.percent_two_balls = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 9:
                if ftype == TType.I32:
                    self.percent_ramp = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 4:
                if ftype == TType.STRUCT:
                    self.solution_ball = phyre.interface.scene.ttypes.UserInput()
                    self.solution_ball.read(iprot)
                else:
                    iprot.skip(ftype)
            elif fid == 5:
                if ftype == TType.STRUCT:
                    self.solution_two_balls = phyre.interface.scene.ttypes.UserInput()
                    self.solution_two_balls.read(iprot)
                else:
                    iprot.skip(ftype)
            elif fid == 6:
                if ftype == TType.STRUCT:
                    self.solution_ramp = phyre.interface.scene.ttypes.UserInput()
                    self.solution_ramp.read(iprot)
                else:
                    iprot.skip(ftype)
            elif fid == 10:
                if ftype == TType.STRING:
                    self.flag_ball = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                else:
                    iprot.skip(ftype)
            elif fid == 11:
                if ftype == TType.STRING:
                    self.flag_two_balls = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                else:
                    iprot.skip(ftype)
            elif fid == 12:
                if ftype == TType.STRING:
                    self.flag_ramp = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                else:
                    iprot.skip(ftype)
            elif fid == 13:
                if ftype == TType.LIST:
                    self.known_solutions = []
                    (_etype45, _size42) = iprot.readListBegin()
                    for _i46 in range(_size42):
                        _elem47 = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                        self.known_solutions.append(_elem47)
                    iprot.readListEnd()
                else:
                    iprot.skip(ftype)
            elif fid == 14:
                if ftype == TType.I32:
                    self.num_tasks = iprot.readI32()
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
        oprot.writeStructBegin('EvalData')
        if self.attempts_to_solve_ball is not None:
            oprot.writeFieldBegin('attempts_to_solve_ball', TType.I32, 1)
            oprot.writeI32(self.attempts_to_solve_ball)
            oprot.writeFieldEnd()
        if self.attempts_to_solve_two_balls is not None:
            oprot.writeFieldBegin('attempts_to_solve_two_balls', TType.I32, 2)
            oprot.writeI32(self.attempts_to_solve_two_balls)
            oprot.writeFieldEnd()
        if self.attempts_to_solve_ramp is not None:
            oprot.writeFieldBegin('attempts_to_solve_ramp', TType.I32, 3)
            oprot.writeI32(self.attempts_to_solve_ramp)
            oprot.writeFieldEnd()
        if self.solution_ball is not None:
            oprot.writeFieldBegin('solution_ball', TType.STRUCT, 4)
            self.solution_ball.write(oprot)
            oprot.writeFieldEnd()
        if self.solution_two_balls is not None:
            oprot.writeFieldBegin('solution_two_balls', TType.STRUCT, 5)
            self.solution_two_balls.write(oprot)
            oprot.writeFieldEnd()
        if self.solution_ramp is not None:
            oprot.writeFieldBegin('solution_ramp', TType.STRUCT, 6)
            self.solution_ramp.write(oprot)
            oprot.writeFieldEnd()
        if self.percent_ball is not None:
            oprot.writeFieldBegin('percent_ball', TType.I32, 7)
            oprot.writeI32(self.percent_ball)
            oprot.writeFieldEnd()
        if self.percent_two_balls is not None:
            oprot.writeFieldBegin('percent_two_balls', TType.I32, 8)
            oprot.writeI32(self.percent_two_balls)
            oprot.writeFieldEnd()
        if self.percent_ramp is not None:
            oprot.writeFieldBegin('percent_ramp', TType.I32, 9)
            oprot.writeI32(self.percent_ramp)
            oprot.writeFieldEnd()
        if self.flag_ball is not None:
            oprot.writeFieldBegin('flag_ball', TType.STRING, 10)
            oprot.writeString(self.flag_ball.encode('utf-8') if sys.version_info[0] == 2 else self.flag_ball)
            oprot.writeFieldEnd()
        if self.flag_two_balls is not None:
            oprot.writeFieldBegin('flag_two_balls', TType.STRING, 11)
            oprot.writeString(self.flag_two_balls.encode('utf-8') if sys.version_info[0] == 2 else self.flag_two_balls)
            oprot.writeFieldEnd()
        if self.flag_ramp is not None:
            oprot.writeFieldBegin('flag_ramp', TType.STRING, 12)
            oprot.writeString(self.flag_ramp.encode('utf-8') if sys.version_info[0] == 2 else self.flag_ramp)
            oprot.writeFieldEnd()
        if self.known_solutions is not None:
            oprot.writeFieldBegin('known_solutions', TType.LIST, 13)
            oprot.writeListBegin(TType.STRING, len(self.known_solutions))
            for iter48 in self.known_solutions:
                oprot.writeString(iter48.encode('utf-8') if sys.version_info[0] == 2 else iter48)
            oprot.writeListEnd()
            oprot.writeFieldEnd()
        if self.num_tasks is not None:
            oprot.writeFieldBegin('num_tasks', TType.I32, 14)
            oprot.writeI32(self.num_tasks)
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


class TaskWithMeta(object):
    pass               
           
                
                      
                     
                   
       


    def __init__(self, task=None, eval_data=None, template_params=None, text_eval_info=None, rendered_img=None,):
        self.task = task
        self.eval_data = eval_data
        self.template_params = template_params
        self.text_eval_info = text_eval_info
        self.rendered_img = rendered_img

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
                    self.task = Task()
                    self.task.read(iprot)
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.STRUCT:
                    self.eval_data = EvalData()
                    self.eval_data.read(iprot)
                else:
                    iprot.skip(ftype)
            elif fid == 3:
                if ftype == TType.STRING:
                    self.template_params = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                else:
                    iprot.skip(ftype)
            elif fid == 4:
                if ftype == TType.STRING:
                    self.text_eval_info = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                else:
                    iprot.skip(ftype)
            elif fid == 5:
                if ftype == TType.STRING:
                    self.rendered_img = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
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
        oprot.writeStructBegin('TaskWithMeta')
        if self.task is not None:
            oprot.writeFieldBegin('task', TType.STRUCT, 1)
            self.task.write(oprot)
            oprot.writeFieldEnd()
        if self.eval_data is not None:
            oprot.writeFieldBegin('eval_data', TType.STRUCT, 2)
            self.eval_data.write(oprot)
            oprot.writeFieldEnd()
        if self.template_params is not None:
            oprot.writeFieldBegin('template_params', TType.STRING, 3)
            oprot.writeString(self.template_params.encode('utf-8') if sys.version_info[0] == 2 else self.template_params)
            oprot.writeFieldEnd()
        if self.text_eval_info is not None:
            oprot.writeFieldBegin('text_eval_info', TType.STRING, 4)
            oprot.writeString(self.text_eval_info.encode('utf-8') if sys.version_info[0] == 2 else self.text_eval_info)
            oprot.writeFieldEnd()
        if self.rendered_img is not None:
            oprot.writeFieldBegin('rendered_img', TType.STRING, 5)
            oprot.writeString(self.rendered_img.encode('utf-8') if sys.version_info[0] == 2 else self.rendered_img)
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
all_structs.append(Task)
Task.thrift_spec = (
    None,     
    (1, TType.STRING, 'taskId', 'UTF8', None, ),     
    (2, TType.STRUCT, 'scene', [phyre.interface.scene.ttypes.Scene, None], None, ),     
    (3, TType.I32, 'bodyId1', None, None, ),     
    (4, TType.I32, 'bodyId2', None, None, ),     
    (5, TType.LIST, 'relationships', (TType.I32, None, False), None, ),     
    (6, TType.STRING, 'description', 'UTF8', None, ),     
    (7, TType.LIST, 'solutions', (TType.STRUCT, [phyre.interface.scene.ttypes.UserInput, None], False), None, ),     
    (8, TType.STRUCT, 'phantomShape', [phyre.interface.scene.ttypes.Shape, None], None, ),     
    (9, TType.STRING, 'tier', 'UTF8', None, ),     
)
all_structs.append(TaskCollection)
TaskCollection.thrift_spec = (
    None,     
    (1, TType.LIST, 'tasks', (TType.STRUCT, [Task, None], False), None, ),     
)
all_structs.append(TaskSimulation)
TaskSimulation.thrift_spec = (
    None,     
    (1, TType.BOOL, 'isSolution', None, None, ),     
    (2, TType.LIST, 'sceneList', (TType.STRUCT, [phyre.interface.scene.ttypes.Scene, None], False), None, ),     
    (3, TType.LIST, 'solvedStateList', (TType.BOOL, None, False), None, ),     
    (4, TType.I32, 'stepsSimulated', None, None, ),     
)
all_structs.append(TaskSimulationWithMeta)
TaskSimulationWithMeta.thrift_spec = (
    None,     
    (1, TType.STRUCT, 'simulation', [TaskSimulation, None], None, ),     
    (2, TType.LIST, 'rendered_imgs', (TType.STRING, 'UTF8', False), None, ),     
)
all_structs.append(Thumb)
Thumb.thrift_spec = (
    None,     
    (1, TType.STRING, 'img', 'UTF8', None, ),     
    (2, TType.STRING, 'extra', 'UTF8', None, ),     
)
all_structs.append(EvalData)
EvalData.thrift_spec = (
    None,     
    (1, TType.I32, 'attempts_to_solve_ball', None, None, ),     
    (2, TType.I32, 'attempts_to_solve_two_balls', None, None, ),     
    (3, TType.I32, 'attempts_to_solve_ramp', None, None, ),     
    (4, TType.STRUCT, 'solution_ball', [phyre.interface.scene.ttypes.UserInput, None], None, ),     
    (5, TType.STRUCT, 'solution_two_balls', [phyre.interface.scene.ttypes.UserInput, None], None, ),     
    (6, TType.STRUCT, 'solution_ramp', [phyre.interface.scene.ttypes.UserInput, None], None, ),     
    (7, TType.I32, 'percent_ball', None, None, ),     
    (8, TType.I32, 'percent_two_balls', None, None, ),     
    (9, TType.I32, 'percent_ramp', None, None, ),     
    (10, TType.STRING, 'flag_ball', 'UTF8', None, ),      
    (11, TType.STRING, 'flag_two_balls', 'UTF8', None, ),      
    (12, TType.STRING, 'flag_ramp', 'UTF8', None, ),      
    (13, TType.LIST, 'known_solutions', (TType.STRING, 'UTF8', False), None, ),      
    (14, TType.I32, 'num_tasks', None, None, ),      
)
all_structs.append(TaskWithMeta)
TaskWithMeta.thrift_spec = (
    None,     
    (1, TType.STRUCT, 'task', [Task, None], None, ),     
    (2, TType.STRUCT, 'eval_data', [EvalData, None], None, ),     
    (3, TType.STRING, 'template_params', 'UTF8', None, ),     
    (4, TType.STRING, 'text_eval_info', 'UTF8', None, ),     
    (5, TType.STRING, 'rendered_img', 'UTF8', None, ),     
)
fix_spec(all_structs)
del all_structs
