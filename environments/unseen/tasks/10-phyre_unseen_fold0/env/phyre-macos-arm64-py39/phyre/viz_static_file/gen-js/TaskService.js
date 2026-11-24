  
                                            
  
                                                                   
  


                                 

TaskService_list_task_tier_map_args = function(args) {
  this.task_id_pattern = null;
  if (args) {
    if (args.task_id_pattern !== undefined && args.task_id_pattern !== null) {
      this.task_id_pattern = args.task_id_pattern;
    }
  }
};
TaskService_list_task_tier_map_args.prototype = {};
TaskService_list_task_tier_map_args.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 1:
      if (ftype == Thrift.Type.STRING) {
        this.task_id_pattern = input.readString().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 0:
        input.skip(ftype);
        break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_list_task_tier_map_args.prototype.write = function(output) {
  output.writeStructBegin('TaskService_list_task_tier_map_args');
  if (this.task_id_pattern !== null && this.task_id_pattern !== undefined) {
    output.writeFieldBegin('task_id_pattern', Thrift.Type.STRING, 1);
    output.writeString(this.task_id_pattern);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_list_task_tier_map_result = function(args) {
  this.success = null;
  if (args) {
    if (args.success !== undefined && args.success !== null) {
      this.success = Thrift.copyMap(args.success, [null]);
    }
  }
};
TaskService_list_task_tier_map_result.prototype = {};
TaskService_list_task_tier_map_result.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 0:
      if (ftype == Thrift.Type.MAP) {
        var _size56 = 0;
        var _rtmp360;
        this.success = {};
        var _ktype57 = 0;
        var _vtype58 = 0;
        _rtmp360 = input.readMapBegin();
        _ktype57 = _rtmp360.ktype;
        _vtype58 = _rtmp360.vtype;
        _size56 = _rtmp360.size;
        for (var _i61 = 0; _i61 < _size56; ++_i61)
        {
          if (_i61 > 0 ) {
            if (input.rstack.length > input.rpos[input.rpos.length -1] + 1) {
              input.rstack.pop();
            }
          }
          var key62 = null;
          var val63 = null;
          key62 = input.readString().value;
          val63 = input.readString().value;
          this.success[key62] = val63;
        }
        input.readMapEnd();
      } else {
        input.skip(ftype);
      }
      break;
      case 0:
        input.skip(ftype);
        break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_list_task_tier_map_result.prototype.write = function(output) {
  output.writeStructBegin('TaskService_list_task_tier_map_result');
  if (this.success !== null && this.success !== undefined) {
    output.writeFieldBegin('success', Thrift.Type.MAP, 0);
    output.writeMapBegin(Thrift.Type.STRING, Thrift.Type.STRING, Thrift.objectLength(this.success));
    for (var kiter64 in this.success)
    {
      if (this.success.hasOwnProperty(kiter64))
      {
        var viter65 = this.success[kiter64];
        output.writeString(kiter64);
        output.writeString(viter65);
      }
    }
    output.writeMapEnd();
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_load_evaluation_data_args = function(args) {
  this.task_id_pattern = null;
  if (args) {
    if (args.task_id_pattern !== undefined && args.task_id_pattern !== null) {
      this.task_id_pattern = args.task_id_pattern;
    }
  }
};
TaskService_load_evaluation_data_args.prototype = {};
TaskService_load_evaluation_data_args.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 1:
      if (ftype == Thrift.Type.STRING) {
        this.task_id_pattern = input.readString().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 0:
        input.skip(ftype);
        break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_load_evaluation_data_args.prototype.write = function(output) {
  output.writeStructBegin('TaskService_load_evaluation_data_args');
  if (this.task_id_pattern !== null && this.task_id_pattern !== undefined) {
    output.writeFieldBegin('task_id_pattern', Thrift.Type.STRING, 1);
    output.writeString(this.task_id_pattern);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_load_evaluation_data_result = function(args) {
  this.success = null;
  if (args) {
    if (args.success !== undefined && args.success !== null) {
      this.success = Thrift.copyMap(args.success, [EvalData]);
    }
  }
};
TaskService_load_evaluation_data_result.prototype = {};
TaskService_load_evaluation_data_result.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 0:
      if (ftype == Thrift.Type.MAP) {
        var _size66 = 0;
        var _rtmp370;
        this.success = {};
        var _ktype67 = 0;
        var _vtype68 = 0;
        _rtmp370 = input.readMapBegin();
        _ktype67 = _rtmp370.ktype;
        _vtype68 = _rtmp370.vtype;
        _size66 = _rtmp370.size;
        for (var _i71 = 0; _i71 < _size66; ++_i71)
        {
          if (_i71 > 0 ) {
            if (input.rstack.length > input.rpos[input.rpos.length -1] + 1) {
              input.rstack.pop();
            }
          }
          var key72 = null;
          var val73 = null;
          key72 = input.readString().value;
          val73 = new EvalData();
          val73.read(input);
          this.success[key72] = val73;
        }
        input.readMapEnd();
      } else {
        input.skip(ftype);
      }
      break;
      case 0:
        input.skip(ftype);
        break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_load_evaluation_data_result.prototype.write = function(output) {
  output.writeStructBegin('TaskService_load_evaluation_data_result');
  if (this.success !== null && this.success !== undefined) {
    output.writeFieldBegin('success', Thrift.Type.MAP, 0);
    output.writeMapBegin(Thrift.Type.STRING, Thrift.Type.STRUCT, Thrift.objectLength(this.success));
    for (var kiter74 in this.success)
    {
      if (this.success.hasOwnProperty(kiter74))
      {
        var viter75 = this.success[kiter74];
        output.writeString(kiter74);
        viter75.write(output);
      }
    }
    output.writeMapEnd();
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_get_task_from_id_args = function(args) {
  this.task_id = null;
  if (args) {
    if (args.task_id !== undefined && args.task_id !== null) {
      this.task_id = args.task_id;
    }
  }
};
TaskService_get_task_from_id_args.prototype = {};
TaskService_get_task_from_id_args.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 1:
      if (ftype == Thrift.Type.STRING) {
        this.task_id = input.readString().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 0:
        input.skip(ftype);
        break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_get_task_from_id_args.prototype.write = function(output) {
  output.writeStructBegin('TaskService_get_task_from_id_args');
  if (this.task_id !== null && this.task_id !== undefined) {
    output.writeFieldBegin('task_id', Thrift.Type.STRING, 1);
    output.writeString(this.task_id);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_get_task_from_id_result = function(args) {
  this.success = null;
  this.err = null;
  if (args instanceof Error_message) {
    this.err = args;
    return;
  }
  if (args) {
    if (args.success !== undefined && args.success !== null) {
      this.success = new TaskWithMeta(args.success);
    }
    if (args.err !== undefined && args.err !== null) {
      this.err = args.err;
    }
  }
};
TaskService_get_task_from_id_result.prototype = {};
TaskService_get_task_from_id_result.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 0:
      if (ftype == Thrift.Type.STRUCT) {
        this.success = new TaskWithMeta();
        this.success.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 1:
      if (ftype == Thrift.Type.STRUCT) {
        this.err = new Error_message();
        this.err.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_get_task_from_id_result.prototype.write = function(output) {
  output.writeStructBegin('TaskService_get_task_from_id_result');
  if (this.success !== null && this.success !== undefined) {
    output.writeFieldBegin('success', Thrift.Type.STRUCT, 0);
    this.success.write(output);
    output.writeFieldEnd();
  }
  if (this.err !== null && this.err !== undefined) {
    output.writeFieldBegin('err', Thrift.Type.STRUCT, 1);
    this.err.write(output);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_get_task_thumbs_args = function(args) {
  this.task_ids = null;
  if (args) {
    if (args.task_ids !== undefined && args.task_ids !== null) {
      this.task_ids = Thrift.copyList(args.task_ids, [null]);
    }
  }
};
TaskService_get_task_thumbs_args.prototype = {};
TaskService_get_task_thumbs_args.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 1:
      if (ftype == Thrift.Type.LIST) {
        var _size76 = 0;
        var _rtmp380;
        this.task_ids = [];
        var _etype79 = 0;
        _rtmp380 = input.readListBegin();
        _etype79 = _rtmp380.etype;
        _size76 = _rtmp380.size;
        for (var _i81 = 0; _i81 < _size76; ++_i81)
        {
          var elem82 = null;
          elem82 = input.readString().value;
          this.task_ids.push(elem82);
        }
        input.readListEnd();
      } else {
        input.skip(ftype);
      }
      break;
      case 0:
        input.skip(ftype);
        break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_get_task_thumbs_args.prototype.write = function(output) {
  output.writeStructBegin('TaskService_get_task_thumbs_args');
  if (this.task_ids !== null && this.task_ids !== undefined) {
    output.writeFieldBegin('task_ids', Thrift.Type.LIST, 1);
    output.writeListBegin(Thrift.Type.STRING, this.task_ids.length);
    for (var iter83 in this.task_ids)
    {
      if (this.task_ids.hasOwnProperty(iter83))
      {
        iter83 = this.task_ids[iter83];
        output.writeString(iter83);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_get_task_thumbs_result = function(args) {
  this.success = null;
  if (args) {
    if (args.success !== undefined && args.success !== null) {
      this.success = Thrift.copyList(args.success, [Thumb]);
    }
  }
};
TaskService_get_task_thumbs_result.prototype = {};
TaskService_get_task_thumbs_result.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 0:
      if (ftype == Thrift.Type.LIST) {
        var _size84 = 0;
        var _rtmp388;
        this.success = [];
        var _etype87 = 0;
        _rtmp388 = input.readListBegin();
        _etype87 = _rtmp388.etype;
        _size84 = _rtmp388.size;
        for (var _i89 = 0; _i89 < _size84; ++_i89)
        {
          var elem90 = null;
          elem90 = new Thumb();
          elem90.read(input);
          this.success.push(elem90);
        }
        input.readListEnd();
      } else {
        input.skip(ftype);
      }
      break;
      case 0:
        input.skip(ftype);
        break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_get_task_thumbs_result.prototype.write = function(output) {
  output.writeStructBegin('TaskService_get_task_thumbs_result');
  if (this.success !== null && this.success !== undefined) {
    output.writeFieldBegin('success', Thrift.Type.LIST, 0);
    output.writeListBegin(Thrift.Type.STRUCT, this.success.length);
    for (var iter91 in this.success)
    {
      if (this.success.hasOwnProperty(iter91))
      {
        iter91 = this.success[iter91];
        iter91.write(output);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_simulate_task_by_id_args = function(args) {
  this.task_id = null;
  this.user_input = null;
  this.dilate = null;
  if (args) {
    if (args.task_id !== undefined && args.task_id !== null) {
      this.task_id = args.task_id;
    }
    if (args.user_input !== undefined && args.user_input !== null) {
      this.user_input = new UserInput(args.user_input);
    }
    if (args.dilate !== undefined && args.dilate !== null) {
      this.dilate = args.dilate;
    }
  }
};
TaskService_simulate_task_by_id_args.prototype = {};
TaskService_simulate_task_by_id_args.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 1:
      if (ftype == Thrift.Type.STRING) {
        this.task_id = input.readString().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.STRUCT) {
        this.user_input = new UserInput();
        this.user_input.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 3:
      if (ftype == Thrift.Type.BOOL) {
        this.dilate = input.readBool().value;
      } else {
        input.skip(ftype);
      }
      break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_simulate_task_by_id_args.prototype.write = function(output) {
  output.writeStructBegin('TaskService_simulate_task_by_id_args');
  if (this.task_id !== null && this.task_id !== undefined) {
    output.writeFieldBegin('task_id', Thrift.Type.STRING, 1);
    output.writeString(this.task_id);
    output.writeFieldEnd();
  }
  if (this.user_input !== null && this.user_input !== undefined) {
    output.writeFieldBegin('user_input', Thrift.Type.STRUCT, 2);
    this.user_input.write(output);
    output.writeFieldEnd();
  }
  if (this.dilate !== null && this.dilate !== undefined) {
    output.writeFieldBegin('dilate', Thrift.Type.BOOL, 3);
    output.writeBool(this.dilate);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_simulate_task_by_id_result = function(args) {
  this.success = null;
  if (args) {
    if (args.success !== undefined && args.success !== null) {
      this.success = new TaskSimulationWithMeta(args.success);
    }
  }
};
TaskService_simulate_task_by_id_result.prototype = {};
TaskService_simulate_task_by_id_result.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 0:
      if (ftype == Thrift.Type.STRUCT) {
        this.success = new TaskSimulationWithMeta();
        this.success.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 0:
        input.skip(ftype);
        break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_simulate_task_by_id_result.prototype.write = function(output) {
  output.writeStructBegin('TaskService_simulate_task_by_id_result');
  if (this.success !== null && this.success !== undefined) {
    output.writeFieldBegin('success', Thrift.Type.STRUCT, 0);
    this.success.write(output);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_simulate_task_with_last_input_args = function(args) {
  this.task = null;
  if (args) {
    if (args.task !== undefined && args.task !== null) {
      this.task = new Task(args.task);
    }
  }
};
TaskService_simulate_task_with_last_input_args.prototype = {};
TaskService_simulate_task_with_last_input_args.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 1:
      if (ftype == Thrift.Type.STRUCT) {
        this.task = new Task();
        this.task.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 0:
        input.skip(ftype);
        break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_simulate_task_with_last_input_args.prototype.write = function(output) {
  output.writeStructBegin('TaskService_simulate_task_with_last_input_args');
  if (this.task !== null && this.task !== undefined) {
    output.writeFieldBegin('task', Thrift.Type.STRUCT, 1);
    this.task.write(output);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_simulate_task_with_last_input_result = function(args) {
  this.success = null;
  if (args) {
    if (args.success !== undefined && args.success !== null) {
      this.success = new TaskSimulationWithMeta(args.success);
    }
  }
};
TaskService_simulate_task_with_last_input_result.prototype = {};
TaskService_simulate_task_with_last_input_result.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 0:
      if (ftype == Thrift.Type.STRUCT) {
        this.success = new TaskSimulationWithMeta();
        this.success.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 0:
        input.skip(ftype);
        break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_simulate_task_with_last_input_result.prototype.write = function(output) {
  output.writeStructBegin('TaskService_simulate_task_with_last_input_result');
  if (this.success !== null && this.success !== undefined) {
    output.writeFieldBegin('success', Thrift.Type.STRUCT, 0);
    this.success.write(output);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_save_solution_args = function(args) {
  this.task_id = null;
  this.user_input = null;
  if (args) {
    if (args.task_id !== undefined && args.task_id !== null) {
      this.task_id = args.task_id;
    }
    if (args.user_input !== undefined && args.user_input !== null) {
      this.user_input = new UserInput(args.user_input);
    }
  }
};
TaskService_save_solution_args.prototype = {};
TaskService_save_solution_args.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 1:
      if (ftype == Thrift.Type.STRING) {
        this.task_id = input.readString().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.STRUCT) {
        this.user_input = new UserInput();
        this.user_input.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_save_solution_args.prototype.write = function(output) {
  output.writeStructBegin('TaskService_save_solution_args');
  if (this.task_id !== null && this.task_id !== undefined) {
    output.writeFieldBegin('task_id', Thrift.Type.STRING, 1);
    output.writeString(this.task_id);
    output.writeFieldEnd();
  }
  if (this.user_input !== null && this.user_input !== undefined) {
    output.writeFieldBegin('user_input', Thrift.Type.STRUCT, 2);
    this.user_input.write(output);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_save_solution_result = function(args) {
};
TaskService_save_solution_result.prototype = {};
TaskService_save_solution_result.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    input.skip(ftype);
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_save_solution_result.prototype.write = function(output) {
  output.writeStructBegin('TaskService_save_solution_result');
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_get_last_input_args = function(args) {
};
TaskService_get_last_input_args.prototype = {};
TaskService_get_last_input_args.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    input.skip(ftype);
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_get_last_input_args.prototype.write = function(output) {
  output.writeStructBegin('TaskService_get_last_input_args');
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_get_last_input_result = function(args) {
  this.success = null;
  if (args) {
    if (args.success !== undefined && args.success !== null) {
      this.success = new UserInput(args.success);
    }
  }
};
TaskService_get_last_input_result.prototype = {};
TaskService_get_last_input_result.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 0:
      if (ftype == Thrift.Type.STRUCT) {
        this.success = new UserInput();
        this.success.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 0:
        input.skip(ftype);
        break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_get_last_input_result.prototype.write = function(output) {
  output.writeStructBegin('TaskService_get_last_input_result');
  if (this.success !== null && this.success !== undefined) {
    output.writeFieldBegin('success', Thrift.Type.STRUCT, 0);
    this.success.write(output);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_get_eval_user_input_args = function(args) {
  this.task_id = null;
  this.tier_name = null;
  if (args) {
    if (args.task_id !== undefined && args.task_id !== null) {
      this.task_id = args.task_id;
    }
    if (args.tier_name !== undefined && args.tier_name !== null) {
      this.tier_name = args.tier_name;
    }
  }
};
TaskService_get_eval_user_input_args.prototype = {};
TaskService_get_eval_user_input_args.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 1:
      if (ftype == Thrift.Type.STRING) {
        this.task_id = input.readString().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.STRING) {
        this.tier_name = input.readString().value;
      } else {
        input.skip(ftype);
      }
      break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_get_eval_user_input_args.prototype.write = function(output) {
  output.writeStructBegin('TaskService_get_eval_user_input_args');
  if (this.task_id !== null && this.task_id !== undefined) {
    output.writeFieldBegin('task_id', Thrift.Type.STRING, 1);
    output.writeString(this.task_id);
    output.writeFieldEnd();
  }
  if (this.tier_name !== null && this.tier_name !== undefined) {
    output.writeFieldBegin('tier_name', Thrift.Type.STRING, 2);
    output.writeString(this.tier_name);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_get_eval_user_input_result = function(args) {
  this.success = null;
  if (args) {
    if (args.success !== undefined && args.success !== null) {
      this.success = new UserInput(args.success);
    }
  }
};
TaskService_get_eval_user_input_result.prototype = {};
TaskService_get_eval_user_input_result.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 0:
      if (ftype == Thrift.Type.STRUCT) {
        this.success = new UserInput();
        this.success.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 0:
        input.skip(ftype);
        break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_get_eval_user_input_result.prototype.write = function(output) {
  output.writeStructBegin('TaskService_get_eval_user_input_result');
  if (this.success !== null && this.success !== undefined) {
    output.writeFieldBegin('success', Thrift.Type.STRUCT, 0);
    this.success.write(output);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_render_args = function(args) {
  this.scene = null;
  if (args) {
    if (args.scene !== undefined && args.scene !== null) {
      this.scene = new Scene(args.scene);
    }
  }
};
TaskService_render_args.prototype = {};
TaskService_render_args.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 1:
      if (ftype == Thrift.Type.STRUCT) {
        this.scene = new Scene();
        this.scene.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 0:
        input.skip(ftype);
        break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_render_args.prototype.write = function(output) {
  output.writeStructBegin('TaskService_render_args');
  if (this.scene !== null && this.scene !== undefined) {
    output.writeFieldBegin('scene', Thrift.Type.STRUCT, 1);
    this.scene.write(output);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskService_render_result = function(args) {
  this.success = null;
  if (args) {
    if (args.success !== undefined && args.success !== null) {
      this.success = new Image(args.success);
    }
  }
};
TaskService_render_result.prototype = {};
TaskService_render_result.prototype.read = function(input) {
  input.readStructBegin();
  while (true)
  {
    var ret = input.readFieldBegin();
    var fname = ret.fname;
    var ftype = ret.ftype;
    var fid = ret.fid;
    if (ftype == Thrift.Type.STOP) {
      break;
    }
    switch (fid)
    {
      case 0:
      if (ftype == Thrift.Type.STRUCT) {
        this.success = new Image();
        this.success.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 0:
        input.skip(ftype);
        break;
      default:
        input.skip(ftype);
    }
    input.readFieldEnd();
  }
  input.readStructEnd();
  return;
};

TaskService_render_result.prototype.write = function(output) {
  output.writeStructBegin('TaskService_render_result');
  if (this.success !== null && this.success !== undefined) {
    output.writeFieldBegin('success', Thrift.Type.STRUCT, 0);
    this.success.write(output);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskServiceClient = function(input, output) {
    this.input = input;
    this.output = (!output) ? input : output;
    this.seqid = 0;
};
TaskServiceClient.prototype = {};
TaskServiceClient.prototype.list_task_tier_map = function(task_id_pattern, callback) {
  this.send_list_task_tier_map(task_id_pattern, callback); 
  if (!callback) {
    return this.recv_list_task_tier_map();
  }
};

TaskServiceClient.prototype.send_list_task_tier_map = function(task_id_pattern, callback) {
  this.output.writeMessageBegin('list_task_tier_map', Thrift.MessageType.CALL, this.seqid);
  var params = {
    task_id_pattern: task_id_pattern
  };
  var args = new TaskService_list_task_tier_map_args(params);
  args.write(this.output);
  this.output.writeMessageEnd();
  if (callback) {
    var self = this;
    this.output.getTransport().flush(true, function() {
      var result = null;
      try {
        result = self.recv_list_task_tier_map();
      } catch (e) {
        result = e;
      }
      callback(result);
    });
  } else {
    return this.output.getTransport().flush();
  }
};

TaskServiceClient.prototype.recv_list_task_tier_map = function() {
  var ret = this.input.readMessageBegin();
  var fname = ret.fname;
  var mtype = ret.mtype;
  var rseqid = ret.rseqid;
  if (mtype == Thrift.MessageType.EXCEPTION) {
    var x = new Thrift.TApplicationException();
    x.read(this.input);
    this.input.readMessageEnd();
    throw x;
  }
  var result = new TaskService_list_task_tier_map_result();
  result.read(this.input);
  this.input.readMessageEnd();

  if (null !== result.success) {
    return result.success;
  }
  throw 'list_task_tier_map failed: unknown result';
};
TaskServiceClient.prototype.load_evaluation_data = function(task_id_pattern, callback) {
  this.send_load_evaluation_data(task_id_pattern, callback); 
  if (!callback) {
    return this.recv_load_evaluation_data();
  }
};

TaskServiceClient.prototype.send_load_evaluation_data = function(task_id_pattern, callback) {
  this.output.writeMessageBegin('load_evaluation_data', Thrift.MessageType.CALL, this.seqid);
  var params = {
    task_id_pattern: task_id_pattern
  };
  var args = new TaskService_load_evaluation_data_args(params);
  args.write(this.output);
  this.output.writeMessageEnd();
  if (callback) {
    var self = this;
    this.output.getTransport().flush(true, function() {
      var result = null;
      try {
        result = self.recv_load_evaluation_data();
      } catch (e) {
        result = e;
      }
      callback(result);
    });
  } else {
    return this.output.getTransport().flush();
  }
};

TaskServiceClient.prototype.recv_load_evaluation_data = function() {
  var ret = this.input.readMessageBegin();
  var fname = ret.fname;
  var mtype = ret.mtype;
  var rseqid = ret.rseqid;
  if (mtype == Thrift.MessageType.EXCEPTION) {
    var x = new Thrift.TApplicationException();
    x.read(this.input);
    this.input.readMessageEnd();
    throw x;
  }
  var result = new TaskService_load_evaluation_data_result();
  result.read(this.input);
  this.input.readMessageEnd();

  if (null !== result.success) {
    return result.success;
  }
  throw 'load_evaluation_data failed: unknown result';
};
TaskServiceClient.prototype.get_task_from_id = function(task_id, callback) {
  this.send_get_task_from_id(task_id, callback); 
  if (!callback) {
    return this.recv_get_task_from_id();
  }
};

TaskServiceClient.prototype.send_get_task_from_id = function(task_id, callback) {
  this.output.writeMessageBegin('get_task_from_id', Thrift.MessageType.CALL, this.seqid);
  var params = {
    task_id: task_id
  };
  var args = new TaskService_get_task_from_id_args(params);
  args.write(this.output);
  this.output.writeMessageEnd();
  if (callback) {
    var self = this;
    this.output.getTransport().flush(true, function() {
      var result = null;
      try {
        result = self.recv_get_task_from_id();
      } catch (e) {
        result = e;
      }
      callback(result);
    });
  } else {
    return this.output.getTransport().flush();
  }
};

TaskServiceClient.prototype.recv_get_task_from_id = function() {
  var ret = this.input.readMessageBegin();
  var fname = ret.fname;
  var mtype = ret.mtype;
  var rseqid = ret.rseqid;
  if (mtype == Thrift.MessageType.EXCEPTION) {
    var x = new Thrift.TApplicationException();
    x.read(this.input);
    this.input.readMessageEnd();
    throw x;
  }
  var result = new TaskService_get_task_from_id_result();
  result.read(this.input);
  this.input.readMessageEnd();

  if (null !== result.err) {
    throw result.err;
  }
  if (null !== result.success) {
    return result.success;
  }
  throw 'get_task_from_id failed: unknown result';
};
TaskServiceClient.prototype.get_task_thumbs = function(task_ids, callback) {
  this.send_get_task_thumbs(task_ids, callback); 
  if (!callback) {
    return this.recv_get_task_thumbs();
  }
};

TaskServiceClient.prototype.send_get_task_thumbs = function(task_ids, callback) {
  this.output.writeMessageBegin('get_task_thumbs', Thrift.MessageType.CALL, this.seqid);
  var params = {
    task_ids: task_ids
  };
  var args = new TaskService_get_task_thumbs_args(params);
  args.write(this.output);
  this.output.writeMessageEnd();
  if (callback) {
    var self = this;
    this.output.getTransport().flush(true, function() {
      var result = null;
      try {
        result = self.recv_get_task_thumbs();
      } catch (e) {
        result = e;
      }
      callback(result);
    });
  } else {
    return this.output.getTransport().flush();
  }
};

TaskServiceClient.prototype.recv_get_task_thumbs = function() {
  var ret = this.input.readMessageBegin();
  var fname = ret.fname;
  var mtype = ret.mtype;
  var rseqid = ret.rseqid;
  if (mtype == Thrift.MessageType.EXCEPTION) {
    var x = new Thrift.TApplicationException();
    x.read(this.input);
    this.input.readMessageEnd();
    throw x;
  }
  var result = new TaskService_get_task_thumbs_result();
  result.read(this.input);
  this.input.readMessageEnd();

  if (null !== result.success) {
    return result.success;
  }
  throw 'get_task_thumbs failed: unknown result';
};
TaskServiceClient.prototype.simulate_task_by_id = function(task_id, user_input, dilate, callback) {
  this.send_simulate_task_by_id(task_id, user_input, dilate, callback); 
  if (!callback) {
    return this.recv_simulate_task_by_id();
  }
};

TaskServiceClient.prototype.send_simulate_task_by_id = function(task_id, user_input, dilate, callback) {
  this.output.writeMessageBegin('simulate_task_by_id', Thrift.MessageType.CALL, this.seqid);
  var params = {
    task_id: task_id,
    user_input: user_input,
    dilate: dilate
  };
  var args = new TaskService_simulate_task_by_id_args(params);
  args.write(this.output);
  this.output.writeMessageEnd();
  if (callback) {
    var self = this;
    this.output.getTransport().flush(true, function() {
      var result = null;
      try {
        result = self.recv_simulate_task_by_id();
      } catch (e) {
        result = e;
      }
      callback(result);
    });
  } else {
    return this.output.getTransport().flush();
  }
};

TaskServiceClient.prototype.recv_simulate_task_by_id = function() {
  var ret = this.input.readMessageBegin();
  var fname = ret.fname;
  var mtype = ret.mtype;
  var rseqid = ret.rseqid;
  if (mtype == Thrift.MessageType.EXCEPTION) {
    var x = new Thrift.TApplicationException();
    x.read(this.input);
    this.input.readMessageEnd();
    throw x;
  }
  var result = new TaskService_simulate_task_by_id_result();
  result.read(this.input);
  this.input.readMessageEnd();

  if (null !== result.success) {
    return result.success;
  }
  throw 'simulate_task_by_id failed: unknown result';
};
TaskServiceClient.prototype.simulate_task_with_last_input = function(task, callback) {
  this.send_simulate_task_with_last_input(task, callback); 
  if (!callback) {
    return this.recv_simulate_task_with_last_input();
  }
};

TaskServiceClient.prototype.send_simulate_task_with_last_input = function(task, callback) {
  this.output.writeMessageBegin('simulate_task_with_last_input', Thrift.MessageType.CALL, this.seqid);
  var params = {
    task: task
  };
  var args = new TaskService_simulate_task_with_last_input_args(params);
  args.write(this.output);
  this.output.writeMessageEnd();
  if (callback) {
    var self = this;
    this.output.getTransport().flush(true, function() {
      var result = null;
      try {
        result = self.recv_simulate_task_with_last_input();
      } catch (e) {
        result = e;
      }
      callback(result);
    });
  } else {
    return this.output.getTransport().flush();
  }
};

TaskServiceClient.prototype.recv_simulate_task_with_last_input = function() {
  var ret = this.input.readMessageBegin();
  var fname = ret.fname;
  var mtype = ret.mtype;
  var rseqid = ret.rseqid;
  if (mtype == Thrift.MessageType.EXCEPTION) {
    var x = new Thrift.TApplicationException();
    x.read(this.input);
    this.input.readMessageEnd();
    throw x;
  }
  var result = new TaskService_simulate_task_with_last_input_result();
  result.read(this.input);
  this.input.readMessageEnd();

  if (null !== result.success) {
    return result.success;
  }
  throw 'simulate_task_with_last_input failed: unknown result';
};
TaskServiceClient.prototype.save_solution = function(task_id, user_input, callback) {
  this.send_save_solution(task_id, user_input, callback); 
  if (!callback) {
  this.recv_save_solution();
  }
};

TaskServiceClient.prototype.send_save_solution = function(task_id, user_input, callback) {
  this.output.writeMessageBegin('save_solution', Thrift.MessageType.CALL, this.seqid);
  var params = {
    task_id: task_id,
    user_input: user_input
  };
  var args = new TaskService_save_solution_args(params);
  args.write(this.output);
  this.output.writeMessageEnd();
  if (callback) {
    var self = this;
    this.output.getTransport().flush(true, function() {
      var result = null;
      try {
        result = self.recv_save_solution();
      } catch (e) {
        result = e;
      }
      callback(result);
    });
  } else {
    return this.output.getTransport().flush();
  }
};

TaskServiceClient.prototype.recv_save_solution = function() {
  var ret = this.input.readMessageBegin();
  var fname = ret.fname;
  var mtype = ret.mtype;
  var rseqid = ret.rseqid;
  if (mtype == Thrift.MessageType.EXCEPTION) {
    var x = new Thrift.TApplicationException();
    x.read(this.input);
    this.input.readMessageEnd();
    throw x;
  }
  var result = new TaskService_save_solution_result();
  result.read(this.input);
  this.input.readMessageEnd();

  return;
};
TaskServiceClient.prototype.get_last_input = function(callback) {
  this.send_get_last_input(callback); 
  if (!callback) {
    return this.recv_get_last_input();
  }
};

TaskServiceClient.prototype.send_get_last_input = function(callback) {
  this.output.writeMessageBegin('get_last_input', Thrift.MessageType.CALL, this.seqid);
  var args = new TaskService_get_last_input_args();
  args.write(this.output);
  this.output.writeMessageEnd();
  if (callback) {
    var self = this;
    this.output.getTransport().flush(true, function() {
      var result = null;
      try {
        result = self.recv_get_last_input();
      } catch (e) {
        result = e;
      }
      callback(result);
    });
  } else {
    return this.output.getTransport().flush();
  }
};

TaskServiceClient.prototype.recv_get_last_input = function() {
  var ret = this.input.readMessageBegin();
  var fname = ret.fname;
  var mtype = ret.mtype;
  var rseqid = ret.rseqid;
  if (mtype == Thrift.MessageType.EXCEPTION) {
    var x = new Thrift.TApplicationException();
    x.read(this.input);
    this.input.readMessageEnd();
    throw x;
  }
  var result = new TaskService_get_last_input_result();
  result.read(this.input);
  this.input.readMessageEnd();

  if (null !== result.success) {
    return result.success;
  }
  throw 'get_last_input failed: unknown result';
};
TaskServiceClient.prototype.get_eval_user_input = function(task_id, tier_name, callback) {
  this.send_get_eval_user_input(task_id, tier_name, callback); 
  if (!callback) {
    return this.recv_get_eval_user_input();
  }
};

TaskServiceClient.prototype.send_get_eval_user_input = function(task_id, tier_name, callback) {
  this.output.writeMessageBegin('get_eval_user_input', Thrift.MessageType.CALL, this.seqid);
  var params = {
    task_id: task_id,
    tier_name: tier_name
  };
  var args = new TaskService_get_eval_user_input_args(params);
  args.write(this.output);
  this.output.writeMessageEnd();
  if (callback) {
    var self = this;
    this.output.getTransport().flush(true, function() {
      var result = null;
      try {
        result = self.recv_get_eval_user_input();
      } catch (e) {
        result = e;
      }
      callback(result);
    });
  } else {
    return this.output.getTransport().flush();
  }
};

TaskServiceClient.prototype.recv_get_eval_user_input = function() {
  var ret = this.input.readMessageBegin();
  var fname = ret.fname;
  var mtype = ret.mtype;
  var rseqid = ret.rseqid;
  if (mtype == Thrift.MessageType.EXCEPTION) {
    var x = new Thrift.TApplicationException();
    x.read(this.input);
    this.input.readMessageEnd();
    throw x;
  }
  var result = new TaskService_get_eval_user_input_result();
  result.read(this.input);
  this.input.readMessageEnd();

  if (null !== result.success) {
    return result.success;
  }
  throw 'get_eval_user_input failed: unknown result';
};
TaskServiceClient.prototype.render = function(scene, callback) {
  this.send_render(scene, callback); 
  if (!callback) {
    return this.recv_render();
  }
};

TaskServiceClient.prototype.send_render = function(scene, callback) {
  this.output.writeMessageBegin('render', Thrift.MessageType.CALL, this.seqid);
  var params = {
    scene: scene
  };
  var args = new TaskService_render_args(params);
  args.write(this.output);
  this.output.writeMessageEnd();
  if (callback) {
    var self = this;
    this.output.getTransport().flush(true, function() {
      var result = null;
      try {
        result = self.recv_render();
      } catch (e) {
        result = e;
      }
      callback(result);
    });
  } else {
    return this.output.getTransport().flush();
  }
};

TaskServiceClient.prototype.recv_render = function() {
  var ret = this.input.readMessageBegin();
  var fname = ret.fname;
  var mtype = ret.mtype;
  var rseqid = ret.rseqid;
  if (mtype == Thrift.MessageType.EXCEPTION) {
    var x = new Thrift.TApplicationException();
    x.read(this.input);
    this.input.readMessageEnd();
    throw x;
  }
  var result = new TaskService_render_result();
  result.read(this.input);
  this.input.readMessageEnd();

  if (null !== result.success) {
    return result.success;
  }
  throw 'render failed: unknown result';
};
