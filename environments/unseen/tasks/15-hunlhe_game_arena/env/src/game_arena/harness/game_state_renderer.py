                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                            

import abc
import io
from PIL import Image
from PIL import ImageDraw


class ImageGenerator(abc.ABC):
  pass                                              

  def __init__(
      self,
      board_size: int = 768,
      background_color: tuple[int, int, int] = (255, 255, 255),
  ):
    pass                               

         
                                                                
                                                            
       
    self._board_size = board_size
    self._background_color = background_color
    self._img = Image.new(
        "RGB", (self._board_size, self._board_size), self._background_color
    )
    self._draw = ImageDraw.Draw(self._img)

  def _get_image_bytes(self) -> bytes:
    pass                                          
    buffer = io.BytesIO()
    self._img.save(buffer, format="PNG")
    return buffer.getvalue()

  @abc.abstractmethod
  def generate_image(self, state_str: str) -> bytes:
    pass                                                                

         
                                                                        
                            
       
    raise NotImplementedError("Subclasses must implement this method.")
