  
                                            
  
                                                                   
  


Color = {
  'WHITE' : 0,
  'BLACK' : 6,
  'GRAY' : 5,
  'GREEN' : 2,
  'BLUE' : 3,
  'PURPLE' : 4,
  'RED' : 1,
  'LIGHT_RED' : 7
};
Error_message = function(args) {
  this.errorNo = null;
  this.errorMsg = null;
  if (args) {
    if (args.errorNo !== undefined && args.errorNo !== null) {
      this.errorNo = args.errorNo;
    }
    if (args.errorMsg !== undefined && args.errorMsg !== null) {
      this.errorMsg = args.errorMsg;
    }
  }
};
Thrift.inherits(Error_message, Thrift.TException);
Error_message.prototype.name = 'Error_message';
Error_message.prototype.read = function(input) {
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
        this.errorNo = input.readI32().value;
      } else {
        input.skip(ftype);
      }
      break;
      case 2:
      if (ftype == Thrift.Type.STRING) {
        this.errorMsg = input.readString().value;
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

Error_message.prototype.write = function(output) {
  output.writeStructBegin('Error_message');
  if (this.errorNo !== null && this.errorNo !== undefined) {
    output.writeFieldBegin('errorNo', Thrift.Type.I32, 1);
    output.writeI32(this.errorNo);
    output.writeFieldEnd();
  }
  if (this.errorMsg !== null && this.errorMsg !== undefined) {
    output.writeFieldBegin('errorMsg', Thrift.Type.STRING, 2);
    output.writeString(this.errorMsg);
    output.writeFieldEnd();
  }
  output.writeFieldStop();
  output.writeStructEnd();
  return;
};

USER_BODY_COLOR = 1;
