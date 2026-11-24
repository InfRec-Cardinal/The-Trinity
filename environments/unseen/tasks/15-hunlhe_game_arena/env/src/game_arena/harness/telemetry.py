                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                               

from typing import Callable, Protocol


class FailedTelemetryCallbackError(Exception):
  pass                                             


class TelemetrySendFn(Protocol):
  pass                                                         

  def __call__(self, module: str, **kwargs) -> None:
    ...

SEND: TelemetrySendFn = lambda module, **kwargs: None


def get_logger(module: str) -> Callable[..., None]:
  pass                                                                           
                                                 
  def logger(**kwargs):
    return SEND(module=module, **kwargs)
  return logger


def set_exporter(send_fn: TelemetrySendFn) -> None:
  pass                                                     
  global SEND
  SEND = send_fn
