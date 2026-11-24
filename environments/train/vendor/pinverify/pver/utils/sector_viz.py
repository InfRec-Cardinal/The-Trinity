                                                        

                                                                    
                                                   
                                                                    
                                                          
   

import math
import os
import tempfile
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Set, Optional, Tuple


                                                               
SECTOR_NAMES = ["Front", "Front-Left", "Back-Left", "Back", "Back-Right", "Front-Right"]

                                                                                              
FILL_CURRENT = (255, 255, 0, 140)                                     
FILL_VISITED = (0, 200, 0, 140)                                         
FILL_TRAP = (255, 50, 50, 140)                                   
FILL_UNVISITED = (255, 255, 255, 140)                                

                                             
TEXT_CURRENT = (255, 255, 0)
TEXT_VISITED = (0, 220, 0)
TEXT_TRAP = (255, 80, 80)
TEXT_UNVISITED = (255, 255, 255)

                   
COLOR_LINE = (80, 80, 80, 140)                                            
COLOR_CIRCLE = (80, 80, 80, 140)                                   


def draw_sector_overlay(
    img_path: str,
    bbox_xyxy: Optional[list],
    current_rel_idx: int,
    visited_rel_indices: Set[int],
    visited_sector_visibility: Dict[int, bool],
    num_sectors: int = 6,
    output_path: Optional[str] = None,
) -> str:
    pass                                                               

                                                                       
                                    
                                        
                                                      
                                   

            
                                         
       
    img = Image.open(img_path).convert("RGBA")
    w, h = img.size

                                                                 
    if bbox_xyxy and len(bbox_xyxy) == 4:
        cx = (bbox_xyxy[0] + bbox_xyxy[2]) / 2
        cy = (bbox_xyxy[1] + bbox_xyxy[3]) / 2
    else:
        cx, cy = w / 2, h / 2

                    
    max_radius_x = min(cx, w - cx) * 0.85
    max_radius_y = min(cy, h - cy) * 0.85
    radius = min(max_radius_x, max_radius_y, max(w, h) * 0.4)
    radius = max(radius, 60)

    font = _get_font(size=max(14, int(radius * 0.14)))

    sector_span = 360.0 / num_sectors                  

                                                            
    sector_center_angles = {}
    for i in range(num_sectors):
        angle = 90.0 + i * sector_span
        sector_center_angles[i] = angle % 360

                                                          
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)

    bbox_circle = [cx - radius, cy - radius, cx + radius, cy + radius]

    for i in range(num_sectors):
                              
        if i == current_rel_idx:
            fill = FILL_CURRENT
        elif i in visited_rel_indices:
            vis = visited_sector_visibility.get(i, True)
            fill = FILL_VISITED if vis else FILL_TRAP
        else:
            fill = FILL_UNVISITED

        start_angle = sector_center_angles[i] - sector_span / 2
        end_angle = sector_center_angles[i] + sector_span / 2

        ov_draw.pieslice(bbox_circle, start=start_angle, end=end_angle, fill=fill)

                                                       
    for i in range(num_sectors):
        boundary_angle_deg = sector_center_angles[i] - sector_span / 2
        boundary_angle_rad = math.radians(boundary_angle_deg)
        ex = cx + radius * math.cos(boundary_angle_rad)
        ey = cy + radius * math.sin(boundary_angle_rad)
        ov_draw.line([(cx, cy), (ex, ey)], fill=COLOR_LINE, width=2)

                             
    ov_draw.ellipse(bbox_circle, outline=COLOR_CIRCLE, width=2)

                                           
    img = Image.alpha_composite(img, overlay)

                                                               
    draw = ImageDraw.Draw(img)
    for i in range(num_sectors):
        angle_rad = math.radians(sector_center_angles[i])

                    
        if i == current_rel_idx:
            text_color = TEXT_CURRENT
        elif i in visited_rel_indices:
            vis = visited_sector_visibility.get(i, True)
            text_color = TEXT_VISITED if vis else TEXT_TRAP
        else:
            text_color = TEXT_UNVISITED

        name = SECTOR_NAMES[i] if i < len(SECTOR_NAMES) else f"Sector-{i}"
        if i == current_rel_idx:
            name += " (YOU)"

        label_r = radius * 0.65
        lx = cx + label_r * math.cos(angle_rad)
        ly = cy + label_r * math.sin(angle_rad)

        _draw_text_with_bg(draw, (lx, ly), name, font, text_color)

                      
    img_rgb = img.convert("RGB")
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".jpg", prefix="secviz_")
        os.close(fd)

    img_rgb.save(output_path, quality=90)
    return output_path


def _get_font(size=16):
    pass                                                                                
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        pass
    for fp in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
               "C:/Windows/Fonts/arial.ttf"]:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _draw_text_with_bg(draw: ImageDraw.Draw, center: Tuple[float, float], text: str,
                       font, color: Tuple[int, ...], bg_alpha: int = 180):
    pass                                                          
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    x = center[0] - tw / 2
    y = center[1] - th / 2

    pad = 4
                                                           
    bg_color = (0, 0, 0, bg_alpha) if draw.im.mode == "RGBA" else (20, 20, 20)
    draw.rectangle([x - pad, y - pad, x + tw + pad, y + th + pad], fill=bg_color)
    draw.text((x, y), text, fill=color, font=font)
