  
                                                             
                                                              
                                                        
                                                            
                                                    
                                                             
                                                            
  
                                               
  
                                                             
                                                              
                                                         
                                                           
                                                          
                     
   

                    

   
                                                                   
                                                                   
                                                                 
                                                             
                                                
  
                                                                    
                                                                
  
                                                 
                                                                        
                                                           
             
           
                                                                     
                                                      
                                                    
                                      
   
var Thrift = {
       
                                         
                
                              
                       
       
    Version: '0.13.0',

       
                                            
                
                                                           
                                                                           
                                                       
                                                         
                                                         
                                                                   
                                                          
                                                          
                                                          
                                                                                       
                                                                                                    
                                                      
                                                                                         
                                                                                              
                                                                  
                                                                                                    
                                                                                                     
       
    Type: {
        STOP: 0,
        VOID: 1,
        BOOL: 2,
        BYTE: 3,
        I08: 3,
        DOUBLE: 4,
        I16: 6,
        I32: 8,
        I64: 10,
        STRING: 11,
        UTF7: 11,
        STRUCT: 12,
        MAP: 13,
        SET: 14,
        LIST: 15,
        UTF8: 16,
        UTF16: 17
    },

       
                                                    
                
                                                                           
                                                                                      
                                                                                         
                                                                                              
       
    MessageType: {
        CALL: 1,
        REPLY: 2,
        EXCEPTION: 3,
        ONEWAY: 4
    },

       
                                                                          
                                            
                                                          
       
    objectLength: function(obj) {
        var length = 0;
        for (var k in obj) {
            if (obj.hasOwnProperty(k)) {
                length++;
            }
        }
        return length;
    },

       
                                                           
                                                                                          
                                                                               
                                                                                 
                                                                                       
       
    inherits: function(constructor, superConstructor, name) {
      function F() {}
      F.prototype = superConstructor.prototype;
      constructor.prototype = new F();
      constructor.prototype.name = name || '';
    }
};

   
                                            
               
                  
                                                                                      
                                                                           
   
Thrift.TException = function(message) {
    this.message = message;
};
Thrift.inherits(Thrift.TException, Error, 'TException');

   
                                            
            
                                      
   
Thrift.TException.prototype.getMessage = function() {
    return this.message;
};

   
                                                          
            
                                                                   
                                                                                                         
                                                                                                  
                                                        
                                                                                                                       
                                                                                                                                      
                                                                        
                                                                                                            
                                                        
                                                                                            
                                                        
   
Thrift.TApplicationExceptionType = {
    UNKNOWN: 0,
    UNKNOWN_METHOD: 1,
    INVALID_MESSAGE_TYPE: 2,
    WRONG_METHOD_NAME: 3,
    BAD_SEQUENCE_ID: 4,
    MISSING_RESULT: 5,
    INTERNAL_ERROR: 6,
    PROTOCOL_ERROR: 7,
    INVALID_TRANSFORM: 8,
    INVALID_PROTOCOL: 9,
    UNSUPPORTED_CLIENT_TYPE: 10
};

   
                                                       
               
                              
                                                                                                 
                                                                                         
                                                                                                                                    
  
Thrift.TApplicationException = function(message, code) {
    this.message = message;
    this.code = typeof code === 'number' ? code : 0;
};
Thrift.inherits(Thrift.TApplicationException, Thrift.TException, 'TApplicationException');

   
                                                           
                                                           
   
Thrift.TApplicationException.prototype.read = function(input) {
    while (1) {
        var ret = input.readFieldBegin();

        if (ret.ftype == Thrift.Type.STOP) {
            break;
        }

        var fid = ret.fid;

        switch (fid) {
            case 1:
                if (ret.ftype == Thrift.Type.STRING) {
                    ret = input.readString();
                    this.message = ret.value;
                } else {
                    ret = input.skip(ret.ftype);
                }
                break;
            case 2:
                if (ret.ftype == Thrift.Type.I32) {
                    ret = input.readI32();
                    this.code = ret.value;
                } else {
                    ret = input.skip(ret.ftype);
                }
                break;
           default:
                ret = input.skip(ret.ftype);
                break;
        }

        input.readFieldEnd();
    }

    input.readStructEnd();
};

   
                                                         
                                                            
   
Thrift.TApplicationException.prototype.write = function(output) {
    output.writeStructBegin('TApplicationException');

    if (this.message) {
        output.writeFieldBegin('message', Thrift.Type.STRING, 1);
        output.writeString(this.getMessage());
        output.writeFieldEnd();
    }

    if (this.code) {
        output.writeFieldBegin('type', Thrift.Type.I32, 2);
        output.writeI32(this.code);
        output.writeFieldEnd();
    }

    output.writeFieldStop();
    output.writeStructEnd();
};

   
                                                               
            
                                                             
   
Thrift.TApplicationException.prototype.getCode = function() {
    return this.code;
};

Thrift.TProtocolExceptionType = {
    UNKNOWN: 0,
    INVALID_DATA: 1,
    NEGATIVE_SIZE: 2,
    SIZE_LIMIT: 3,
    BAD_VERSION: 4,
    NOT_IMPLEMENTED: 5,
    DEPTH_LIMIT: 6
};

Thrift.TProtocolException = function TProtocolException(type, message) {
    Error.call(this);
    Error.captureStackTrace(this, this.constructor);
    this.name = this.constructor.name;
    this.type = type;
    this.message = message;
};
Thrift.inherits(Thrift.TProtocolException, Thrift.TException, 'TProtocolException');

   
                                              
                                                                     
                                                                        
                              
               
                                                 
                                                                       
                                                                       
                                                                        
                                         
           
                                                                         
   
Thrift.Transport = Thrift.TXHRTransport = function(url, options) {
    this.url = url;
    this.wpos = 0;
    this.rpos = 0;
    this.useCORS = (options && options.useCORS);
    this.customHeaders = options ? (options.customHeaders ? options.customHeaders : {}): {};
    this.send_buf = '';
    this.recv_buf = '';
};

Thrift.TXHRTransport.prototype = {
       
                                                       
                                                         
       
    getXmlHttpRequestObject: function() {
        try { return new XMLHttpRequest(); } catch (e1) { }
        try { return new ActiveXObject('Msxml2.XMLHTTP'); } catch (e2) { }
        try { return new ActiveXObject('Microsoft.XMLHTTP'); } catch (e3) { }

        throw "Your browser doesn't support XHR.";
    },

       
                                                                            
                                                                              
                                                                            
                                                                       
                                                                           
                                                                    
                                                                      
                                     
       
    flush: function(async, callback) {
        var self = this;
        if ((async && !callback) || this.url === undefined || this.url === '') {
            return this.send_buf;
        }

        var xreq = this.getXmlHttpRequestObject();

        if (xreq.overrideMimeType) {
            xreq.overrideMimeType('application/vnd.apache.thrift.json; charset=utf-8');
        }

        if (callback) {
                                                                        
                                 
            xreq.onreadystatechange =
              (function() {
                var clientCallback = callback;
                return function() {
                  if (this.readyState == 4 && this.status == 200) {
                    self.setRecvBuffer(this.responseText);
                    clientCallback();
                  }
                };
              }());

                                                                        
            xreq.onerror =
                (function() {
                  var clientCallback = callback;
                  return function() {
                      clientCallback();
                  };
                }());

        }

        xreq.open('POST', this.url, !!async);

                             
        Object.keys(self.customHeaders).forEach(function(prop) {
            xreq.setRequestHeader(prop, self.customHeaders[prop]);
        });

        if (xreq.setRequestHeader) {
            xreq.setRequestHeader('Accept', 'application/vnd.apache.thrift.json; charset=utf-8');
            xreq.setRequestHeader('Content-Type', 'application/vnd.apache.thrift.json; charset=utf-8');
        }

        xreq.send(this.send_buf);
        if (async && callback) {
            return;
        }

        if (xreq.readyState != 4) {
            throw 'encountered an unknown ajax ready state: ' + xreq.readyState;
        }

        if (xreq.status != 200) {
            throw 'encountered a unknown request status: ' + xreq.status;
        }

        this.recv_buf = xreq.responseText;
        this.recv_buf_sz = this.recv_buf.length;
        this.wpos = this.recv_buf.length;
        this.rpos = 0;
    },

       
                                                                       
                                                                                               
                                                                    
                                                                                                  
                                                                                             
                                                 
                                                                                        
       
    jqRequest: function(client, postData, args, recv_method) {
        if (typeof jQuery === 'undefined' ||
            typeof jQuery.Deferred === 'undefined') {
            throw 'Thrift.js requires jQuery 1.5+ to use asynchronous requests';
        }

        var thriftTransport = this;

        var jqXHR = jQuery.ajax({
            url: this.url,
            data: postData,
            type: 'POST',
            cache: false,
            contentType: 'application/vnd.apache.thrift.json; charset=utf-8',
            dataType: 'text thrift',
            converters: {
                'text thrift' : function(responseData) {
                    thriftTransport.setRecvBuffer(responseData);
                    var value = recv_method.call(client);
                    return value;
                }
            },
            context: client,
            success: jQuery.makeArray(args).pop(),
            beforeSend: function (xreq) {
                Object.keys(thriftTransport.customHeaders).forEach(function (prop) {
                    xreq.setRequestHeader(prop, thriftTransport.customHeaders[prop]);
                });
            }
        });

        return jqXHR;
    },

       
                                                                  
                                                               
       
    setRecvBuffer: function(buf) {
        this.recv_buf = buf;
        this.recv_buf_sz = this.recv_buf.length;
        this.wpos = this.recv_buf.length;
        this.rpos = 0;
    },

       
                                                                      
                
                                      
       
    isOpen: function() {
        return true;
    },

       
                                                              
       
    open: function() {},

       
                                                               
       
    close: function() {},

       
                                                                   
              
                                                                
                                                       
       
    read: function(len) {
        var avail = this.wpos - this.rpos;

        if (avail === 0) {
            return '';
        }

        var give = len;

        if (avail < len) {
            give = avail;
        }

        var ret = this.read_buf.substr(this.rpos, give);
        this.rpos += give;

                                  
        return ret;
    },

       
                                          
                                                       
       
    readAll: function() {
        return this.recv_buf;
    },

       
                                   
                                                
       
    write: function(buf) {
        this.send_buf = buf;
    },

       
                               
                
                                         
       
    getSendBuffer: function() {
        return this.send_buf;
    }

};


   
                                                    
               
                                                 
                                                                       
                                                                             
                                                                        
                                         
           
                                                                             
   
Thrift.TWebSocketTransport = function(url) {
    this.__reset(url);
};

Thrift.TWebSocketTransport.prototype = {
    __reset: function(url) {
      this.url = url;                               
      this.socket = null;                         
      this.callbacks = [];                           
      this.send_pending = [];                                                
      this.send_buf = '';                                              
      this.recv_buf = '';                       
      this.rb_wpos = 0;                                                     
      this.rb_rpos = 0;                                                   
    },

       
                                                                     
                                                                       
                                      
                                       
                                                                 
                                                      
       
    flush: function(async, callback) {
      var self = this;
      if (this.isOpen()) {
                                                                         
        this.socket.send(this.send_buf);
        this.callbacks.push((function() {
          var clientCallback = callback;
          return function(msg) {
            self.setRecvBuffer(msg);
            if (clientCallback) {
                clientCallback();
            }
          };
        }()));
      } else {
                                           
        this.send_pending.push({
          buf: this.send_buf,
          cb: callback
        });
      }
    },

    __onOpen: function() {
       var self = this;
       if (this.send_pending.length > 0) {
                                                                  
                               
          this.send_pending.forEach(function(elem) {
             self.socket.send(elem.buf);
             self.callbacks.push((function() {
               var clientCallback = elem.cb;
               return function(msg) {
                  self.setRecvBuffer(msg);
                  clientCallback();
               };
             }()));
          });
          this.send_pending = [];
       }
    },

    __onClose: function(evt) {
      this.__reset(this.url);
    },

    __onMessage: function(evt) {
      if (this.callbacks.length) {
        this.callbacks.shift()(evt.data);
      }
    },

    __onError: function(evt) {
      console.log('Thrift WebSocket Error: ' + evt.toString());
      this.socket.close();
    },

       
                                                              
                                                                    
       
    setRecvBuffer: function(buf) {
        this.recv_buf = buf;
        this.recv_buf_sz = this.recv_buf.length;
        this.wpos = this.recv_buf.length;
        this.rpos = 0;
    },

       
                                            
                
                         
       
    isOpen: function() {
        return this.socket && this.socket.readyState == this.socket.OPEN;
    },

       
                                     
       
    open: function() {
                                                          
      if (this.socket && this.socket.readyState != this.socket.CLOSED) {
        return;
      }
                                                      
      this.socket = new WebSocket(this.url);
      this.socket.onopen = this.__onOpen.bind(this);
      this.socket.onmessage = this.__onMessage.bind(this);
      this.socket.onerror = this.__onError.bind(this);
      this.socket.onclose = this.__onClose.bind(this);
    },

       
                                      
       
    close: function() {
      this.socket.close();
    },

       
                                                                   
              
                                                                
                                                       
       
    read: function(len) {
        var avail = this.wpos - this.rpos;

        if (avail === 0) {
            return '';
        }

        var give = len;

        if (avail < len) {
            give = avail;
        }

        var ret = this.read_buf.substr(this.rpos, give);
        this.rpos += give;

                                  
        return ret;
    },

       
                                          
                                                       
       
    readAll: function() {
        return this.recv_buf;
    },

       
                                   
                                                
       
    write: function(buf) {
        this.send_buf = buf;
    },

       
                               
                
                                         
       
    getSendBuffer: function() {
        return this.send_buf;
    }

};

   
                                               
               
                                                                            
                                                                               
                                                                           
                                      
           
                                                      
   
Thrift.TJSONProtocol = Thrift.Protocol = function(transport) {
    this.tstack = [];
    this.tpos = [];
    this.transport = transport;
};

   
                                        
            
                           
   
Thrift.Protocol.Type = {};
Thrift.Protocol.Type[Thrift.Type.BOOL] = '"tf"';
Thrift.Protocol.Type[Thrift.Type.BYTE] = '"i8"';
Thrift.Protocol.Type[Thrift.Type.I16] = '"i16"';
Thrift.Protocol.Type[Thrift.Type.I32] = '"i32"';
Thrift.Protocol.Type[Thrift.Type.I64] = '"i64"';
Thrift.Protocol.Type[Thrift.Type.DOUBLE] = '"dbl"';
Thrift.Protocol.Type[Thrift.Type.STRUCT] = '"rec"';
Thrift.Protocol.Type[Thrift.Type.STRING] = '"str"';
Thrift.Protocol.Type[Thrift.Type.MAP] = '"map"';
Thrift.Protocol.Type[Thrift.Type.LIST] = '"lst"';
Thrift.Protocol.Type[Thrift.Type.SET] = '"set"';

   
                                        
            
                           
   
Thrift.Protocol.RType = {};
Thrift.Protocol.RType.tf = Thrift.Type.BOOL;
Thrift.Protocol.RType.i8 = Thrift.Type.BYTE;
Thrift.Protocol.RType.i16 = Thrift.Type.I16;
Thrift.Protocol.RType.i32 = Thrift.Type.I32;
Thrift.Protocol.RType.i64 = Thrift.Type.I64;
Thrift.Protocol.RType.dbl = Thrift.Type.DOUBLE;
Thrift.Protocol.RType.rec = Thrift.Type.STRUCT;
Thrift.Protocol.RType.str = Thrift.Type.STRING;
Thrift.Protocol.RType.map = Thrift.Type.MAP;
Thrift.Protocol.RType.lst = Thrift.Type.LIST;
Thrift.Protocol.RType.set = Thrift.Type.SET;

   
                                    
            
                          
                            
   
 Thrift.Protocol.Version = 1;

Thrift.Protocol.prototype = {
       
                                        
                
                                                            
       
    getTransport: function() {
        return this.transport;
    },

       
                                                        
                                                         
                                                                         
                                                                                            
       
    writeMessageBegin: function(name, messageType, seqid) {
        this.tstack = [];
        this.tpos = [];

        this.tstack.push([Thrift.Protocol.Version, '"' +
            name + '"', messageType, seqid]);
    },

       
                                                  
       
    writeMessageEnd: function() {
        var obj = this.tstack.pop();

        this.wobj = this.tstack.pop();
        this.wobj.push(obj);

        this.wbuf = '[' + this.wobj.join(',') + ']';

        this.transport.write(this.wbuf);
     },


       
                                            
                                                     
       
    writeStructBegin: function(name) {
        this.tpos.push(this.tstack.length);
        this.tstack.push({});
    },

       
                                      
       
    writeStructEnd: function() {

        var p = this.tpos.pop();
        var struct = this.tstack[p];
        var str = '{';
        var first = true;
        for (var key in struct) {
            if (first) {
                first = false;
            } else {
                str += ',';
            }

            str += key + ':' + struct[key];
        }

        str += '}';
        this.tstack[p] = str;
    },

       
                                                  
                                                    
                                                                            
                                                               
       
    writeFieldBegin: function(name, fieldType, fieldId) {
        this.tpos.push(this.tstack.length);
        this.tstack.push({ 'fieldId': '"' +
            fieldId + '"', 'fieldType': Thrift.Protocol.Type[fieldType]
        });

    },

       
                                     
       
    writeFieldEnd: function() {
        var value = this.tstack.pop();
        var fieldInfo = this.tstack.pop();

        this.tstack[this.tstack.length - 1][fieldInfo.fieldId] = '{' +
            fieldInfo.fieldType + ':' + value + '}';
        this.tpos.pop();
    },

       
                                                            
       
    writeFieldStop: function() {
            
    },

       
                                                    
                                                               
                                                                 
                                                                            
       
    writeMapBegin: function(keyType, valType, size) {
        this.tpos.push(this.tstack.length);
        this.tstack.push([Thrift.Protocol.Type[keyType],
            Thrift.Protocol.Type[valType], 0]);
    },

       
                                   
       
    writeMapEnd: function() {
        var p = this.tpos.pop();

        if (p == this.tstack.length) {
            return;
        }

        if ((this.tstack.length - p - 1) % 2 !== 0) {
            this.tstack.push('');
        }

        var size = (this.tstack.length - p - 1) / 2;

        this.tstack[p][this.tstack[p].length - 1] = size;

        var map = '}';
        var first = true;
        while (this.tstack.length > p + 1) {
            var v = this.tstack.pop();
            var k = this.tstack.pop();
            if (first) {
                first = false;
            } else {
                map = ',' + map;
            }

            if (! isNaN(k)) { k = '"' + k + '"'; }                                 
            map = k + ':' + v + map;
        }
        map = '{' + map;

        this.tstack[p].push(map);
        this.tstack[p] = '[' + this.tstack[p].join(',') + ']';
    },

       
                                                     
                                                                     
                                                                 
       
    writeListBegin: function(elemType, size) {
        this.tpos.push(this.tstack.length);
        this.tstack.push([Thrift.Protocol.Type[elemType], size]);
    },

       
                                    
       
    writeListEnd: function() {
        var p = this.tpos.pop();

        while (this.tstack.length > p + 1) {
            var tmpVal = this.tstack[p + 1];
            this.tstack.splice(p + 1, 1);
            this.tstack[p].push(tmpVal);
        }

        this.tstack[p] = '[' + this.tstack[p].join(',') + ']';
    },

       
                                                    
                                                                     
                                                                 
       
    writeSetBegin: function(elemType, size) {
        this.tpos.push(this.tstack.length);
        this.tstack.push([Thrift.Protocol.Type[elemType], size]);
    },

       
                                   
       
    writeSetEnd: function() {
        var p = this.tpos.pop();

        while (this.tstack.length > p + 1) {
            var tmpVal = this.tstack[p + 1];
            this.tstack.splice(p + 1, 1);
            this.tstack[p].push(tmpVal);
        }

        this.tstack[p] = '[' + this.tstack[p].join(',') + ']';
    },

                               
    writeBool: function(value) {
        this.tstack.push(value ? 1 : 0);
    },

                              
    writeByte: function(i8) {
        this.tstack.push(i8);
    },

                              
    writeI16: function(i16) {
        this.tstack.push(i16);
    },

                              
    writeI32: function(i32) {
        this.tstack.push(i32);
    },

                              
    writeI64: function(i64) {
        if (typeof i64 === 'number') {
            this.tstack.push(i64);
        } else {
            this.tstack.push(Int64Util.toDecimalString(i64));
        }
    },

                              
    writeDouble: function(dbl) {
        this.tstack.push(dbl);
    },

                              
    writeString: function(str) {
                                                             
        if (str === null) {
            this.tstack.push(null);
        } else {
                                                               
            var escapedString = '';
            for (var i = 0; i < str.length; i++) {
                var ch = str.charAt(i);                                 
                if (ch === '\"') {
                    escapedString += '\\\"';                    
                } else if (ch === '\\') {                         
                    escapedString += '\\\\';                                 
                } else if (ch === '\b') {                                    
                    escapedString += '\\b';                      
                } else if (ch === '\f') {                                   
                    escapedString += '\\f';                      
                } else if (ch === '\n') {                                  
                    escapedString += '\\n';                      
                } else if (ch === '\r') {                                 
                    escapedString += '\\r';                      
                } else if (ch === '\t') {                              
                    escapedString += '\\t';                      
                } else {
                    escapedString += ch;                                   
                }
            }
            this.tstack.push('"' + escapedString + '"');
        }
    },

                              
    writeBinary: function(binary) {
        var str = '';
        if (typeof binary == 'string') {
            str = binary;
        } else if (binary instanceof Uint8Array) {
            var arr = binary;
            for (var i = 0; i < arr.length; ++i) {
                str += String.fromCharCode(arr[i]);
            }
        } else {
            throw new TypeError('writeBinary only accepts String or Uint8Array.');
        }
        this.tstack.push('"' + btoa(str) + '"');
    },

       
             
                                       
                                                                 
                                                                       
                                                                                        
       
       
                                               
                                            
       
    readMessageBegin: function() {
        this.rstack = [];
        this.rpos = [];

        received = this.transport.readAll();

        if (typeof JSONInt64 !== 'undefined' && typeof JSONInt64.parse === 'function') {
            this.robj = JSONInt64.parse(received);
        } else if (typeof JSON !== 'undefined' && typeof JSON.parse === 'function') {
            this.robj = JSON.parse(received);
        } else if (typeof jQuery !== 'undefined') {
            this.robj = jQuery.parseJSON(received);
        } else {
            this.robj = eval(received);
        }

        var r = {};
        var version = this.robj.shift();

        if (version != Thrift.Protocol.Version) {
            throw 'Wrong thrift protocol version: ' + version;
        }

        r.fname = this.robj.shift();
        r.mtype = this.robj.shift();
        r.rseqid = this.robj.shift();


                             
        this.rstack.push(this.robj.shift());

        return r;
    },

                                             
    readMessageEnd: function() {
    },

       
                                              
                                                                
                                                                        
       
    readStructBegin: function(name) {
        var r = {};
        r.fname = '';

                                            
        if (this.rstack[this.rstack.length - 1] instanceof Array) {
            this.rstack.push(this.rstack[this.rstack.length - 1].shift());
        }

        return r;
    },

                                            
    readStructEnd: function() {
        if (this.rstack[this.rstack.length - 2] instanceof Array) {
            this.rstack.pop();
        }
    },

       
             
                                     
                                                                    
                                                                  
                                                                   
       
       
                                             
                                          
       
    readFieldBegin: function() {
        var r = {};

        var fid = -1;
        var ftype = Thrift.Type.STOP;

                       
        for (var f in (this.rstack[this.rstack.length - 1])) {
            if (f === null) {
              continue;
            }

            fid = parseInt(f, 10);
            this.rpos.push(this.rstack.length);

            var field = this.rstack[this.rstack.length - 1][fid];

                                             
            delete this.rstack[this.rstack.length - 1][fid];

            this.rstack.push(field);

            break;
        }

        if (fid != -1) {

                                                            
                                
            for (var i in (this.rstack[this.rstack.length - 1])) {
                if (Thrift.Protocol.RType[i] === null) {
                    continue;
                }

                ftype = Thrift.Protocol.RType[i];
                this.rstack[this.rstack.length - 1] =
                    this.rstack[this.rstack.length - 1][i];
            }
        }

        r.fname = '';
        r.ftype = ftype;
        r.fid = fid;

        return r;
    },

                                           
    readFieldEnd: function() {
        var pos = this.rpos.pop();

                                                  
        while (this.rstack.length > pos) {
            this.rstack.pop();
        }

    },

       
             
                                   
                                                                
                                                                  
                                                                   
       
       
                                           
                                        
       
    readMapBegin: function() {
        var map = this.rstack.pop();
        var first = map.shift();
        if (first instanceof Array) {
          this.rstack.push(map);
          map = first;
          first = map.shift();
        }

        var r = {};
        r.ktype = Thrift.Protocol.RType[first];
        r.vtype = Thrift.Protocol.RType[map.shift()];
        r.size = map.shift();

        this.rpos.push(this.rstack.length);
        this.rstack.push(map.shift());

        return r;
    },

                                         
    readMapEnd: function() {
        this.readFieldEnd();
    },

       
             
                                   
                                                                    
                                                                          
       
       
                                            
                                        
       
    readListBegin: function() {
        var list = this.rstack[this.rstack.length - 1];

        var r = {};
        r.etype = Thrift.Protocol.RType[list.shift()];
        r.size = list.shift();

        this.rpos.push(this.rstack.length);
        this.rstack.push(list.shift());

        return r;
    },

                                          
    readListEnd: function() {
        var pos = this.rpos.pop() - 2;
        var st = this.rstack;
        st.pop();
        if (st instanceof Array && st.length > pos && st[pos].length > 0) {
          st.push(st[pos].shift());
        }
    },

       
                                           
                                        
       
    readSetBegin: function(elemType, size) {
        return this.readListBegin(elemType, size);
    },

                                         
    readSetEnd: function() {
        return this.readListEnd();
    },

                                                      
                                                           
                                                         
    readBool: function() {
        var r = this.readI32();

        if (r !== null && r.value == '1') {
            r.value = true;
        } else {
            r.value = false;
        }

        return r;
    },

                                                              
                                                  
    readByte: function() {
        return this.readI32();
    },

                                                              
                                                  
    readI16: function() {
        return this.readI32();
    },

                                                              
                                                  
    readI32: function(f) {
        if (f === undefined) {
            f = this.rstack[this.rstack.length - 1];
        }

        var r = {};

        if (f instanceof Array) {
            if (f.length === 0) {
                r.value = undefined;
            } else {
                if (!f.isReversed) {
                    f.reverse();
                    f.isReversed = true;
                }
                r.value = f.pop();
            }
        } else if (f instanceof Object) {
           for (var i in f) {
                if (i === null) {
                  continue;
                }
                this.rstack.push(f[i]);
                delete f[i];

                r.value = i;
                break;
           }
        } else {
            r.value = f;
            this.rstack.pop();
        }

        return r;
    },

                                                              
                                                  
    readI64: function(f) {
        if (f === undefined) {
            f = this.rstack[this.rstack.length - 1];
        }

        var r = {};

        if (f instanceof Array) {
            if (f.length === 0) {
                r.value = undefined;
            } else {
                if (!f.isReversed) {
                    f.reverse();
                    f.isReversed = true;
                }
                r.value = f.pop();
            }
        } else if (f instanceof Object) {
            var int64Object = true;
            var objectKeys = Object.keys(f).sort();
            var int64Keys = ['buffer', 'offset'];
            if (objectKeys.length !== int64Keys.length) {
                int64Object = false;
            }
            for (var it=0; int64Object && it < objectKeys.length; ++it) {
                if (objectKeys[it] !== int64Keys[it]) {
                    int64Object = false;
                }
            }
            if (int64Object) {
                r.value = f;
            } else {
                for (var i in f) {
                    if (i === null) {
                    continue;
                    }
                    this.rstack.push(f[i]);
                    delete f[i];

                    r.value = i;
                    break;
                }
            }
        } else {
            r.value = f;
            this.rstack.pop();
        }
        return r;
    },

                                                              
                                                  
    readDouble: function() {
        return this.readI32();
    },

                                                              
                                                  
    readString: function() {
        var r = this.readI32();
        return r;
    },

                                                              
                                                  
    readBinary: function() {
        var r = this.readI32();
        r.value = atob(r.value);
        return r;
    },

       
                                              
    skip: function(type) {
        var ret, i;
        switch (type) {
            case Thrift.Type.BOOL:
                return this.readBool();

            case Thrift.Type.BYTE:
                return this.readByte();

            case Thrift.Type.I16:
                return this.readI16();

            case Thrift.Type.I32:
                return this.readI32();

            case Thrift.Type.I64:
                return this.readI64();

            case Thrift.Type.DOUBLE:
                return this.readDouble();

            case Thrift.Type.STRING:
                return this.readString();

            case Thrift.Type.STRUCT:
                this.readStructBegin();
                while (true) {
                    ret = this.readFieldBegin();
                    if (ret.ftype == Thrift.Type.STOP) {
                        break;
                    }
                    this.skip(ret.ftype);
                    this.readFieldEnd();
                }
                this.readStructEnd();
                return null;

            case Thrift.Type.MAP:
                ret = this.readMapBegin();
                for (i = 0; i < ret.size; i++) {
                    if (i > 0) {
                        if (this.rstack.length > this.rpos[this.rpos.length - 1] + 1) {
                            this.rstack.pop();
                        }
                    }
                    this.skip(ret.ktype);
                    this.skip(ret.vtype);
                }
                this.readMapEnd();
                return null;

            case Thrift.Type.SET:
                ret = this.readSetBegin();
                for (i = 0; i < ret.size; i++) {
                    this.skip(ret.etype);
                }
                this.readSetEnd();
                return null;

            case Thrift.Type.LIST:
                ret = this.readListBegin();
                for (i = 0; i < ret.size; i++) {
                    this.skip(ret.etype);
                }
                this.readListEnd();
                return null;

            default:
                throw new Thrift.TProtocolException(Thrift.TProtocolExceptionType.INVALID_DATA);
        }
    }
};


   
                                                                                  
               
   
Thrift.MultiplexProtocol = function(srvName, trans, strictRead, strictWrite) {
    Thrift.Protocol.call(this, trans, strictRead, strictWrite);
    this.serviceName = srvName;
};
Thrift.inherits(Thrift.MultiplexProtocol, Thrift.Protocol, 'multiplexProtocol');

                                                    
Thrift.MultiplexProtocol.prototype.writeMessageBegin = function(name, type, seqid) {

    if (type === Thrift.MessageType.CALL || type === Thrift.MessageType.ONEWAY) {
        Thrift.Protocol.prototype.writeMessageBegin.call(this, this.serviceName + ':' + name, type, seqid);
    } else {
        Thrift.Protocol.prototype.writeMessageBegin.call(this, name, type, seqid);
    }
};

Thrift.Multiplexer = function() {
    this.seqid = 0;
};

                                                            
               
                                                                    
                                                               
                                                                                                  
           
                                        
                                                                               
                                                    
                                                                                
  
Thrift.Multiplexer.prototype.createClient = function(serviceName, SCl, transport) {
    if (SCl.Client) {
        SCl = SCl.Client;
    }
    var self = this;
    SCl.prototype.new_seqid = function() {
        self.seqid += 1;
        return self.seqid;
    };
    var client = new SCl(new Thrift.MultiplexProtocol(serviceName, transport));

    return client;
};



var copyList, copyMap;

copyList = function(lst, types) {

  if (!lst) {return lst; }

  var type;

  if (types.shift === undefined) {
    type = types;
  }
  else {
    type = types[0];
  }
  var Type = type;

  var len = lst.length, result = [], i, val;
  for (i = 0; i < len; i++) {
    val = lst[i];
    if (type === null) {
      result.push(val);
    }
    else if (type === copyMap || type === copyList) {
      result.push(type(val, types.slice(1)));
    }
    else {
      result.push(new Type(val));
    }
  }
  return result;
};

copyMap = function(obj, types) {

  if (!obj) {return obj; }

  var type;

  if (types.shift === undefined) {
    type = types;
  }
  else {
    type = types[0];
  }
  var Type = type;

  var result = {}, val;
  for (var prop in obj) {
    if (obj.hasOwnProperty(prop)) {
      val = obj[prop];
      if (type === null) {
        result[prop] = val;
      }
      else if (type === copyMap || type === copyList) {
        result[prop] = type(val, types.slice(1));
      }
      else {
        result[prop] = new Type(val);
      }
    }
  }
  return result;
};

Thrift.copyMap = copyMap;
Thrift.copyList = copyList;
