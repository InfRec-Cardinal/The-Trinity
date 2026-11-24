import os, sys
import json
from PIL import Image, ImageDraw
from io import BytesIO
import base64

def pil_image_to_base64(image: Image.Image) -> str:
    pass                               
                                     
       
    buffer = BytesIO()
    image.save(buffer, format="jpeg")  
    image_bytes = buffer.getvalue()
    base64_str = base64.b64encode(image_bytes).decode('utf-8')
    return base64_str

def test_split_image(image, grid_size, add_line=False, resize_only=False):
    width, height = image.size
    m, n = grid_size

    tile_width = width // m
    tile_height = height // n

    resized_image = image.resize((tile_width, tile_height), Image.LANCZOS)
    if add_line:
        resized_image = add_lines(resized_image, grid_size = grid_size)
    if resize_only:
        return resized_image

    parts = []
    for i in range(m):
        for j in range(n):
            left = i * tile_width
            upper = j * tile_height
            right = (i + 1) * tile_width
            lower = (j + 1) * tile_height
            tile = image.crop((left, upper, right, lower))
            parts.append((tile, (left, upper, right, lower)))
    return resized_image, list(zip(*parts))[0]

def add_lines(image, grid_size = (2,2)):
    draw = ImageDraw.Draw(image)
    img_width, img_height = image.size

    if grid_size == (2,2):
        vertical_line = [(img_width // 2, 0), (img_width // 2, img_height)]
        horizontal_line = [(0, img_height // 2), (img_width, img_height // 2)]
        line_color = (255, 255, 255)         
        line_width = 15
        draw.line(vertical_line, fill=line_color, width=line_width)
        draw.line(horizontal_line, fill=line_color, width=line_width)
    
        line_color = (255, 0, 0)       
        line_width = 5
        draw.line(vertical_line, fill=line_color, width=line_width)
        draw.line(horizontal_line, fill=line_color, width=line_width)
    else:
        m, n = grid_size
    
                                                    
        vertical_step = img_width // m
        horizontal_step = img_height // n
    
        line_color = (255, 255, 255)         
        line_width = 15
        for i in range(1, m):
            vertical_line = [(i * vertical_step, 0), (i * vertical_step, img_height)]
            draw.line(vertical_line, fill=line_color, width=line_width)
    
        for j in range(1, n):
            horizontal_line = [(0, j * horizontal_step), (img_width, j * horizontal_step)]
            draw.line(horizontal_line, fill=line_color, width=line_width)
    
        line_color = (255, 0, 0)       
        line_width = 5
        for i in range(1, m):
            vertical_line = [(i * vertical_step, 0), (i * vertical_step, img_height)]
            draw.line(vertical_line, fill=line_color, width=line_width)
    
        for j in range(1, n):
            horizontal_line = [(0, j * horizontal_step), (img_width, j * horizontal_step)]
            draw.line(horizontal_line, fill=line_color, width=line_width)

    return image

def check_bboxes(parts, bboxes, verbose=False):
    results = []
    for part, coords in parts:
        left, upper, right, lower = coords
        part_bboxes = []
        for bbox in bboxes:
            x_left, y_top, x_right, y_lower = bbox
            if x_left >= left and x_right <= right and y_top >= upper and y_lower <= lower:
                part_bboxes.append("whole")
            elif (left <= x_left <= right and upper <= y_top <= lower) or \
                 (left <= x_right <= right and upper <= y_top <= lower) or \
                 (left <= x_left <= right and upper <= y_lower <= lower) or \
                 (left <= x_right <= right and upper <= y_lower <= lower):
                overlap_left = max(left, x_left)
                overlap_upper = max(upper, y_top)
                overlap_right = min(right, x_right)
                overlap_lower = min(lower, y_lower)
                
                              
                overlap_width = max(0, overlap_right - overlap_left)
                overlap_height = max(0, overlap_lower - overlap_upper)
                
                        
                overlap_area = overlap_width * overlap_height
                
                           
                bbox_area = (x_right - x_left) * (y_lower - y_top)
                
                                      
                if overlap_area / bbox_area > 0.1:
                    part_bboxes.append("partial")
            else:
                part_bboxes.append("no")
        if part_bboxes:
            if "partial" in part_bboxes:
                results.append(("partial", coords))
            elif "whole" in part_bboxes:
                results.append((len([x for x in part_bboxes if x == "whole"]), coords))
            else:
                results.append(("no", coords))
        else:
            results.append(("no", coords))
    if verbose:
        return results
    else:
        return [r[0] for r in results]

def save_bbox_images(image, bboxes, output_dir, data_id):
    tgt_dir = os.path.join(output_dir, f'{data_id}')
    if not os.path.exists(tgt_dir):
        os.makedirs(tgt_dir)
    
    for i, bbox in enumerate(bboxes):
        x_left, y_top, x_right, y_lower = bbox
        cropped_image = image.crop((x_left, y_top, x_right, y_lower))
        cropped_image_path = os.path.join(tgt_dir, f'bbox_{i}.jpg')
        cropped_image.save(cropped_image_path)
        
def draw_bboxes(image, bboxes, output_dir, data_id):
    tgt_dir = os.path.join(output_dir, f'{data_id}')

    draw = ImageDraw.Draw(image)

    for bbox in bboxes:
        x_left, y_top, x_right, y_lower = bbox
        draw.rectangle([x_left, y_top, x_right, y_lower], outline="red", width=5)
    image.save(os.path.join(tgt_dir, 'all_bboxes.jpg'))

