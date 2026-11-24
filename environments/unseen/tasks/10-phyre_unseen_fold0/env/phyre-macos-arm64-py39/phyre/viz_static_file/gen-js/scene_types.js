  
                                            
  
                                                                   
  


BodyType = {
  'STATIC' : 1,
  'DYNAMIC' : 2
};
ShapeType = {
  'UNDEFINED' : 0,
  'BALL' : 1,
  'BAR' : 2,
  'JAR' : 3,
  'STANDINGSTICKS' : 4
};
UserInputStatus = {
  'UNDEFINED' : 0,
  'NO_OCCLUSIONS' : 1,
  'HAD_OCCLUSIONS' : 2
};
Vector = function(args) {
  this.x = null;
  this.y = null;
  if (args) {
    if (args.x !== undefined && args.x !== null) {
      this.x = args.x;
    } else {
      throw new Thrift.TProtocolException(Thrift.TProtocolExceptionType.UNKNOWN, 'Required field x is unset!');
    }
    if (args.y !== undefined && args.y !== null) {
      this.y = args.y;
    } else {
      throw new Thrift.TProtocolException(Thrift.TProtocolExceptionType.UNKNOWN, 'Required field y is unset!');
    }
  }
};
Vector.prototype = {};
Vector.prototype.read = function(input) {
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
      if (ftype == Thrift.Type.DOUBLE) {
        this.x = input.readDouble().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.DOUBLE) {
        this.y = input.readDouble().value;
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

Vector.prototype.write = function(output) {
  output.writeStructBegin('Vector');
  if (this.x !== null && this.x !== undefined) {
    output.writeFieldBegin('x', Thrift.Type.DOUBLE, 1);
    output.writeDouble(this.x);
    output.writeFieldEnd();
  }
  if (this.y !== null && this.y !== undefined) {
    output.writeFieldBegin('y', Thrift.Type.DOUBLE, 2);
    output.writeDouble(this.y);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

IntVector = function(args) {
  this.x = null;
  this.y = null;
  if (args) {
    if (args.x !== undefined && args.x !== null) {
      this.x = args.x;
    } else {
      throw new Thrift.TProtocolException(Thrift.TProtocolExceptionType.UNKNOWN, 'Required field x is unset!');
    }
    if (args.y !== undefined && args.y !== null) {
      this.y = args.y;
    } else {
      throw new Thrift.TProtocolException(Thrift.TProtocolExceptionType.UNKNOWN, 'Required field y is unset!');
    }
  }
};
IntVector.prototype = {};
IntVector.prototype.read = function(input) {
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
        this.x = input.readI32().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.I32) {
        this.y = input.readI32().value;
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

IntVector.prototype.write = function(output) {
  output.writeStructBegin('IntVector');
  if (this.x !== null && this.x !== undefined) {
    output.writeFieldBegin('x', Thrift.Type.I32, 1);
    output.writeI32(this.x);
    output.writeFieldEnd();
  }
  if (this.y !== null && this.y !== undefined) {
    output.writeFieldBegin('y', Thrift.Type.I32, 2);
    output.writeI32(this.y);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

Polygon = function(args) {
  this.vertices = null;
  if (args) {
    if (args.vertices !== undefined && args.vertices !== null) {
      this.vertices = Thrift.copyList(args.vertices, [Vector]);
    } else {
      throw new Thrift.TProtocolException(Thrift.TProtocolExceptionType.UNKNOWN, 'Required field vertices is unset!');
    }
  }
};
Polygon.prototype = {};
Polygon.prototype.read = function(input) {
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
        var _size0 = 0;
        var _rtmp34;
        this.vertices = [];
        var _etype3 = 0;
        _rtmp34 = input.readListBegin();
        _etype3 = _rtmp34.etype;
        _size0 = _rtmp34.size;
        for (var _i5 = 0; _i5 < _size0; ++_i5)
        {
          var elem6 = null;
          elem6 = new Vector();
          elem6.read(input);
          this.vertices.push(elem6);
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

Polygon.prototype.write = function(output) {
  output.writeStructBegin('Polygon');
  if (this.vertices !== null && this.vertices !== undefined) {
    output.writeFieldBegin('vertices', Thrift.Type.LIST, 1);
    output.writeListBegin(Thrift.Type.STRUCT, this.vertices.length);
    for (var iter7 in this.vertices)
    {
      if (this.vertices.hasOwnProperty(iter7))
      {
        iter7 = this.vertices[iter7];
        iter7.write(output);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

Circle = function(args) {
  this.radius = null;
  if (args) {
    if (args.radius !== undefined && args.radius !== null) {
      this.radius = args.radius;
    } else {
      throw new Thrift.TProtocolException(Thrift.TProtocolExceptionType.UNKNOWN, 'Required field radius is unset!');
    }
  }
};
Circle.prototype = {};
Circle.prototype.read = function(input) {
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
      if (ftype == Thrift.Type.DOUBLE) {
        this.radius = input.readDouble().value;
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

Circle.prototype.write = function(output) {
  output.writeStructBegin('Circle');
  if (this.radius !== null && this.radius !== undefined) {
    output.writeFieldBegin('radius', Thrift.Type.DOUBLE, 1);
    output.writeDouble(this.radius);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

Shape = function(args) {
  this.polygon = null;
  this.circle = null;
  if (args) {
    if (args.polygon !== undefined && args.polygon !== null) {
      this.polygon = new Polygon(args.polygon);
    }
    if (args.circle !== undefined && args.circle !== null) {
      this.circle = new Circle(args.circle);
    }
  }
};
Shape.prototype = {};
Shape.prototype.read = function(input) {
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
        this.polygon = new Polygon();
        this.polygon.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.STRUCT) {
        this.circle = new Circle();
        this.circle.read(input);
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

Shape.prototype.write = function(output) {
  output.writeStructBegin('Shape');
  if (this.polygon !== null && this.polygon !== undefined) {
    output.writeFieldBegin('polygon', Thrift.Type.STRUCT, 1);
    this.polygon.write(output);
    output.writeFieldEnd();
  }
  if (this.circle !== null && this.circle !== undefined) {
    output.writeFieldBegin('circle', Thrift.Type.STRUCT, 2);
    this.circle.write(output);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

Body = function(args) {
  this.position = null;
  this.bodyType = null;
  this.angle = 0;
  this.shapes = null;
  this.color = null;
  this.shapeType = 0;
  this.diameter = null;
  if (args) {
    if (args.position !== undefined && args.position !== null) {
      this.position = new Vector(args.position);
    } else {
      throw new Thrift.TProtocolException(Thrift.TProtocolExceptionType.UNKNOWN, 'Required field position is unset!');
    }
    if (args.bodyType !== undefined && args.bodyType !== null) {
      this.bodyType = args.bodyType;
    } else {
      throw new Thrift.TProtocolException(Thrift.TProtocolExceptionType.UNKNOWN, 'Required field bodyType is unset!');
    }
    if (args.angle !== undefined && args.angle !== null) {
      this.angle = args.angle;
    }
    if (args.shapes !== undefined && args.shapes !== null) {
      this.shapes = Thrift.copyList(args.shapes, [Shape]);
    }
    if (args.color !== undefined && args.color !== null) {
      this.color = args.color;
    }
    if (args.shapeType !== undefined && args.shapeType !== null) {
      this.shapeType = args.shapeType;
    }
    if (args.diameter !== undefined && args.diameter !== null) {
      this.diameter = args.diameter;
    }
  }
};
Body.prototype = {};
Body.prototype.read = function(input) {
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
        this.position = new Vector();
        this.position.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.I32) {
        this.bodyType = input.readI32().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 3:
      if (ftype == Thrift.Type.DOUBLE) {
        this.angle = input.readDouble().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 4:
      if (ftype == Thrift.Type.LIST) {
        var _size8 = 0;
        var _rtmp312;
        this.shapes = [];
        var _etype11 = 0;
        _rtmp312 = input.readListBegin();
        _etype11 = _rtmp312.etype;
        _size8 = _rtmp312.size;
        for (var _i13 = 0; _i13 < _size8; ++_i13)
        {
          var elem14 = null;
          elem14 = new Shape();
          elem14.read(input);
          this.shapes.push(elem14);
        }
        input.readListEnd();
      } else {
        input.skip(ftype);
      }
      break;
      case 5:
      if (ftype == Thrift.Type.I32) {
        this.color = input.readI32().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 6:
      if (ftype == Thrift.Type.I32) {
        this.shapeType = input.readI32().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 7:
      if (ftype == Thrift.Type.DOUBLE) {
        this.diameter = input.readDouble().value;
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

Body.prototype.write = function(output) {
  output.writeStructBegin('Body');
  if (this.position !== null && this.position !== undefined) {
    output.writeFieldBegin('position', Thrift.Type.STRUCT, 1);
    this.position.write(output);
    output.writeFieldEnd();
  }
  if (this.bodyType !== null && this.bodyType !== undefined) {
    output.writeFieldBegin('bodyType', Thrift.Type.I32, 2);
    output.writeI32(this.bodyType);
    output.writeFieldEnd();
  }
  if (this.angle !== null && this.angle !== undefined) {
    output.writeFieldBegin('angle', Thrift.Type.DOUBLE, 3);
    output.writeDouble(this.angle);
    output.writeFieldEnd();
  }
  if (this.shapes !== null && this.shapes !== undefined) {
    output.writeFieldBegin('shapes', Thrift.Type.LIST, 4);
    output.writeListBegin(Thrift.Type.STRUCT, this.shapes.length);
    for (var iter15 in this.shapes)
    {
      if (this.shapes.hasOwnProperty(iter15))
      {
        iter15 = this.shapes[iter15];
        iter15.write(output);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  if (this.color !== null && this.color !== undefined) {
    output.writeFieldBegin('color', Thrift.Type.I32, 5);
    output.writeI32(this.color);
    output.writeFieldEnd();
  }
  if (this.shapeType !== null && this.shapeType !== undefined) {
    output.writeFieldBegin('shapeType', Thrift.Type.I32, 6);
    output.writeI32(this.shapeType);
    output.writeFieldEnd();
  }
  if (this.diameter !== null && this.diameter !== undefined) {
    output.writeFieldBegin('diameter', Thrift.Type.DOUBLE, 7);
    output.writeDouble(this.diameter);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

AbsoluteConvexPolygon = function(args) {
  this.vertices = null;
  if (args) {
    if (args.vertices !== undefined && args.vertices !== null) {
      this.vertices = Thrift.copyList(args.vertices, [Vector]);
    }
  }
};
AbsoluteConvexPolygon.prototype = {};
AbsoluteConvexPolygon.prototype.read = function(input) {
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
        this.vertices = [];
        var _etype19 = 0;
        _rtmp320 = input.readListBegin();
        _etype19 = _rtmp320.etype;
        _size16 = _rtmp320.size;
        for (var _i21 = 0; _i21 < _size16; ++_i21)
        {
          var elem22 = null;
          elem22 = new Vector();
          elem22.read(input);
          this.vertices.push(elem22);
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

AbsoluteConvexPolygon.prototype.write = function(output) {
  output.writeStructBegin('AbsoluteConvexPolygon');
  if (this.vertices !== null && this.vertices !== undefined) {
    output.writeFieldBegin('vertices', Thrift.Type.LIST, 1);
    output.writeListBegin(Thrift.Type.STRUCT, this.vertices.length);
    for (var iter23 in this.vertices)
    {
      if (this.vertices.hasOwnProperty(iter23))
      {
        iter23 = this.vertices[iter23];
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

CircleWithPosition = function(args) {
  this.position = null;
  this.radius = null;
  if (args) {
    if (args.position !== undefined && args.position !== null) {
      this.position = new Vector(args.position);
    }
    if (args.radius !== undefined && args.radius !== null) {
      this.radius = args.radius;
    }
  }
};
CircleWithPosition.prototype = {};
CircleWithPosition.prototype.read = function(input) {
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
        this.position = new Vector();
        this.position.read(input);
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.DOUBLE) {
        this.radius = input.readDouble().value;
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

CircleWithPosition.prototype.write = function(output) {
  output.writeStructBegin('CircleWithPosition');
  if (this.position !== null && this.position !== undefined) {
    output.writeFieldBegin('position', Thrift.Type.STRUCT, 1);
    this.position.write(output);
    output.writeFieldEnd();
  }
  if (this.radius !== null && this.radius !== undefined) {
    output.writeFieldBegin('radius', Thrift.Type.DOUBLE, 2);
    output.writeDouble(this.radius);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

UserInput = function(args) {
  this.polygons = null;
  this.balls = null;
  this.flattened_point_list = null;
  if (args) {
    if (args.polygons !== undefined && args.polygons !== null) {
      this.polygons = Thrift.copyList(args.polygons, [AbsoluteConvexPolygon]);
    }
    if (args.balls !== undefined && args.balls !== null) {
      this.balls = Thrift.copyList(args.balls, [CircleWithPosition]);
    }
    if (args.flattened_point_list !== undefined && args.flattened_point_list !== null) {
      this.flattened_point_list = Thrift.copyList(args.flattened_point_list, [null]);
    }
  }
};
UserInput.prototype = {};
UserInput.prototype.read = function(input) {
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
        var _size24 = 0;
        var _rtmp328;
        this.polygons = [];
        var _etype27 = 0;
        _rtmp328 = input.readListBegin();
        _etype27 = _rtmp328.etype;
        _size24 = _rtmp328.size;
        for (var _i29 = 0; _i29 < _size24; ++_i29)
        {
          var elem30 = null;
          elem30 = new AbsoluteConvexPolygon();
          elem30.read(input);
          this.polygons.push(elem30);
        }
        input.readListEnd();
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.LIST) {
        var _size31 = 0;
        var _rtmp335;
        this.balls = [];
        var _etype34 = 0;
        _rtmp335 = input.readListBegin();
        _etype34 = _rtmp335.etype;
        _size31 = _rtmp335.size;
        for (var _i36 = 0; _i36 < _size31; ++_i36)
        {
          var elem37 = null;
          elem37 = new CircleWithPosition();
          elem37.read(input);
          this.balls.push(elem37);
        }
        input.readListEnd();
      } else {
        input.skip(ftype);
      }
      break;
      case 3:
      if (ftype == Thrift.Type.LIST) {
        var _size38 = 0;
        var _rtmp342;
        this.flattened_point_list = [];
        var _etype41 = 0;
        _rtmp342 = input.readListBegin();
        _etype41 = _rtmp342.etype;
        _size38 = _rtmp342.size;
        for (var _i43 = 0; _i43 < _size38; ++_i43)
        {
          var elem44 = null;
          elem44 = input.readI32().value;
          this.flattened_point_list.push(elem44);
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

UserInput.prototype.write = function(output) {
  output.writeStructBegin('UserInput');
  if (this.polygons !== null && this.polygons !== undefined) {
    output.writeFieldBegin('polygons', Thrift.Type.LIST, 1);
    output.writeListBegin(Thrift.Type.STRUCT, this.polygons.length);
    for (var iter45 in this.polygons)
    {
      if (this.polygons.hasOwnProperty(iter45))
      {
        iter45 = this.polygons[iter45];
        iter45.write(output);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  if (this.balls !== null && this.balls !== undefined) {
    output.writeFieldBegin('balls', Thrift.Type.LIST, 2);
    output.writeListBegin(Thrift.Type.STRUCT, this.balls.length);
    for (var iter46 in this.balls)
    {
      if (this.balls.hasOwnProperty(iter46))
      {
        iter46 = this.balls[iter46];
        iter46.write(output);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  if (this.flattened_point_list !== null && this.flattened_point_list !== undefined) {
    output.writeFieldBegin('flattened_point_list', Thrift.Type.LIST, 3);
    output.writeListBegin(Thrift.Type.I32, this.flattened_point_list.length);
    for (var iter47 in this.flattened_point_list)
    {
      if (this.flattened_point_list.hasOwnProperty(iter47))
      {
        iter47 = this.flattened_point_list[iter47];
        output.writeI32(iter47);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

Scene = function(args) {
  this.bodies = null;
  this.user_input_bodies = null;
  this.width = null;
  this.height = null;
  this.user_input_status = 0;
  if (args) {
    if (args.bodies !== undefined && args.bodies !== null) {
      this.bodies = Thrift.copyList(args.bodies, [Body]);
    }
    if (args.user_input_bodies !== undefined && args.user_input_bodies !== null) {
      this.user_input_bodies = Thrift.copyList(args.user_input_bodies, [Body]);
    }
    if (args.width !== undefined && args.width !== null) {
      this.width = args.width;
    } else {
      throw new Thrift.TProtocolException(Thrift.TProtocolExceptionType.UNKNOWN, 'Required field width is unset!');
    }
    if (args.height !== undefined && args.height !== null) {
      this.height = args.height;
    } else {
      throw new Thrift.TProtocolException(Thrift.TProtocolExceptionType.UNKNOWN, 'Required field height is unset!');
    }
    if (args.user_input_status !== undefined && args.user_input_status !== null) {
      this.user_input_status = args.user_input_status;
    }
  }
};
Scene.prototype = {};
Scene.prototype.read = function(input) {
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
        var _size48 = 0;
        var _rtmp352;
        this.bodies = [];
        var _etype51 = 0;
        _rtmp352 = input.readListBegin();
        _etype51 = _rtmp352.etype;
        _size48 = _rtmp352.size;
        for (var _i53 = 0; _i53 < _size48; ++_i53)
        {
          var elem54 = null;
          elem54 = new Body();
          elem54.read(input);
          this.bodies.push(elem54);
        }
        input.readListEnd();
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.LIST) {
        var _size55 = 0;
        var _rtmp359;
        this.user_input_bodies = [];
        var _etype58 = 0;
        _rtmp359 = input.readListBegin();
        _etype58 = _rtmp359.etype;
        _size55 = _rtmp359.size;
        for (var _i60 = 0; _i60 < _size55; ++_i60)
        {
          var elem61 = null;
          elem61 = new Body();
          elem61.read(input);
          this.user_input_bodies.push(elem61);
        }
        input.readListEnd();
      } else {
        input.skip(ftype);
      }
      break;
      case 3:
      if (ftype == Thrift.Type.I32) {
        this.width = input.readI32().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 4:
      if (ftype == Thrift.Type.I32) {
        this.height = input.readI32().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 5:
      if (ftype == Thrift.Type.I32) {
        this.user_input_status = input.readI32().value;
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

Scene.prototype.write = function(output) {
  output.writeStructBegin('Scene');
  if (this.bodies !== null && this.bodies !== undefined) {
    output.writeFieldBegin('bodies', Thrift.Type.LIST, 1);
    output.writeListBegin(Thrift.Type.STRUCT, this.bodies.length);
    for (var iter62 in this.bodies)
    {
      if (this.bodies.hasOwnProperty(iter62))
      {
        iter62 = this.bodies[iter62];
        iter62.write(output);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  if (this.user_input_bodies !== null && this.user_input_bodies !== undefined) {
    output.writeFieldBegin('user_input_bodies', Thrift.Type.LIST, 2);
    output.writeListBegin(Thrift.Type.STRUCT, this.user_input_bodies.length);
    for (var iter63 in this.user_input_bodies)
    {
      if (this.user_input_bodies.hasOwnProperty(iter63))
      {
        iter63 = this.user_input_bodies[iter63];
        iter63.write(output);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  if (this.width !== null && this.width !== undefined) {
    output.writeFieldBegin('width', Thrift.Type.I32, 3);
    output.writeI32(this.width);
    output.writeFieldEnd();
  }
  if (this.height !== null && this.height !== undefined) {
    output.writeFieldBegin('height', Thrift.Type.I32, 4);
    output.writeI32(this.height);
    output.writeFieldEnd();
  }
  if (this.user_input_status !== null && this.user_input_status !== undefined) {
    output.writeFieldBegin('user_input_status', Thrift.Type.I32, 5);
    output.writeI32(this.user_input_status);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

Solution = function(args) {
  this.points = null;
  if (args) {
    if (args.points !== undefined && args.points !== null) {
      this.points = Thrift.copyList(args.points, [IntVector]);
    }
  }
};
Solution.prototype = {};
Solution.prototype.read = function(input) {
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
        var _size64 = 0;
        var _rtmp368;
        this.points = [];
        var _etype67 = 0;
        _rtmp368 = input.readListBegin();
        _etype67 = _rtmp368.etype;
        _size64 = _rtmp368.size;
        for (var _i69 = 0; _i69 < _size64; ++_i69)
        {
          var elem70 = null;
          elem70 = new IntVector();
          elem70.read(input);
          this.points.push(elem70);
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

Solution.prototype.write = function(output) {
  output.writeStructBegin('Solution');
  if (this.points !== null && this.points !== undefined) {
    output.writeFieldBegin('points', Thrift.Type.LIST, 1);
    output.writeListBegin(Thrift.Type.STRUCT, this.points.length);
    for (var iter71 in this.points)
    {
      if (this.points.hasOwnProperty(iter71))
      {
        iter71 = this.points[iter71];
        iter71.write(output);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

Image = function(args) {
  this.values = null;
  this.height = null;
  this.width = null;
  if (args) {
    if (args.values !== undefined && args.values !== null) {
      this.values = Thrift.copyList(args.values, [null]);
    }
    if (args.height !== undefined && args.height !== null) {
      this.height = args.height;
    }
    if (args.width !== undefined && args.width !== null) {
      this.width = args.width;
    }
  }
};
Image.prototype = {};
Image.prototype.read = function(input) {
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
        var _size72 = 0;
        var _rtmp376;
        this.values = [];
        var _etype75 = 0;
        _rtmp376 = input.readListBegin();
        _etype75 = _rtmp376.etype;
        _size72 = _rtmp376.size;
        for (var _i77 = 0; _i77 < _size72; ++_i77)
        {
          var elem78 = null;
          elem78 = input.readI32().value;
          this.values.push(elem78);
        }
        input.readListEnd();
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.I32) {
        this.height = input.readI32().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 3:
      if (ftype == Thrift.Type.I32) {
        this.width = input.readI32().value;
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

Image.prototype.write = function(output) {
  output.writeStructBegin('Image');
  if (this.values !== null && this.values !== undefined) {
    output.writeFieldBegin('values', Thrift.Type.LIST, 1);
    output.writeListBegin(Thrift.Type.I32, this.values.length);
    for (var iter79 in this.values)
    {
      if (this.values.hasOwnProperty(iter79))
      {
        iter79 = this.values[iter79];
        output.writeI32(iter79);
      }
    }
    output.writeListEnd();
    output.writeFieldEnd();
  }
  if (this.height !== null && this.height !== undefined) {
    output.writeFieldBegin('height', Thrift.Type.I32, 2);
    output.writeI32(this.height);
    output.writeFieldEnd();
  }
  if (this.width !== null && this.width !== undefined) {
    output.writeFieldBegin('width', Thrift.Type.I32, 3);
    output.writeI32(this.width);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

