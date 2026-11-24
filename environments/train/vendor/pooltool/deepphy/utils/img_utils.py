import glob
import base64
import imageio
import os
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from typing import Optional

try:
    import phyre
except ImportError:
       pass

try:
    import pooltool as pt
except:
    pass

                   
DEFAULT_DPI = 96                                                                          
INCH_PER_CM = 2.54                               



def encode_image_to_base64(image_path):
    pass                                           
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None

def find_dynamic_frames(directory, k = 5):

    image_files = sorted(glob.glob(os.path.join(directory, 'frame_*.png')))

    if len(image_files) >= k:
        image_files = image_files[:k]

    return image_files

def add_grid_with_matplotlib(image_path, grid_size, line_color='red', line_width=1.5, fontsize=10):
    pass                                                                  
    if not os.path.exists(image_path):
        print(f"  Error: Cannot add grid, file not found -> {image_path}")
        return None
    try:
        img = mpimg.imread(image_path)
        height, width, _ = img.shape
        dpi = 100
        fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
        ax.imshow(img)
        rows, cols = grid_size
        for i in range(1, cols):
            ax.axvline(x=(width / cols) * i, color=line_color, linewidth=line_width)
        for i in range(1, rows):
            ax.axhline(y=(height / rows) * i, color=line_color, linewidth=line_width)

        cell_number = 1
        cell_height = height / rows
        cell_width = width / cols
        for r in range(rows):
            for c in range(cols):
                ax.text(cell_width * (c + 0.5), cell_height * (r + 0.5), str(cell_number),
                        color=line_color, fontsize=fontsize, fontweight='bold', ha='center', va='center')
                cell_number += 1

        ax.axis('off')
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

        base, ext = os.path.splitext(image_path)
        output_path = f"{base}_{rows}x{cols}_grid{ext}"
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0, dpi=dpi)
        plt.close(fig)
        print(f"  Added a {rows}x{cols} grid to the image, saved to: {output_path}")
        return output_path
    except Exception as e:
        print(f"  An error occurred while processing the image: {e}")
        return None

def get_normalized_center_coords(cell_number, grid_size):
    pass                                                                                        
                                                                          
       
    rows, cols = grid_size
    if not (1 <= cell_number <= rows * cols):
        return None
    index = cell_number - 1
    row_from_top = index // cols                                       
    col_from_left = index % cols                                            

                                                                                     
    center_x = (col_from_left + 0.5) / cols

                                                                    
                                                                                
                                                                                   
    center_y = ((rows - 1 - row_from_top) + 0.5) / rows

    return (center_x, center_y)

def convert_radius_size_to_normalized(radius_size, max_level):
    pass                                                                                        
                         
                            
       
    if not (1 <= radius_size <= max_level):
        return None

                                                
    min_output_r = 0.0625
    max_output_r = 1.0

                                            
    if max_level == 1:
                                                                                                
        return max_output_r

                                              
                                                                                                 
                               
                                     
                                       
                                       
                                     
    ratio = (radius_size - 1) / (max_level - 1)

                                                                          
    output_range_span = max_output_r - min_output_r
    normalized_r = min_output_r + ratio * output_range_span

    return normalized_r

def save_simulation_images_and_get_keyframes(simulation, output_dir, file_prefix=""):
    pass                                                          
    if simulation.images is None:
        return {"gif_path": None, "keyframes": []}

    temp_frame_paths = []
                                                       
    for i, image_data in enumerate(simulation.images[:5]):
        image_path = os.path.join(output_dir, f"{file_prefix}_frame_{i:03d}.png")
        plt.imsave(image_path, phyre.observations_to_float_rgb(image_data))
        temp_frame_paths.append(image_path)

    gif_path = os.path.join(output_dir, f"{file_prefix}simulation.gif")
    with imageio.get_writer(gif_path, mode='I', duration=0.1) as writer:
        for image_path in temp_frame_paths:
            writer.append_data(imageio.imread(image_path))

    keyframes = []
    for i, frame_path in enumerate(temp_frame_paths):
        keyframes.append({'path': frame_path, 'label': f"Keyframe {i}"})

    return {"gif_path": gif_path, "keyframes": keyframes}

def delete_unselected_frames(base_output_dir: str, selected_frames: list):
    pass                                                                                                        

         
                                                                                                                
                                                                                   
                                                                                                             
       
    frames_source_dir = os.path.join(base_output_dir, "0", "images")
    if not os.path.isdir(frames_source_dir):
        print(f"  Warning: Frame directory {frames_source_dir} not found, skipping deletion of unselected frames.")
        return

    all_frame_files = [os.path.join(frames_source_dir, f) for f in os.listdir(frames_source_dir) if f.endswith('.png')]
    selected_frames_set = set(selected_frames)

    deleted_count = 0
    for frame_path in all_frame_files:
        if frame_path not in selected_frames_set:
            try:
                os.remove(frame_path)
                deleted_count += 1
                                                                                             
            except OSError as e:
                print(f"  Error: Failed to delete frame {frame_path}: {e}")

    print(f"  Deleted {deleted_count} unselected frame images from {frames_source_dir}.")

def plot_static_pool_table(system, figsize=(10, 8), dpi=200, filename=None, show_text=True):
    pass                                                                   
                                                                          

         
                                                                                    
                                                                     
                                                                       
                                                                                                          
                                                                           
       
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

                                                 
    table_width = system.table.w
    table_length = system.table.l

                                                                             
    ball_radius = pt.BallParams().R                 
    if system.balls:
        ball_radius = next(iter(system.balls.values())).params.R


                                                    
    buffer_margin = max(ball_radius * 2.5, 0.1)                       

    playing_surface = plt.Rectangle(
        (0, 0), table_width, table_length,
        facecolor='#006400',             
        edgecolor='black',
        linewidth=2,
        zorder=0
    )
    ax.add_patch(playing_surface)

                                        
    if system.table.has_pockets:
        for pocket_id, pocket in system.table.pockets.items():
            p_center_x, p_center_y = pocket.center[:2]
            p_radius = pocket.radius

            pocket_circle = plt.Circle(
                (p_center_x, p_center_y), p_radius,
                color='darkgray',
                zorder=1
            )
            ax.add_patch(pocket_circle)

                       
                                                     
    ball_colors = {
        "cue": "white", "1": "yellow", "2": "blue", "3": "red",
        "4": "purple", "5": "orange", "6": "green", "7": "maroon",
        "8": "black", "9": "yellow", "10": "blue", "11": "red",
        "12": "purple", "13": "orange", "14": "green", "15": "maroon",
    }

                                              
                                                                    
    sorted_ball_ids = sorted(system.balls.keys(), key=lambda x: (x.isalpha(), int(x) if x.isdigit() else float('inf')))

    for ball_id in sorted_ball_ids:
        ball = system.balls[ball_id]
        x, y = ball.xyz[:2]
        radius = ball.params.R
        color = ball_colors.get(ball_id, "gray")

        ball_circle = plt.Circle(
            (x, y), radius,
            facecolor=color,
            zorder=2,
            edgecolor='black',
            linewidth=0.5
        )
        ax.add_patch(ball_circle)

        if show_text:
            fontsize = max(8, radius * 150)                          
            text_color = 'white' if str(ball_id) == '8' else 'black'
            ax.text(x, y, str(ball_id),
                    color=text_color,
                    fontsize=fontsize,
                    ha='center', va='center', fontweight='bold', zorder=3)

                                             
    ax.set_xlim(-buffer_margin, table_width + buffer_margin)
    ax.set_ylim(-buffer_margin, table_length + buffer_margin)
    ax.set_aspect('equal', adjustable='box')

                                      
    ax.set_title('')
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])

    if filename:
        plt.savefig(filename, dpi=dpi, bbox_inches='tight')
    plt.close(fig)                                     

def crop_image_by_cm(
    input_path: str,
    crop_top_cm: float = 0,
    crop_bottom_cm: float = 0,
    crop_left_cm: float = 0,
    crop_right_cm: float = 0,
    output_path: Optional[str] = None
) -> bool:
    pass                                                                                          

                                                                                        
                                                                         

         
                                                                     
                                                                                           
                                                                                                 
                                                                                             
                                                                                               
                                                                         
                                                                                    
                                                      

            
                                                  
       
                                    
    if not os.path.exists(input_path):
        print(f"Error: Input file does not exist at '{input_path}'")
        return False

    try:
                        
        with Image.open(input_path) as img:
                                                      
            width, height = img.size
            print(f"Original image dimensions: {width}x{height} pixels")

                                   
                                                                   
            if 'dpi' in img.info and isinstance(img.info['dpi'], (tuple, list)) and len(img.info['dpi']) == 2:
                dpi_x, dpi_y = img.info['dpi']
                print(f"Successfully read image DPI: X={dpi_x}, Y={dpi_y}")
            else:
                dpi_x, dpi_y = DEFAULT_DPI, DEFAULT_DPI
                print(f"Warning: Image has no DPI information, using default value of {DEFAULT_DPI} DPI.")

                                                   
            px_top = int((crop_top_cm / INCH_PER_CM) * dpi_y)
            px_bottom = int((crop_bottom_cm / INCH_PER_CM) * dpi_y)
            px_left = int((crop_left_cm / INCH_PER_CM) * dpi_x)
            px_right = int((crop_right_cm / INCH_PER_CM) * dpi_x)

            print(f"Calculated crop pixels: Top={px_top}, Bottom={px_bottom}, Left={px_left}, Right={px_right}")

                                   
            if (px_left + px_right) >= width:
                print(f"Error: Horizontal crop sum ({px_left + px_right}px) is greater than or equal to image width ({width}px).")
                return False
            if (px_top + px_bottom) >= height:
                print(f"Error: Vertical crop sum ({px_top + px_bottom}px) is greater than or equal to image height ({height}px).")
                return False

                                                                     
            left = px_left
            upper = px_top
            right = width - px_right
            lower = height - px_bottom

            crop_box = (left, upper, right, lower)
            print(f"Final crop box (left, upper, right, lower): {crop_box}")

                              
            cropped_img = img.crop(crop_box)

                                                      
            save_path = output_path if output_path else input_path

                                                                           
            if output_path:
                output_dir = os.path.dirname(output_path)
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)

            cropped_img.save(save_path)

            action = "overwritten" if save_path == input_path else "saved to"
            print(f"Success! Image has been cropped and {action}: '{save_path}'")
            return True

    except Exception as e:
        print(f"An error occurred while processing the image: {e}")
        return False
