  
                                            
  
                                                                   
  


SpatialRelationship = {
  'NONE' : 0,
  'ABOVE' : 1,
  'BELOW' : 2,
  'LEFT_OF' : 3,
  'RIGHT_OF' : 4,
  'TOUCHING_BRIEFLY' : 5,
  'TOUCHING' : 6,
  'INSIDE' : 7,
  'NOT_TOUCHING' : 8,
  'NOT_INSIDE' : 9
};
Task = function(args) {
  this.taskId = null;
  this.scene = null;
  this.bodyId1 = null;
  this.bodyId2 = null;
  this.relationships = null;
  this.description = null;
  this.solutions = null;
  this.phantomShape = null;
  this.tier = null;
  if (args) {
    if (args.taskId !== undefined && args.taskId !== null) {
      this.taskId = args.taskId;
    }
    if (args.scene !== undefined && args.scene !== null) {
      this.scene = new Scene(args.scene);
    } else {
      throw new Thrift.TProtocolException(Thrift.TProtocolExceptionType.UNKNOWN, 'Required field scene is unset!');
    }
    if (args.bodyId1 !== undefined && args.bodyId1 !== null) {
      this.bodyId1 = args.bodyId1;
    } else {
      throw new Thrift.TProtocolException(Thrift.TProtocolExceptionType.UNKNOWN, 'Required field bodyId1 is unset!');
    }
    if (args.bodyId2 !== undefined && args.bodyId2 !== null) {
      this.bodyId2 = args.bodyId2;
    }
    if (args.relationships !== undefined && args.relationships !== null) {
      this.relationships = Thrift.copyList(args.relationships, [null]);
    } else {
      throw new Thrift.TProtocolException(Thrift.TProtocolExceptionType.UNKNOWN, 'Required field relationships is unset!');
    }
    if (args.description !== undefined && args.description !== null) {
      this.description = args.description;
    }
    if (args.solutions !== undefined && args.solutions !== null) {
      this.solutions = Thrift.copyList(args.solutions, [UserInput]);
    }
    if (args.phantomShape !== undefined && args.phantomShape !== null) {
      this.phantomShape = new Shape(args.phantomShape);
    }
    if (args.tier !== undefined && args.tier !== null) {
      this.tier = args.tier;
    }
  }
};
Task.prototype = {};
Task.prototype.read = function(input) {
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
        this.taskId = input.readString().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.STRUCT) {
        this.scene = new Scene();
        this.scene.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 3:
      if (ftype == Thrift.Type.I32) {
        this.bodyId1 = input.readI32().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 4:
      if (ftype == Thrift.Type.I32) {
        this.bodyId2 = input.readI32().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 5:
      if (ftype == Thrift.Type.LIST) {
        var _size0 = 0;
        var _rtmp34;
        this.relationships = [];
        var _etype3 = 0;
        _rtmp34 = input.readListBegin();
        _etype3 = _rtmp34.etype;
        _size0 = _rtmp34.size;
        for (var _i5 = 0; _i5 < _size0; ++_i5)
        {
          var elem6 = null;
          elem6 = input.readI32().value;
          this.relationships.push(elem6);
        }
        input.readListEnd();
      } else {
        input.skip(ftype);
      }
      break;
      case 6:
      if (ftype == Thrift.Type.STRING) {
        this.description = input.readString().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 7:
      if (ftype == Thrift.Type.LIST) {
        var _size7 = 0;
        var _rtmp311;
        this.solutions = [];
        var _etype10 = 0;
        _rtmp311 = input.readListBegin();
        _etype10 = _rtmp311.etype;
        _size7 = _rtmp311.size;
        for (var _i12 = 0; _i12 < _size7; ++_i12)
        {
          var elem13 = null;
          elem13 = new UserInput();
          elem13.read(input);
          this.solutions.push(elem13);
        }
        input.readListEnd();
      } else {
        input.skip(ftype);
      }
      break;
      case 8:
      if (ftype == Thrift.Type.STRUCT) {
        this.phantomShape = new Shape();
        this.phantomShape.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 9:
      if (ftype == Thrift.Type.STRING) {
        this.tier = input.readString().value;
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

Task.prototype.write = function(output) {
  output.writeStructBegin('Task');
  if (this.taskId !== null && this.taskId !== undefined) {
    output.writeFieldBegin('taskId', Thrift.Type.STRING, 1);
    output.writeString(this.taskId);
    output.writeFieldEnd();
  }
  if (this.scene !== null && this.scene !== undefined) {
    output.writeFieldBegin('scene', Thrift.Type.STRUCT, 2);
    this.scene.write(output);
    output.writeFieldEnd();
  }
  if (this.bodyId1 !== null && this.bodyId1 !== undefined) {
    output.writeFieldBegin('bodyId1', Thrift.Type.I32, 3);
    output.writeI32(this.bodyId1);
    output.writeFieldEnd();
  }
  if (this.bodyId2 !== null && this.bodyId2 !== undefined) {
    output.writeFieldBegin('bodyId2', Thrift.Type.I32, 4);
    output.writeI32(this.bodyId2);
    output.writeFieldEnd();
  }
  if (this.relationships !== null && this.relationships !== undefined) {
    output.writeFieldBegin('relationships', Thrift.Type.LIST, 5);
    output.writeListBegin(Thrift.Type.I32, this.relationships.length);
    for (var iter14 in this.relationships)
    {
      if (this.relationships.hasOwnProperty(iter14))
      {
        iter14 = this.relationships[iter14];
        output.writeI32(iter14);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  if (this.description !== null && this.description !== undefined) {
    output.writeFieldBegin('description', Thrift.Type.STRING, 6);
    output.writeString(this.description);
    output.writeFieldEnd();
  }
  if (this.solutions !== null && this.solutions !== undefined) {
    output.writeFieldBegin('solutions', Thrift.Type.LIST, 7);
    output.writeListBegin(Thrift.Type.STRUCT, this.solutions.length);
    for (var iter15 in this.solutions)
    {
      if (this.solutions.hasOwnProperty(iter15))
      {
        iter15 = this.solutions[iter15];
        iter15.write(output);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  if (this.phantomShape !== null && this.phantomShape !== undefined) {
    output.writeFieldBegin('phantomShape', Thrift.Type.STRUCT, 8);
    this.phantomShape.write(output);
    output.writeFieldEnd();
  }
  if (this.tier !== null && this.tier !== undefined) {
    output.writeFieldBegin('tier', Thrift.Type.STRING, 9);
    output.writeString(this.tier);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskCollection = function(args) {
  this.tasks = null;
  if (args) {
    if (args.tasks !== undefined && args.tasks !== null) {
      this.tasks = Thrift.copyList(args.tasks, [Task]);
    }
  }
};
TaskCollection.prototype = {};
TaskCollection.prototype.read = function(input) {
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
        var _size16 = 0;
        var _rtmp320;
        this.tasks = [];
        var _etype19 = 0;
        _rtmp320 = input.readListBegin();
        _etype19 = _rtmp320.etype;
        _size16 = _rtmp320.size;
        for (var _i21 = 0; _i21 < _size16; ++_i21)
        {
          var elem22 = null;
          elem22 = new Task();
          elem22.read(input);
          this.tasks.push(elem22);
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

TaskCollection.prototype.write = function(output) {
  output.writeStructBegin('TaskCollection');
  if (this.tasks !== null && this.tasks !== undefined) {
    output.writeFieldBegin('tasks', Thrift.Type.LIST, 1);
    output.writeListBegin(Thrift.Type.STRUCT, this.tasks.length);
    for (var iter23 in this.tasks)
    {
      if (this.tasks.hasOwnProperty(iter23))
      {
        iter23 = this.tasks[iter23];
        iter23.write(output);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskSimulation = function(args) {
  this.isSolution = null;
  this.sceneList = null;
  this.solvedStateList = null;
  this.stepsSimulated = null;
  if (args) {
    if (args.isSolution !== undefined && args.isSolution !== null) {
      this.isSolution = args.isSolution;
    }
    if (args.sceneList !== undefined && args.sceneList !== null) {
      this.sceneList = Thrift.copyList(args.sceneList, [Scene]);
    }
    if (args.solvedStateList !== undefined && args.solvedStateList !== null) {
      this.solvedStateList = Thrift.copyList(args.solvedStateList, [null]);
    }
    if (args.stepsSimulated !== undefined && args.stepsSimulated !== null) {
      this.stepsSimulated = args.stepsSimulated;
    }
  }
};
TaskSimulation.prototype = {};
TaskSimulation.prototype.read = function(input) {
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
      if (ftype == Thrift.Type.BOOL) {
        this.isSolution = input.readBool().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.LIST) {
        var _size24 = 0;
        var _rtmp328;
        this.sceneList = [];
        var _etype27 = 0;
        _rtmp328 = input.readListBegin();
        _etype27 = _rtmp328.etype;
        _size24 = _rtmp328.size;
        for (var _i29 = 0; _i29 < _size24; ++_i29)
        {
          var elem30 = null;
          elem30 = new Scene();
          elem30.read(input);
          this.sceneList.push(elem30);
        }
        input.readListEnd();
      } else {
        input.skip(ftype);
      }
      break;
      case 3:
      if (ftype == Thrift.Type.LIST) {
        var _size31 = 0;
        var _rtmp335;
        this.solvedStateList = [];
        var _etype34 = 0;
        _rtmp335 = input.readListBegin();
        _etype34 = _rtmp335.etype;
        _size31 = _rtmp335.size;
        for (var _i36 = 0; _i36 < _size31; ++_i36)
        {
          var elem37 = null;
          elem37 = input.readBool().value;
          this.solvedStateList.push(elem37);
        }
        input.readListEnd();
      } else {
        input.skip(ftype);
      }
      break;
      case 4:
      if (ftype == Thrift.Type.I32) {
        this.stepsSimulated = input.readI32().value;
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

TaskSimulation.prototype.write = function(output) {
  output.writeStructBegin('TaskSimulation');
  if (this.isSolution !== null && this.isSolution !== undefined) {
    output.writeFieldBegin('isSolution', Thrift.Type.BOOL, 1);
    output.writeBool(this.isSolution);
    output.writeFieldEnd();
  }
  if (this.sceneList !== null && this.sceneList !== undefined) {
    output.writeFieldBegin('sceneList', Thrift.Type.LIST, 2);
    output.writeListBegin(Thrift.Type.STRUCT, this.sceneList.length);
    for (var iter38 in this.sceneList)
    {
      if (this.sceneList.hasOwnProperty(iter38))
      {
        iter38 = this.sceneList[iter38];
        iter38.write(output);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  if (this.solvedStateList !== null && this.solvedStateList !== undefined) {
    output.writeFieldBegin('solvedStateList', Thrift.Type.LIST, 3);
    output.writeListBegin(Thrift.Type.BOOL, this.solvedStateList.length);
    for (var iter39 in this.solvedStateList)
    {
      if (this.solvedStateList.hasOwnProperty(iter39))
      {
        iter39 = this.solvedStateList[iter39];
        output.writeBool(iter39);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  if (this.stepsSimulated !== null && this.stepsSimulated !== undefined) {
    output.writeFieldBegin('stepsSimulated', Thrift.Type.I32, 4);
    output.writeI32(this.stepsSimulated);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskSimulationWithMeta = function(args) {
  this.simulation = null;
  this.rendered_imgs = null;
  if (args) {
    if (args.simulation !== undefined && args.simulation !== null) {
      this.simulation = new TaskSimulation(args.simulation);
    }
    if (args.rendered_imgs !== undefined && args.rendered_imgs !== null) {
      this.rendered_imgs = Thrift.copyList(args.rendered_imgs, [null]);
    }
  }
};
TaskSimulationWithMeta.prototype = {};
TaskSimulationWithMeta.prototype.read = function(input) {
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
        this.simulation = new TaskSimulation();
        this.simulation.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.LIST) {
        var _size40 = 0;
        var _rtmp344;
        this.rendered_imgs = [];
        var _etype43 = 0;
        _rtmp344 = input.readListBegin();
        _etype43 = _rtmp344.etype;
        _size40 = _rtmp344.size;
        for (var _i45 = 0; _i45 < _size40; ++_i45)
        {
          var elem46 = null;
          elem46 = input.readString().value;
          this.rendered_imgs.push(elem46);
        }
        input.readListEnd();
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

TaskSimulationWithMeta.prototype.write = function(output) {
  output.writeStructBegin('TaskSimulationWithMeta');
  if (this.simulation !== null && this.simulation !== undefined) {
    output.writeFieldBegin('simulation', Thrift.Type.STRUCT, 1);
    this.simulation.write(output);
    output.writeFieldEnd();
  }
  if (this.rendered_imgs !== null && this.rendered_imgs !== undefined) {
    output.writeFieldBegin('rendered_imgs', Thrift.Type.LIST, 2);
    output.writeListBegin(Thrift.Type.STRING, this.rendered_imgs.length);
    for (var iter47 in this.rendered_imgs)
    {
      if (this.rendered_imgs.hasOwnProperty(iter47))
      {
        iter47 = this.rendered_imgs[iter47];
        output.writeString(iter47);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

Thumb = function(args) {
  this.img = null;
  this.extra = null;
  if (args) {
    if (args.img !== undefined && args.img !== null) {
      this.img = args.img;
    }
    if (args.extra !== undefined && args.extra !== null) {
      this.extra = args.extra;
    }
  }
};
Thumb.prototype = {};
Thumb.prototype.read = function(input) {
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
        this.img = input.readString().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.STRING) {
        this.extra = input.readString().value;
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

Thumb.prototype.write = function(output) {
  output.writeStructBegin('Thumb');
  if (this.img !== null && this.img !== undefined) {
    output.writeFieldBegin('img', Thrift.Type.STRING, 1);
    output.writeString(this.img);
    output.writeFieldEnd();
  }
  if (this.extra !== null && this.extra !== undefined) {
    output.writeFieldBegin('extra', Thrift.Type.STRING, 2);
    output.writeString(this.extra);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

EvalData = function(args) {
  this.attempts_to_solve_ball = null;
  this.attempts_to_solve_two_balls = null;
  this.attempts_to_solve_ramp = null;
  this.percent_ball = null;
  this.percent_two_balls = null;
  this.percent_ramp = null;
  this.solution_ball = null;
  this.solution_two_balls = null;
  this.solution_ramp = null;
  this.flag_ball = null;
  this.flag_two_balls = null;
  this.flag_ramp = null;
  this.known_solutions = null;
  this.num_tasks = null;
  if (args) {
    if (args.attempts_to_solve_ball !== undefined && args.attempts_to_solve_ball !== null) {
      this.attempts_to_solve_ball = args.attempts_to_solve_ball;
    }
    if (args.attempts_to_solve_two_balls !== undefined && args.attempts_to_solve_two_balls !== null) {
      this.attempts_to_solve_two_balls = args.attempts_to_solve_two_balls;
    }
    if (args.attempts_to_solve_ramp !== undefined && args.attempts_to_solve_ramp !== null) {
      this.attempts_to_solve_ramp = args.attempts_to_solve_ramp;
    }
    if (args.percent_ball !== undefined && args.percent_ball !== null) {
      this.percent_ball = args.percent_ball;
    }
    if (args.percent_two_balls !== undefined && args.percent_two_balls !== null) {
      this.percent_two_balls = args.percent_two_balls;
    }
    if (args.percent_ramp !== undefined && args.percent_ramp !== null) {
      this.percent_ramp = args.percent_ramp;
    }
    if (args.solution_ball !== undefined && args.solution_ball !== null) {
      this.solution_ball = new UserInput(args.solution_ball);
    }
    if (args.solution_two_balls !== undefined && args.solution_two_balls !== null) {
      this.solution_two_balls = new UserInput(args.solution_two_balls);
    }
    if (args.solution_ramp !== undefined && args.solution_ramp !== null) {
      this.solution_ramp = new UserInput(args.solution_ramp);
    }
    if (args.flag_ball !== undefined && args.flag_ball !== null) {
      this.flag_ball = args.flag_ball;
    }
    if (args.flag_two_balls !== undefined && args.flag_two_balls !== null) {
      this.flag_two_balls = args.flag_two_balls;
    }
    if (args.flag_ramp !== undefined && args.flag_ramp !== null) {
      this.flag_ramp = args.flag_ramp;
    }
    if (args.known_solutions !== undefined && args.known_solutions !== null) {
      this.known_solutions = Thrift.copyList(args.known_solutions, [null]);
    }
    if (args.num_tasks !== undefined && args.num_tasks !== null) {
      this.num_tasks = args.num_tasks;
    }
  }
};
EvalData.prototype = {};
EvalData.prototype.read = function(input) {
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
      if (ftype == Thrift.Type.I32) {
        this.attempts_to_solve_ball = input.readI32().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.I32) {
        this.attempts_to_solve_two_balls = input.readI32().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 3:
      if (ftype == Thrift.Type.I32) {
        this.attempts_to_solve_ramp = input.readI32().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 7:
      if (ftype == Thrift.Type.I32) {
        this.percent_ball = input.readI32().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 8:
      if (ftype == Thrift.Type.I32) {
        this.percent_two_balls = input.readI32().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 9:
      if (ftype == Thrift.Type.I32) {
        this.percent_ramp = input.readI32().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 4:
      if (ftype == Thrift.Type.STRUCT) {
        this.solution_ball = new UserInput();
        this.solution_ball.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 5:
      if (ftype == Thrift.Type.STRUCT) {
        this.solution_two_balls = new UserInput();
        this.solution_two_balls.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 6:
      if (ftype == Thrift.Type.STRUCT) {
        this.solution_ramp = new UserInput();
        this.solution_ramp.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 10:
      if (ftype == Thrift.Type.STRING) {
        this.flag_ball = input.readString().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 11:
      if (ftype == Thrift.Type.STRING) {
        this.flag_two_balls = input.readString().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 12:
      if (ftype == Thrift.Type.STRING) {
        this.flag_ramp = input.readString().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 13:
      if (ftype == Thrift.Type.LIST) {
        var _size48 = 0;
        var _rtmp352;
        this.known_solutions = [];
        var _etype51 = 0;
        _rtmp352 = input.readListBegin();
        _etype51 = _rtmp352.etype;
        _size48 = _rtmp352.size;
        for (var _i53 = 0; _i53 < _size48; ++_i53)
        {
          var elem54 = null;
          elem54 = input.readString().value;
          this.known_solutions.push(elem54);
        }
        input.readListEnd();
      } else {
        input.skip(ftype);
      }
      break;
      case 14:
      if (ftype == Thrift.Type.I32) {
        this.num_tasks = input.readI32().value;
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

EvalData.prototype.write = function(output) {
  output.writeStructBegin('EvalData');
  if (this.attempts_to_solve_ball !== null && this.attempts_to_solve_ball !== undefined) {
    output.writeFieldBegin('attempts_to_solve_ball', Thrift.Type.I32, 1);
    output.writeI32(this.attempts_to_solve_ball);
    output.writeFieldEnd();
  }
  if (this.attempts_to_solve_two_balls !== null && this.attempts_to_solve_two_balls !== undefined) {
    output.writeFieldBegin('attempts_to_solve_two_balls', Thrift.Type.I32, 2);
    output.writeI32(this.attempts_to_solve_two_balls);
    output.writeFieldEnd();
  }
  if (this.attempts_to_solve_ramp !== null && this.attempts_to_solve_ramp !== undefined) {
    output.writeFieldBegin('attempts_to_solve_ramp', Thrift.Type.I32, 3);
    output.writeI32(this.attempts_to_solve_ramp);
    output.writeFieldEnd();
  }
  if (this.percent_ball !== null && this.percent_ball !== undefined) {
    output.writeFieldBegin('percent_ball', Thrift.Type.I32, 7);
    output.writeI32(this.percent_ball);
    output.writeFieldEnd();
  }
  if (this.percent_two_balls !== null && this.percent_two_balls !== undefined) {
    output.writeFieldBegin('percent_two_balls', Thrift.Type.I32, 8);
    output.writeI32(this.percent_two_balls);
    output.writeFieldEnd();
  }
  if (this.percent_ramp !== null && this.percent_ramp !== undefined) {
    output.writeFieldBegin('percent_ramp', Thrift.Type.I32, 9);
    output.writeI32(this.percent_ramp);
    output.writeFieldEnd();
  }
  if (this.solution_ball !== null && this.solution_ball !== undefined) {
    output.writeFieldBegin('solution_ball', Thrift.Type.STRUCT, 4);
    this.solution_ball.write(output);
    output.writeFieldEnd();
  }
  if (this.solution_two_balls !== null && this.solution_two_balls !== undefined) {
    output.writeFieldBegin('solution_two_balls', Thrift.Type.STRUCT, 5);
    this.solution_two_balls.write(output);
    output.writeFieldEnd();
  }
  if (this.solution_ramp !== null && this.solution_ramp !== undefined) {
    output.writeFieldBegin('solution_ramp', Thrift.Type.STRUCT, 6);
    this.solution_ramp.write(output);
    output.writeFieldEnd();
  }
  if (this.flag_ball !== null && this.flag_ball !== undefined) {
    output.writeFieldBegin('flag_ball', Thrift.Type.STRING, 10);
    output.writeString(this.flag_ball);
    output.writeFieldEnd();
  }
  if (this.flag_two_balls !== null && this.flag_two_balls !== undefined) {
    output.writeFieldBegin('flag_two_balls', Thrift.Type.STRING, 11);
    output.writeString(this.flag_two_balls);
    output.writeFieldEnd();
  }
  if (this.flag_ramp !== null && this.flag_ramp !== undefined) {
    output.writeFieldBegin('flag_ramp', Thrift.Type.STRING, 12);
    output.writeString(this.flag_ramp);
    output.writeFieldEnd();
  }
  if (this.known_solutions !== null && this.known_solutions !== undefined) {
    output.writeFieldBegin('known_solutions', Thrift.Type.LIST, 13);
    output.writeListBegin(Thrift.Type.STRING, this.known_solutions.length);
    for (var iter55 in this.known_solutions)
    {
      if (this.known_solutions.hasOwnProperty(iter55))
      {
        iter55 = this.known_solutions[iter55];
        output.writeString(iter55);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  if (this.num_tasks !== null && this.num_tasks !== undefined) {
    output.writeFieldBegin('num_tasks', Thrift.Type.I32, 14);
    output.writeI32(this.num_tasks);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

TaskWithMeta = function(args) {
  this.task = null;
  this.eval_data = null;
  this.template_params = null;
  this.text_eval_info = null;
  this.rendered_img = null;
  if (args) {
    if (args.task !== undefined && args.task !== null) {
      this.task = new Task(args.task);
    }
    if (args.eval_data !== undefined && args.eval_data !== null) {
      this.eval_data = new EvalData(args.eval_data);
    }
    if (args.template_params !== undefined && args.template_params !== null) {
      this.template_params = args.template_params;
    }
    if (args.text_eval_info !== undefined && args.text_eval_info !== null) {
      this.text_eval_info = args.text_eval_info;
    }
    if (args.rendered_img !== undefined && args.rendered_img !== null) {
      this.rendered_img = args.rendered_img;
    }
  }
};
TaskWithMeta.prototype = {};
TaskWithMeta.prototype.read = function(input) {
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
      case 2:
      if (ftype == Thrift.Type.STRUCT) {
        this.eval_data = new EvalData();
        this.eval_data.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 3:
      if (ftype == Thrift.Type.STRING) {
        this.template_params = input.readString().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 4:
      if (ftype == Thrift.Type.STRING) {
        this.text_eval_info = input.readString().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 5:
      if (ftype == Thrift.Type.STRING) {
        this.rendered_img = input.readString().value;
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

TaskWithMeta.prototype.write = function(output) {
  output.writeStructBegin('TaskWithMeta');
  if (this.task !== null && this.task !== undefined) {
    output.writeFieldBegin('task', Thrift.Type.STRUCT, 1);
    this.task.write(output);
    output.writeFieldEnd();
  }
  if (this.eval_data !== null && this.eval_data !== undefined) {
    output.writeFieldBegin('eval_data', Thrift.Type.STRUCT, 2);
    this.eval_data.write(output);
    output.writeFieldEnd();
  }
  if (this.template_params !== null && this.template_params !== undefined) {
    output.writeFieldBegin('template_params', Thrift.Type.STRING, 3);
    output.writeString(this.template_params);
    output.writeFieldEnd();
  }
  if (this.text_eval_info !== null && this.text_eval_info !== undefined) {
    output.writeFieldBegin('text_eval_info', Thrift.Type.STRING, 4);
    output.writeString(this.text_eval_info);
    output.writeFieldEnd();
  }
  if (this.rendered_img !== null && this.rendered_img !== undefined) {
    output.writeFieldBegin('rendered_img', Thrift.Type.STRING, 5);
    output.writeString(this.rendered_img);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

