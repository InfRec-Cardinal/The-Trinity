 
                                           
 
                                                                  
 
                     
 

from thrift.Thrift import TType, TMessageType, TFrozenDict, TException, TApplicationException
from thrift.protocol.TProtocol import TProtocolException
from thrift.TRecursive import fix_spec

import sys
import logging
from .ttypes import *
from thrift.Thrift import TProcessor
from thrift.transport import TTransport
all_structs = []


class Iface(object):
    def list_task_tier_map(self, task_id_pattern):
        pass                   
                          
           
        pass

    def load_evaluation_data(self, task_id_pattern):
        pass                   
                          
           
        pass

    def get_task_from_id(self, task_id):
        pass                   
                  
           
        pass

    def get_task_thumbs(self, task_ids):
        pass                   
                   
           
        pass

    def simulate_task_by_id(self, task_id, user_input, dilate):
        pass                   
                  
                     
                 
           
        pass

    def simulate_task_with_last_input(self, task):
        pass                   
               
           
        pass

    def save_solution(self, task_id, user_input):
        pass                   
                  
                     
           
        pass

    def get_last_input(self):
        pass

    def get_eval_user_input(self, task_id, tier_name):
        pass                   
                  
                    
           
        pass

    def render(self, scene):
        pass                   
                
           
        pass


class Client(Iface):
    def __init__(self, iprot, oprot=None):
        self._iprot = self._oprot = iprot
        if oprot is not None:
            self._oprot = oprot
        self._seqid = 0

    def list_task_tier_map(self, task_id_pattern):
        pass                   
                          
           
        self.send_list_task_tier_map(task_id_pattern)
        return self.recv_list_task_tier_map()

    def send_list_task_tier_map(self, task_id_pattern):
        self._oprot.writeMessageBegin('list_task_tier_map', TMessageType.CALL, self._seqid)
        args = list_task_tier_map_args()
        args.task_id_pattern = task_id_pattern
        args.write(self._oprot)
        self._oprot.writeMessageEnd()
        self._oprot.trans.flush()

    def recv_list_task_tier_map(self):
        iprot = self._iprot
        (fname, mtype, rseqid) = iprot.readMessageBegin()
        if mtype == TMessageType.EXCEPTION:
            x = TApplicationException()
            x.read(iprot)
            iprot.readMessageEnd()
            raise x
        result = list_task_tier_map_result()
        result.read(iprot)
        iprot.readMessageEnd()
        if result.success is not None:
            return result.success
        raise TApplicationException(TApplicationException.MISSING_RESULT, "list_task_tier_map failed: unknown result")

    def load_evaluation_data(self, task_id_pattern):
        pass                   
                          
           
        self.send_load_evaluation_data(task_id_pattern)
        return self.recv_load_evaluation_data()

    def send_load_evaluation_data(self, task_id_pattern):
        self._oprot.writeMessageBegin('load_evaluation_data', TMessageType.CALL, self._seqid)
        args = load_evaluation_data_args()
        args.task_id_pattern = task_id_pattern
        args.write(self._oprot)
        self._oprot.writeMessageEnd()
        self._oprot.trans.flush()

    def recv_load_evaluation_data(self):
        iprot = self._iprot
        (fname, mtype, rseqid) = iprot.readMessageBegin()
        if mtype == TMessageType.EXCEPTION:
            x = TApplicationException()
            x.read(iprot)
            iprot.readMessageEnd()
            raise x
        result = load_evaluation_data_result()
        result.read(iprot)
        iprot.readMessageEnd()
        if result.success is not None:
            return result.success
        raise TApplicationException(TApplicationException.MISSING_RESULT, "load_evaluation_data failed: unknown result")

    def get_task_from_id(self, task_id):
        pass                   
                  
           
        self.send_get_task_from_id(task_id)
        return self.recv_get_task_from_id()

    def send_get_task_from_id(self, task_id):
        self._oprot.writeMessageBegin('get_task_from_id', TMessageType.CALL, self._seqid)
        args = get_task_from_id_args()
        args.task_id = task_id
        args.write(self._oprot)
        self._oprot.writeMessageEnd()
        self._oprot.trans.flush()

    def recv_get_task_from_id(self):
        iprot = self._iprot
        (fname, mtype, rseqid) = iprot.readMessageBegin()
        if mtype == TMessageType.EXCEPTION:
            x = TApplicationException()
            x.read(iprot)
            iprot.readMessageEnd()
            raise x
        result = get_task_from_id_result()
        result.read(iprot)
        iprot.readMessageEnd()
        if result.success is not None:
            return result.success
        if result.err is not None:
            raise result.err
        raise TApplicationException(TApplicationException.MISSING_RESULT, "get_task_from_id failed: unknown result")

    def get_task_thumbs(self, task_ids):
        pass                   
                   
           
        self.send_get_task_thumbs(task_ids)
        return self.recv_get_task_thumbs()

    def send_get_task_thumbs(self, task_ids):
        self._oprot.writeMessageBegin('get_task_thumbs', TMessageType.CALL, self._seqid)
        args = get_task_thumbs_args()
        args.task_ids = task_ids
        args.write(self._oprot)
        self._oprot.writeMessageEnd()
        self._oprot.trans.flush()

    def recv_get_task_thumbs(self):
        iprot = self._iprot
        (fname, mtype, rseqid) = iprot.readMessageBegin()
        if mtype == TMessageType.EXCEPTION:
            x = TApplicationException()
            x.read(iprot)
            iprot.readMessageEnd()
            raise x
        result = get_task_thumbs_result()
        result.read(iprot)
        iprot.readMessageEnd()
        if result.success is not None:
            return result.success
        raise TApplicationException(TApplicationException.MISSING_RESULT, "get_task_thumbs failed: unknown result")

    def simulate_task_by_id(self, task_id, user_input, dilate):
        pass                   
                  
                     
                 
           
        self.send_simulate_task_by_id(task_id, user_input, dilate)
        return self.recv_simulate_task_by_id()

    def send_simulate_task_by_id(self, task_id, user_input, dilate):
        self._oprot.writeMessageBegin('simulate_task_by_id', TMessageType.CALL, self._seqid)
        args = simulate_task_by_id_args()
        args.task_id = task_id
        args.user_input = user_input
        args.dilate = dilate
        args.write(self._oprot)
        self._oprot.writeMessageEnd()
        self._oprot.trans.flush()

    def recv_simulate_task_by_id(self):
        iprot = self._iprot
        (fname, mtype, rseqid) = iprot.readMessageBegin()
        if mtype == TMessageType.EXCEPTION:
            x = TApplicationException()
            x.read(iprot)
            iprot.readMessageEnd()
            raise x
        result = simulate_task_by_id_result()
        result.read(iprot)
        iprot.readMessageEnd()
        if result.success is not None:
            return result.success
        raise TApplicationException(TApplicationException.MISSING_RESULT, "simulate_task_by_id failed: unknown result")

    def simulate_task_with_last_input(self, task):
        pass                   
               
           
        self.send_simulate_task_with_last_input(task)
        return self.recv_simulate_task_with_last_input()

    def send_simulate_task_with_last_input(self, task):
        self._oprot.writeMessageBegin('simulate_task_with_last_input', TMessageType.CALL, self._seqid)
        args = simulate_task_with_last_input_args()
        args.task = task
        args.write(self._oprot)
        self._oprot.writeMessageEnd()
        self._oprot.trans.flush()

    def recv_simulate_task_with_last_input(self):
        iprot = self._iprot
        (fname, mtype, rseqid) = iprot.readMessageBegin()
        if mtype == TMessageType.EXCEPTION:
            x = TApplicationException()
            x.read(iprot)
            iprot.readMessageEnd()
            raise x
        result = simulate_task_with_last_input_result()
        result.read(iprot)
        iprot.readMessageEnd()
        if result.success is not None:
            return result.success
        raise TApplicationException(TApplicationException.MISSING_RESULT, "simulate_task_with_last_input failed: unknown result")

    def save_solution(self, task_id, user_input):
        pass                   
                  
                     
           
        self.send_save_solution(task_id, user_input)
        self.recv_save_solution()

    def send_save_solution(self, task_id, user_input):
        self._oprot.writeMessageBegin('save_solution', TMessageType.CALL, self._seqid)
        args = save_solution_args()
        args.task_id = task_id
        args.user_input = user_input
        args.write(self._oprot)
        self._oprot.writeMessageEnd()
        self._oprot.trans.flush()

    def recv_save_solution(self):
        iprot = self._iprot
        (fname, mtype, rseqid) = iprot.readMessageBegin()
        if mtype == TMessageType.EXCEPTION:
            x = TApplicationException()
            x.read(iprot)
            iprot.readMessageEnd()
            raise x
        result = save_solution_result()
        result.read(iprot)
        iprot.readMessageEnd()
        return

    def get_last_input(self):
        self.send_get_last_input()
        return self.recv_get_last_input()

    def send_get_last_input(self):
        self._oprot.writeMessageBegin('get_last_input', TMessageType.CALL, self._seqid)
        args = get_last_input_args()
        args.write(self._oprot)
        self._oprot.writeMessageEnd()
        self._oprot.trans.flush()

    def recv_get_last_input(self):
        iprot = self._iprot
        (fname, mtype, rseqid) = iprot.readMessageBegin()
        if mtype == TMessageType.EXCEPTION:
            x = TApplicationException()
            x.read(iprot)
            iprot.readMessageEnd()
            raise x
        result = get_last_input_result()
        result.read(iprot)
        iprot.readMessageEnd()
        if result.success is not None:
            return result.success
        raise TApplicationException(TApplicationException.MISSING_RESULT, "get_last_input failed: unknown result")

    def get_eval_user_input(self, task_id, tier_name):
        pass                   
                  
                    
           
        self.send_get_eval_user_input(task_id, tier_name)
        return self.recv_get_eval_user_input()

    def send_get_eval_user_input(self, task_id, tier_name):
        self._oprot.writeMessageBegin('get_eval_user_input', TMessageType.CALL, self._seqid)
        args = get_eval_user_input_args()
        args.task_id = task_id
        args.tier_name = tier_name
        args.write(self._oprot)
        self._oprot.writeMessageEnd()
        self._oprot.trans.flush()

    def recv_get_eval_user_input(self):
        iprot = self._iprot
        (fname, mtype, rseqid) = iprot.readMessageBegin()
        if mtype == TMessageType.EXCEPTION:
            x = TApplicationException()
            x.read(iprot)
            iprot.readMessageEnd()
            raise x
        result = get_eval_user_input_result()
        result.read(iprot)
        iprot.readMessageEnd()
        if result.success is not None:
            return result.success
        raise TApplicationException(TApplicationException.MISSING_RESULT, "get_eval_user_input failed: unknown result")

    def render(self, scene):
        pass                   
                
           
        self.send_render(scene)
        return self.recv_render()

    def send_render(self, scene):
        self._oprot.writeMessageBegin('render', TMessageType.CALL, self._seqid)
        args = render_args()
        args.scene = scene
        args.write(self._oprot)
        self._oprot.writeMessageEnd()
        self._oprot.trans.flush()

    def recv_render(self):
        iprot = self._iprot
        (fname, mtype, rseqid) = iprot.readMessageBegin()
        if mtype == TMessageType.EXCEPTION:
            x = TApplicationException()
            x.read(iprot)
            iprot.readMessageEnd()
            raise x
        result = render_result()
        result.read(iprot)
        iprot.readMessageEnd()
        if result.success is not None:
            return result.success
        raise TApplicationException(TApplicationException.MISSING_RESULT, "render failed: unknown result")


class Processor(Iface, TProcessor):
    def __init__(self, handler):
        self._handler = handler
        self._processMap = {}
        self._processMap["list_task_tier_map"] = Processor.process_list_task_tier_map
        self._processMap["load_evaluation_data"] = Processor.process_load_evaluation_data
        self._processMap["get_task_from_id"] = Processor.process_get_task_from_id
        self._processMap["get_task_thumbs"] = Processor.process_get_task_thumbs
        self._processMap["simulate_task_by_id"] = Processor.process_simulate_task_by_id
        self._processMap["simulate_task_with_last_input"] = Processor.process_simulate_task_with_last_input
        self._processMap["save_solution"] = Processor.process_save_solution
        self._processMap["get_last_input"] = Processor.process_get_last_input
        self._processMap["get_eval_user_input"] = Processor.process_get_eval_user_input
        self._processMap["render"] = Processor.process_render

    def process(self, iprot, oprot):
        (name, type, seqid) = iprot.readMessageBegin()
        if name not in self._processMap:
            iprot.skip(TType.STRUCT)
            iprot.readMessageEnd()
            x = TApplicationException(TApplicationException.UNKNOWN_METHOD, 'Unknown function %s' % (name))
            oprot.writeMessageBegin(name, TMessageType.EXCEPTION, seqid)
            x.write(oprot)
            oprot.writeMessageEnd()
            oprot.trans.flush()
            return
        else:
            self._processMap[name](self, seqid, iprot, oprot)
        return True

    def process_list_task_tier_map(self, seqid, iprot, oprot):
        args = list_task_tier_map_args()
        args.read(iprot)
        iprot.readMessageEnd()
        result = list_task_tier_map_result()
        try:
            result.success = self._handler.list_task_tier_map(args.task_id_pattern)
            msg_type = TMessageType.REPLY
        except TTransport.TTransportException:
            raise
        except TApplicationException as ex:
            logging.exception('TApplication exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = ex
        except Exception:
            logging.exception('Unexpected exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = TApplicationException(TApplicationException.INTERNAL_ERROR, 'Internal error')
        oprot.writeMessageBegin("list_task_tier_map", msg_type, seqid)
        result.write(oprot)
        oprot.writeMessageEnd()
        oprot.trans.flush()

    def process_load_evaluation_data(self, seqid, iprot, oprot):
        args = load_evaluation_data_args()
        args.read(iprot)
        iprot.readMessageEnd()
        result = load_evaluation_data_result()
        try:
            result.success = self._handler.load_evaluation_data(args.task_id_pattern)
            msg_type = TMessageType.REPLY
        except TTransport.TTransportException:
            raise
        except TApplicationException as ex:
            logging.exception('TApplication exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = ex
        except Exception:
            logging.exception('Unexpected exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = TApplicationException(TApplicationException.INTERNAL_ERROR, 'Internal error')
        oprot.writeMessageBegin("load_evaluation_data", msg_type, seqid)
        result.write(oprot)
        oprot.writeMessageEnd()
        oprot.trans.flush()

    def process_get_task_from_id(self, seqid, iprot, oprot):
        args = get_task_from_id_args()
        args.read(iprot)
        iprot.readMessageEnd()
        result = get_task_from_id_result()
        try:
            result.success = self._handler.get_task_from_id(args.task_id)
            msg_type = TMessageType.REPLY
        except TTransport.TTransportException:
            raise
        except phyre.interface.shared.ttypes.Error_message as err:
            msg_type = TMessageType.REPLY
            result.err = err
        except TApplicationException as ex:
            logging.exception('TApplication exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = ex
        except Exception:
            logging.exception('Unexpected exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = TApplicationException(TApplicationException.INTERNAL_ERROR, 'Internal error')
        oprot.writeMessageBegin("get_task_from_id", msg_type, seqid)
        result.write(oprot)
        oprot.writeMessageEnd()
        oprot.trans.flush()

    def process_get_task_thumbs(self, seqid, iprot, oprot):
        args = get_task_thumbs_args()
        args.read(iprot)
        iprot.readMessageEnd()
        result = get_task_thumbs_result()
        try:
            result.success = self._handler.get_task_thumbs(args.task_ids)
            msg_type = TMessageType.REPLY
        except TTransport.TTransportException:
            raise
        except TApplicationException as ex:
            logging.exception('TApplication exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = ex
        except Exception:
            logging.exception('Unexpected exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = TApplicationException(TApplicationException.INTERNAL_ERROR, 'Internal error')
        oprot.writeMessageBegin("get_task_thumbs", msg_type, seqid)
        result.write(oprot)
        oprot.writeMessageEnd()
        oprot.trans.flush()

    def process_simulate_task_by_id(self, seqid, iprot, oprot):
        args = simulate_task_by_id_args()
        args.read(iprot)
        iprot.readMessageEnd()
        result = simulate_task_by_id_result()
        try:
            result.success = self._handler.simulate_task_by_id(args.task_id, args.user_input, args.dilate)
            msg_type = TMessageType.REPLY
        except TTransport.TTransportException:
            raise
        except TApplicationException as ex:
            logging.exception('TApplication exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = ex
        except Exception:
            logging.exception('Unexpected exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = TApplicationException(TApplicationException.INTERNAL_ERROR, 'Internal error')
        oprot.writeMessageBegin("simulate_task_by_id", msg_type, seqid)
        result.write(oprot)
        oprot.writeMessageEnd()
        oprot.trans.flush()

    def process_simulate_task_with_last_input(self, seqid, iprot, oprot):
        args = simulate_task_with_last_input_args()
        args.read(iprot)
        iprot.readMessageEnd()
        result = simulate_task_with_last_input_result()
        try:
            result.success = self._handler.simulate_task_with_last_input(args.task)
            msg_type = TMessageType.REPLY
        except TTransport.TTransportException:
            raise
        except TApplicationException as ex:
            logging.exception('TApplication exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = ex
        except Exception:
            logging.exception('Unexpected exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = TApplicationException(TApplicationException.INTERNAL_ERROR, 'Internal error')
        oprot.writeMessageBegin("simulate_task_with_last_input", msg_type, seqid)
        result.write(oprot)
        oprot.writeMessageEnd()
        oprot.trans.flush()

    def process_save_solution(self, seqid, iprot, oprot):
        args = save_solution_args()
        args.read(iprot)
        iprot.readMessageEnd()
        result = save_solution_result()
        try:
            self._handler.save_solution(args.task_id, args.user_input)
            msg_type = TMessageType.REPLY
        except TTransport.TTransportException:
            raise
        except TApplicationException as ex:
            logging.exception('TApplication exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = ex
        except Exception:
            logging.exception('Unexpected exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = TApplicationException(TApplicationException.INTERNAL_ERROR, 'Internal error')
        oprot.writeMessageBegin("save_solution", msg_type, seqid)
        result.write(oprot)
        oprot.writeMessageEnd()
        oprot.trans.flush()

    def process_get_last_input(self, seqid, iprot, oprot):
        args = get_last_input_args()
        args.read(iprot)
        iprot.readMessageEnd()
        result = get_last_input_result()
        try:
            result.success = self._handler.get_last_input()
            msg_type = TMessageType.REPLY
        except TTransport.TTransportException:
            raise
        except TApplicationException as ex:
            logging.exception('TApplication exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = ex
        except Exception:
            logging.exception('Unexpected exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = TApplicationException(TApplicationException.INTERNAL_ERROR, 'Internal error')
        oprot.writeMessageBegin("get_last_input", msg_type, seqid)
        result.write(oprot)
        oprot.writeMessageEnd()
        oprot.trans.flush()

    def process_get_eval_user_input(self, seqid, iprot, oprot):
        args = get_eval_user_input_args()
        args.read(iprot)
        iprot.readMessageEnd()
        result = get_eval_user_input_result()
        try:
            result.success = self._handler.get_eval_user_input(args.task_id, args.tier_name)
            msg_type = TMessageType.REPLY
        except TTransport.TTransportException:
            raise
        except TApplicationException as ex:
            logging.exception('TApplication exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = ex
        except Exception:
            logging.exception('Unexpected exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = TApplicationException(TApplicationException.INTERNAL_ERROR, 'Internal error')
        oprot.writeMessageBegin("get_eval_user_input", msg_type, seqid)
        result.write(oprot)
        oprot.writeMessageEnd()
        oprot.trans.flush()

    def process_render(self, seqid, iprot, oprot):
        args = render_args()
        args.read(iprot)
        iprot.readMessageEnd()
        result = render_result()
        try:
            result.success = self._handler.render(args.scene)
            msg_type = TMessageType.REPLY
        except TTransport.TTransportException:
            raise
        except TApplicationException as ex:
            logging.exception('TApplication exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = ex
        except Exception:
            logging.exception('Unexpected exception in handler')
            msg_type = TMessageType.EXCEPTION
            result = TApplicationException(TApplicationException.INTERNAL_ERROR, 'Internal error')
        oprot.writeMessageBegin("render", msg_type, seqid)
        result.write(oprot)
        oprot.writeMessageEnd()
        oprot.trans.flush()

                                 


class list_task_tier_map_args(object):
    pass               
                      
       


    def __init__(self, task_id_pattern=None,):
        self.task_id_pattern = task_id_pattern

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
                    self.task_id_pattern = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
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
        oprot.writeStructBegin('list_task_tier_map_args')
        if self.task_id_pattern is not None:
            oprot.writeFieldBegin('task_id_pattern', TType.STRING, 1)
            oprot.writeString(self.task_id_pattern.encode('utf-8') if sys.version_info[0] == 2 else self.task_id_pattern)
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
all_structs.append(list_task_tier_map_args)
list_task_tier_map_args.thrift_spec = (
    None,     
    (1, TType.STRING, 'task_id_pattern', 'UTF8', None, ),     
)


class list_task_tier_map_result(object):
    pass               
              
       


    def __init__(self, success=None,):
        self.success = success

    def read(self, iprot):
        if iprot._fast_decode is not None and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None:
            iprot._fast_decode(self, iprot, [self.__class__, self.thrift_spec])
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 0:
                if ftype == TType.MAP:
                    self.success = {}
                    (_ktype50, _vtype51, _size49) = iprot.readMapBegin()
                    for _i53 in range(_size49):
                        _key54 = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                        _val55 = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                        self.success[_key54] = _val55
                    iprot.readMapEnd()
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
        oprot.writeStructBegin('list_task_tier_map_result')
        if self.success is not None:
            oprot.writeFieldBegin('success', TType.MAP, 0)
            oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.success))
            for kiter56, viter57 in self.success.items():
                oprot.writeString(kiter56.encode('utf-8') if sys.version_info[0] == 2 else kiter56)
                oprot.writeString(viter57.encode('utf-8') if sys.version_info[0] == 2 else viter57)
            oprot.writeMapEnd()
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
all_structs.append(list_task_tier_map_result)
list_task_tier_map_result.thrift_spec = (
    (0, TType.MAP, 'success', (TType.STRING, 'UTF8', TType.STRING, 'UTF8', False), None, ),     
)


class load_evaluation_data_args(object):
    pass               
                      
       


    def __init__(self, task_id_pattern=None,):
        self.task_id_pattern = task_id_pattern

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
                    self.task_id_pattern = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
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
        oprot.writeStructBegin('load_evaluation_data_args')
        if self.task_id_pattern is not None:
            oprot.writeFieldBegin('task_id_pattern', TType.STRING, 1)
            oprot.writeString(self.task_id_pattern.encode('utf-8') if sys.version_info[0] == 2 else self.task_id_pattern)
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
all_structs.append(load_evaluation_data_args)
load_evaluation_data_args.thrift_spec = (
    None,     
    (1, TType.STRING, 'task_id_pattern', 'UTF8', None, ),     
)


class load_evaluation_data_result(object):
    pass               
              
       


    def __init__(self, success=None,):
        self.success = success

    def read(self, iprot):
        if iprot._fast_decode is not None and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None:
            iprot._fast_decode(self, iprot, [self.__class__, self.thrift_spec])
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 0:
                if ftype == TType.MAP:
                    self.success = {}
                    (_ktype59, _vtype60, _size58) = iprot.readMapBegin()
                    for _i62 in range(_size58):
                        _key63 = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                        _val64 = EvalData()
                        _val64.read(iprot)
                        self.success[_key63] = _val64
                    iprot.readMapEnd()
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
        oprot.writeStructBegin('load_evaluation_data_result')
        if self.success is not None:
            oprot.writeFieldBegin('success', TType.MAP, 0)
            oprot.writeMapBegin(TType.STRING, TType.STRUCT, len(self.success))
            for kiter65, viter66 in self.success.items():
                oprot.writeString(kiter65.encode('utf-8') if sys.version_info[0] == 2 else kiter65)
                viter66.write(oprot)
            oprot.writeMapEnd()
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
all_structs.append(load_evaluation_data_result)
load_evaluation_data_result.thrift_spec = (
    (0, TType.MAP, 'success', (TType.STRING, 'UTF8', TType.STRUCT, [EvalData, None], False), None, ),     
)


class get_task_from_id_args(object):
    pass               
              
       


    def __init__(self, task_id=None,):
        self.task_id = task_id

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
                    self.task_id = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
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
        oprot.writeStructBegin('get_task_from_id_args')
        if self.task_id is not None:
            oprot.writeFieldBegin('task_id', TType.STRING, 1)
            oprot.writeString(self.task_id.encode('utf-8') if sys.version_info[0] == 2 else self.task_id)
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
all_structs.append(get_task_from_id_args)
get_task_from_id_args.thrift_spec = (
    None,     
    (1, TType.STRING, 'task_id', 'UTF8', None, ),     
)


class get_task_from_id_result(object):
    pass               
              
          
       


    def __init__(self, success=None, err=None,):
        self.success = success
        self.err = err

    def read(self, iprot):
        if iprot._fast_decode is not None and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None:
            iprot._fast_decode(self, iprot, [self.__class__, self.thrift_spec])
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 0:
                if ftype == TType.STRUCT:
                    self.success = TaskWithMeta()
                    self.success.read(iprot)
                else:
                    iprot.skip(ftype)
            elif fid == 1:
                if ftype == TType.STRUCT:
                    self.err = phyre.interface.shared.ttypes.Error_message()
                    self.err.read(iprot)
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
        oprot.writeStructBegin('get_task_from_id_result')
        if self.success is not None:
            oprot.writeFieldBegin('success', TType.STRUCT, 0)
            self.success.write(oprot)
            oprot.writeFieldEnd()
        if self.err is not None:
            oprot.writeFieldBegin('err', TType.STRUCT, 1)
            self.err.write(oprot)
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
all_structs.append(get_task_from_id_result)
get_task_from_id_result.thrift_spec = (
    (0, TType.STRUCT, 'success', [TaskWithMeta, None], None, ),     
    (1, TType.STRUCT, 'err', [phyre.interface.shared.ttypes.Error_message, None], None, ),     
)


class get_task_thumbs_args(object):
    pass               
               
       


    def __init__(self, task_ids=None,):
        self.task_ids = task_ids

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
                    self.task_ids = []
                    (_etype70, _size67) = iprot.readListBegin()
                    for _i71 in range(_size67):
                        _elem72 = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                        self.task_ids.append(_elem72)
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
        oprot.writeStructBegin('get_task_thumbs_args')
        if self.task_ids is not None:
            oprot.writeFieldBegin('task_ids', TType.LIST, 1)
            oprot.writeListBegin(TType.STRING, len(self.task_ids))
            for iter73 in self.task_ids:
                oprot.writeString(iter73.encode('utf-8') if sys.version_info[0] == 2 else iter73)
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
all_structs.append(get_task_thumbs_args)
get_task_thumbs_args.thrift_spec = (
    None,     
    (1, TType.LIST, 'task_ids', (TType.STRING, 'UTF8', False), None, ),     
)


class get_task_thumbs_result(object):
    pass               
              
       


    def __init__(self, success=None,):
        self.success = success

    def read(self, iprot):
        if iprot._fast_decode is not None and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None:
            iprot._fast_decode(self, iprot, [self.__class__, self.thrift_spec])
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 0:
                if ftype == TType.LIST:
                    self.success = []
                    (_etype77, _size74) = iprot.readListBegin()
                    for _i78 in range(_size74):
                        _elem79 = Thumb()
                        _elem79.read(iprot)
                        self.success.append(_elem79)
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
        oprot.writeStructBegin('get_task_thumbs_result')
        if self.success is not None:
            oprot.writeFieldBegin('success', TType.LIST, 0)
            oprot.writeListBegin(TType.STRUCT, len(self.success))
            for iter80 in self.success:
                iter80.write(oprot)
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
all_structs.append(get_task_thumbs_result)
get_task_thumbs_result.thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT, [Thumb, None], False), None, ),     
)


class simulate_task_by_id_args(object):
    pass               
              
                 
             
       


    def __init__(self, task_id=None, user_input=None, dilate=None,):
        self.task_id = task_id
        self.user_input = user_input
        self.dilate = dilate

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
                    self.task_id = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.STRUCT:
                    self.user_input = phyre.interface.scene.ttypes.UserInput()
                    self.user_input.read(iprot)
                else:
                    iprot.skip(ftype)
            elif fid == 3:
                if ftype == TType.BOOL:
                    self.dilate = iprot.readBool()
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
        oprot.writeStructBegin('simulate_task_by_id_args')
        if self.task_id is not None:
            oprot.writeFieldBegin('task_id', TType.STRING, 1)
            oprot.writeString(self.task_id.encode('utf-8') if sys.version_info[0] == 2 else self.task_id)
            oprot.writeFieldEnd()
        if self.user_input is not None:
            oprot.writeFieldBegin('user_input', TType.STRUCT, 2)
            self.user_input.write(oprot)
            oprot.writeFieldEnd()
        if self.dilate is not None:
            oprot.writeFieldBegin('dilate', TType.BOOL, 3)
            oprot.writeBool(self.dilate)
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
all_structs.append(simulate_task_by_id_args)
simulate_task_by_id_args.thrift_spec = (
    None,     
    (1, TType.STRING, 'task_id', 'UTF8', None, ),     
    (2, TType.STRUCT, 'user_input', [phyre.interface.scene.ttypes.UserInput, None], None, ),     
    (3, TType.BOOL, 'dilate', None, None, ),     
)


class simulate_task_by_id_result(object):
    pass               
              
       


    def __init__(self, success=None,):
        self.success = success

    def read(self, iprot):
        if iprot._fast_decode is not None and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None:
            iprot._fast_decode(self, iprot, [self.__class__, self.thrift_spec])
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 0:
                if ftype == TType.STRUCT:
                    self.success = TaskSimulationWithMeta()
                    self.success.read(iprot)
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
        oprot.writeStructBegin('simulate_task_by_id_result')
        if self.success is not None:
            oprot.writeFieldBegin('success', TType.STRUCT, 0)
            self.success.write(oprot)
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
all_structs.append(simulate_task_by_id_result)
simulate_task_by_id_result.thrift_spec = (
    (0, TType.STRUCT, 'success', [TaskSimulationWithMeta, None], None, ),     
)


class simulate_task_with_last_input_args(object):
    pass               
           
       


    def __init__(self, task=None,):
        self.task = task

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
            else:
                iprot.skip(ftype)
            iprot.readFieldEnd()
        iprot.readStructEnd()

    def write(self, oprot):
        if oprot._fast_encode is not None and self.thrift_spec is not None:
            oprot.trans.write(oprot._fast_encode(self, [self.__class__, self.thrift_spec]))
            return
        oprot.writeStructBegin('simulate_task_with_last_input_args')
        if self.task is not None:
            oprot.writeFieldBegin('task', TType.STRUCT, 1)
            self.task.write(oprot)
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
all_structs.append(simulate_task_with_last_input_args)
simulate_task_with_last_input_args.thrift_spec = (
    None,     
    (1, TType.STRUCT, 'task', [Task, None], None, ),     
)


class simulate_task_with_last_input_result(object):
    pass               
              
       


    def __init__(self, success=None,):
        self.success = success

    def read(self, iprot):
        if iprot._fast_decode is not None and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None:
            iprot._fast_decode(self, iprot, [self.__class__, self.thrift_spec])
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 0:
                if ftype == TType.STRUCT:
                    self.success = TaskSimulationWithMeta()
                    self.success.read(iprot)
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
        oprot.writeStructBegin('simulate_task_with_last_input_result')
        if self.success is not None:
            oprot.writeFieldBegin('success', TType.STRUCT, 0)
            self.success.write(oprot)
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
all_structs.append(simulate_task_with_last_input_result)
simulate_task_with_last_input_result.thrift_spec = (
    (0, TType.STRUCT, 'success', [TaskSimulationWithMeta, None], None, ),     
)


class save_solution_args(object):
    pass               
              
                 
       


    def __init__(self, task_id=None, user_input=None,):
        self.task_id = task_id
        self.user_input = user_input

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
                    self.task_id = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.STRUCT:
                    self.user_input = phyre.interface.scene.ttypes.UserInput()
                    self.user_input.read(iprot)
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
        oprot.writeStructBegin('save_solution_args')
        if self.task_id is not None:
            oprot.writeFieldBegin('task_id', TType.STRING, 1)
            oprot.writeString(self.task_id.encode('utf-8') if sys.version_info[0] == 2 else self.task_id)
            oprot.writeFieldEnd()
        if self.user_input is not None:
            oprot.writeFieldBegin('user_input', TType.STRUCT, 2)
            self.user_input.write(oprot)
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
all_structs.append(save_solution_args)
save_solution_args.thrift_spec = (
    None,     
    (1, TType.STRING, 'task_id', 'UTF8', None, ),     
    (2, TType.STRUCT, 'user_input', [phyre.interface.scene.ttypes.UserInput, None], None, ),     
)


class save_solution_result(object):


    def read(self, iprot):
        if iprot._fast_decode is not None and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None:
            iprot._fast_decode(self, iprot, [self.__class__, self.thrift_spec])
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            else:
                iprot.skip(ftype)
            iprot.readFieldEnd()
        iprot.readStructEnd()

    def write(self, oprot):
        if oprot._fast_encode is not None and self.thrift_spec is not None:
            oprot.trans.write(oprot._fast_encode(self, [self.__class__, self.thrift_spec]))
            return
        oprot.writeStructBegin('save_solution_result')
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
all_structs.append(save_solution_result)
save_solution_result.thrift_spec = (
)


class get_last_input_args(object):


    def read(self, iprot):
        if iprot._fast_decode is not None and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None:
            iprot._fast_decode(self, iprot, [self.__class__, self.thrift_spec])
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            else:
                iprot.skip(ftype)
            iprot.readFieldEnd()
        iprot.readStructEnd()

    def write(self, oprot):
        if oprot._fast_encode is not None and self.thrift_spec is not None:
            oprot.trans.write(oprot._fast_encode(self, [self.__class__, self.thrift_spec]))
            return
        oprot.writeStructBegin('get_last_input_args')
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
all_structs.append(get_last_input_args)
get_last_input_args.thrift_spec = (
)


class get_last_input_result(object):
    pass               
              
       


    def __init__(self, success=None,):
        self.success = success

    def read(self, iprot):
        if iprot._fast_decode is not None and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None:
            iprot._fast_decode(self, iprot, [self.__class__, self.thrift_spec])
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 0:
                if ftype == TType.STRUCT:
                    self.success = phyre.interface.scene.ttypes.UserInput()
                    self.success.read(iprot)
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
        oprot.writeStructBegin('get_last_input_result')
        if self.success is not None:
            oprot.writeFieldBegin('success', TType.STRUCT, 0)
            self.success.write(oprot)
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
all_structs.append(get_last_input_result)
get_last_input_result.thrift_spec = (
    (0, TType.STRUCT, 'success', [phyre.interface.scene.ttypes.UserInput, None], None, ),     
)


class get_eval_user_input_args(object):
    pass               
              
                
       


    def __init__(self, task_id=None, tier_name=None,):
        self.task_id = task_id
        self.tier_name = tier_name

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
                    self.task_id = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.STRING:
                    self.tier_name = iprot.readString().decode('utf-8') if sys.version_info[0] == 2 else iprot.readString()
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
        oprot.writeStructBegin('get_eval_user_input_args')
        if self.task_id is not None:
            oprot.writeFieldBegin('task_id', TType.STRING, 1)
            oprot.writeString(self.task_id.encode('utf-8') if sys.version_info[0] == 2 else self.task_id)
            oprot.writeFieldEnd()
        if self.tier_name is not None:
            oprot.writeFieldBegin('tier_name', TType.STRING, 2)
            oprot.writeString(self.tier_name.encode('utf-8') if sys.version_info[0] == 2 else self.tier_name)
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
all_structs.append(get_eval_user_input_args)
get_eval_user_input_args.thrift_spec = (
    None,     
    (1, TType.STRING, 'task_id', 'UTF8', None, ),     
    (2, TType.STRING, 'tier_name', 'UTF8', None, ),     
)


class get_eval_user_input_result(object):
    pass               
              
       


    def __init__(self, success=None,):
        self.success = success

    def read(self, iprot):
        if iprot._fast_decode is not None and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None:
            iprot._fast_decode(self, iprot, [self.__class__, self.thrift_spec])
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 0:
                if ftype == TType.STRUCT:
                    self.success = phyre.interface.scene.ttypes.UserInput()
                    self.success.read(iprot)
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
        oprot.writeStructBegin('get_eval_user_input_result')
        if self.success is not None:
            oprot.writeFieldBegin('success', TType.STRUCT, 0)
            self.success.write(oprot)
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
all_structs.append(get_eval_user_input_result)
get_eval_user_input_result.thrift_spec = (
    (0, TType.STRUCT, 'success', [phyre.interface.scene.ttypes.UserInput, None], None, ),     
)


class render_args(object):
    pass               
            
       


    def __init__(self, scene=None,):
        self.scene = scene

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
                    self.scene = phyre.interface.scene.ttypes.Scene()
                    self.scene.read(iprot)
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
        oprot.writeStructBegin('render_args')
        if self.scene is not None:
            oprot.writeFieldBegin('scene', TType.STRUCT, 1)
            self.scene.write(oprot)
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
all_structs.append(render_args)
render_args.thrift_spec = (
    None,     
    (1, TType.STRUCT, 'scene', [phyre.interface.scene.ttypes.Scene, None], None, ),     
)


class render_result(object):
    pass               
              
       


    def __init__(self, success=None,):
        self.success = success

    def read(self, iprot):
        if iprot._fast_decode is not None and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None:
            iprot._fast_decode(self, iprot, [self.__class__, self.thrift_spec])
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 0:
                if ftype == TType.STRUCT:
                    self.success = phyre.interface.scene.ttypes.Image()
                    self.success.read(iprot)
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
        oprot.writeStructBegin('render_result')
        if self.success is not None:
            oprot.writeFieldBegin('success', TType.STRUCT, 0)
            self.success.write(oprot)
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
all_structs.append(render_result)
render_result.thrift_spec = (
    (0, TType.STRUCT, 'success', [phyre.interface.scene.ttypes.Image, None], None, ),     
)
fix_spec(all_structs)
del all_structs

