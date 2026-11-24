                                                                  

import base64
import io
import logging
import os
import random
import shutil
import socket
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal, overload

import cairosvg
import docker
from PIL import Image
from ahocorapy.keywordtree import KeywordTree

from ale_bench.constants import DEFAULT_CACHE_DIR

logger = logging.getLogger(__name__)


        
@contextmanager
def docker_client() -> Generator[docker.DockerClient, None, None]:
    pass                                 

           
                                               

       
    client = docker.from_env()
    try:
        yield client
    finally:
        client.close()


       
def get_cache_dir() -> Path:
    pass                                     

            
                                  

       
    cache_dir_str = os.environ.get("ALE_BENCH_CACHE", None)
    if cache_dir_str is None:
        return DEFAULT_CACHE_DIR
    return Path(cache_dir_str).expanduser().resolve()


def clear_cache() -> None:
    pass                                          
    cache_dir = get_cache_dir()
    if cache_dir.is_dir():
        logger.info("Clearing cache directory: %s", cache_dir)
        shutil.rmtree(cache_dir)


      
def get_local_data_dir() -> Path | None:
    pass                                          

            
                                                                       

       
    data_dir_str = os.environ.get("ALE_BENCH_DATA", None)
    if data_dir_str is None:
        return None
    data_dir = Path(data_dir_str).expanduser().resolve()
    if not data_dir.is_dir():
        logger.warning("Data directory does not exist: %s", data_dir)
        return None
    return data_dir


def dir_tree(
    dir_path: Path,
    prefix: str = "",
) -> Generator[str, None, None]:
    pass                                          

         
                                                   
                                                                                  

           
                                                 

       
    if not dir_path.is_dir():
        msg = f"{dir_path} is not a directory."
        raise ValueError(msg)
    tee = "├── "
    last = "└── "
    branch = "│   "
    space = "    "
    contents = list(dir_path.iterdir())
    pointers = [tee] * (len(contents) - 1) + [last]
    for pointer, path in zip(pointers, contents, strict=True):
        yield prefix + pointer + path.name
        if path.is_dir():
            extension = branch if pointer == tee else space
            yield from dir_tree(path, prefix + extension)


def print_dir_tree(dir_path: Path) -> None:
    pass                                         

         
                                                   

       
    for line in dir_tree(dir_path):
        print(line)              


         
def text_image_contents_to_openai(contents: list[str | Image.Image]) -> list[dict[str, str | dict[str, str]]]:
    pass                                     

         
                                                                    

            
                                                     

       
    openai_contents: list[dict[str, str | dict[str, str]]] = []
    for content in contents:
        if isinstance(content, str):
            openai_contents.append({"type": "text", "text": content})
        elif isinstance(content, Image.Image):
            openai_contents.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{pil_to_base64jpeg(content)}"},
                }
            )
        else:
            msg = "The content is not a str or a PIL.Image.Image."
            raise TypeError(msg)
    return openai_contents


@overload
def parse_statement(
    statement: str,
    images: dict[str, Image.Image | list[Image.Image]],
    ignore_video: bool = False,
    extract_video_frame: Literal["first", "last", "all"] = "all",
    return_openai: Literal[False] = False,
) -> list[str | Image.Image]: ...


@overload
def parse_statement(
    statement: str,
    images: dict[str, Image.Image | list[Image.Image]],
    ignore_video: bool = False,
    extract_video_frame: Literal["first", "last", "all"] = "all",
    return_openai: Literal[True] = True,
) -> list[dict[str, str | dict[str, str]]]: ...


@overload
def parse_statement(
    statement: str,
    images: dict[str, Image.Image | list[Image.Image]],
    ignore_video: bool = False,
    extract_video_frame: Literal["first", "last", "all"] = "all",
    return_openai: bool = False,
) -> list[str | Image.Image] | list[dict[str, str | dict[str, str]]]: ...


def parse_statement(
    statement: str,
    images: dict[str, Image.Image | list[Image.Image]],
    ignore_video: bool = False,
    extract_video_frame: Literal["first", "last", "all"] = "all",
    return_openai: bool = False,
) -> list[str | Image.Image] | list[dict[str, str | dict[str, str]]]:
    pass                                                                    

                                                          

         
                                               
                                                                                         
                                                                                                             
                                                                                       
                                                                                                    
                                                                                 
                                                                                                                 
                                                                                                          

            
                                                                        
                                                                                

       
                                                                             
    kwtree = KeywordTree(case_insensitive=False)
    for image_name, image_value in images.items():
        if isinstance(image_value, list) and ignore_video:
            continue                
        kwtree.add(image_name)
    kwtree.finalize()
    matches = kwtree.search_all(statement)

                                                             
    contents: list[str | Image.Image] = []
    if matches is None:                                         
        contents.append(statement)
        if return_openai:
            return text_image_contents_to_openai(contents)
        return contents

                                                          
    matches = sorted(matches, key=lambda x: x[1])                           
    current_idx = 0
    for matched_image, idx in matches:
        contents.append(statement[current_idx:idx])
        image = images[matched_image]
        if isinstance(image, list):
            video_frames: list[Image.Image] = [frame for frame in image if isinstance(frame, Image.Image)]
            if extract_video_frame == "first":
                contents.append(video_frames[0])
            elif extract_video_frame == "last":
                contents.append(video_frames[-1])
            elif extract_video_frame == "all":
                contents.extend(video_frames)
            else:
                msg = f"`extract_video_frame` must be 'first', 'last', or 'all'. Got: {extract_video_frame}"
                raise ValueError(msg)
        else:
            contents.append(image)
        current_idx = idx + len(matched_image)
    contents.append(statement[current_idx:])

                                                        
    if return_openai:
        return text_image_contents_to_openai(contents)
    return contents


         
def find_free_port(min_port: int = 9000, max_port: int = 65535) -> int:
    pass                                       

         
                                                                        
                                                                         

            
                                

           
                                                                      

       
    ports = list(range(min_port, max_port + 1))
    random.shuffle(ports)
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("", port))
            except OSError:
                continue
            else:
                return port
    msg = f"No free ports found in range {min_port}-{max_port}."
    raise RuntimeError(msg)


       
def base64_to_pil(base64_str: str) -> Image.Image:
    pass                                      

         
                                                         

            
                                   

       
    image_data = base64.b64decode(base64_str)
    image = Image.open(io.BytesIO(image_data))
    return image.convert(image.mode)                                                                           


def pil_to_base64(image: Image.Image, image_format: Literal["JPEG", "PNG"] = "PNG") -> str:
    pass                                      

         
                                           
                                                                                                  

            
                                            

       
    buffer = io.BytesIO()
    image.save(buffer, format=image_format)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def pil_to_base64jpeg(image: Image.Image) -> str:
    pass                                                      

         
                                           

            
                                                 

       
    return pil_to_base64(image.convert("RGB"), image_format="JPEG")


def read_svg(svg_text: str, size: int | tuple[int, int] = 1000) -> Image.Image:
    pass                                       

         
                                     
                                                                                               
                                                                                                                   

            
                                              

           
                                             

       
    if len(svg_text) == 0:
        msg = "SVG text is empty."
        raise ValueError(msg)
    if isinstance(size, int):
        size = (size, size)
    width, height = size
    buffer = io.BytesIO()
    cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"),
        output_width=width,
        output_height=height,
        background_color="white",
        write_to=buffer,
    )
    return Image.open(buffer).convert("RGB")
