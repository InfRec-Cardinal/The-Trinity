DESC_4_SPLITS = """1 is the upperleft part, 2 is the lowerleft part, 3 is the upperright part, 4 is the lowerright part"""

DESC_ANY_SPLITS = """ images are split into {grids} grids, and the index of image are arranged in left-to-right and then up-to-down order. For exampel, 1 is the first part from the left in the first row, 2 is the second part from the left in the first row, etc; and {num_splits} is the last part from the left in the last row"""

QA_TEMPLATES = """Carefully analysis this image {image}, and answer the question from the given options. Question: {question} Options: {option}. Answer:"""

QA_TEMPLATES_CHAT = """Carefully analysis {image}, and answer the question from the given options. Question: {question} Options: {option}. Answer:"""

ACTIVE_PERCEPTION_TEMPLATES = """This is the original image with visual clues {image1}. These are the visual clues in the original image for answering the given question: {image_clues}. Please answer the question according to the original image and visual clues. These visual clues directly indicate the answer and will help you with the reasoning. Question: {question} Options: {option}. Answer:"""

ACTIVE_PERCEPTION_TEMPLATES_BROTE = """image 0 is <image0>{replace_token}, it is the original image. These are the visual clues in image 0 for answering the given question: {image_clues}. Please answer the question according to the original image 0 and visual clues. These visual clues directly indicate the answer and will help you with the reasoning. Question: {question} Options: {option}. Answer:"""

SHIFT_DECISION_TEMPLATES = """Your will be presented with a part or parts of an image and a question concerning the full image. {image} is the {image_view} part of the full image. Given these views, please determine if you need more visual information to answer the question: "{question}"\n===\n
Do not directly answer the question. You should make desicion, if you need more visial information to answer the question. Yes or No? Your Response:"""

SHIFT_DECISION_TEMPLATES_CHAT = """Your will be presented with a part or parts of an image and a question concerning the full image. {images}. Given these views, please determine if you need more visual information to answer the question: "{question}"\n===\n
Do not directly answer the question. You should make desicion, if you need more visial information to answer the question. Yes or No? Your Response:"""

SHIFT_DECISION_TEMPLATES_BROTE1 = """Your will be presented with a part or parts of an image and a question concerning the full image.{images} Given these views, please determine if you need more visual information to answer the question: "{question}"\n===\n
Do not directly answer the question. You should make desicion, if you need more visial information to answer the question. Yes or No? Your Response:"""

SHIFT_DECISION_TEMPLATES_BROTE1_ANY = """There are {num_splits} parts of the image, and they are arranged in {order}. Your will be presented with a part or parts of an image and a question concerning the full image.{images} Given these views, please determine if you need more visual information to answer the question: "{question}"\n===\n
Do not directly answer the question. You should make desicion, if you need more visial information to answer the question. Yes or No? Your Response:"""

SHIFT_DECISION_TEMPLATES_BROTE2 = """Your will be presented with a partial image and a question concerning the full image. image 0 is <image0>{replace_token}, is the {image_view} part of the full image. Given image 0, please determine if you need more visual information to answer the question: "{question}"\n===\n
Do not directly answer the question. If you can answer the question without more visual information, response with NO. Otherwise, response with other image parts you need to see given this {image_view} part, you can choose from these views: {view_options}. Your Response:"""

MULTI_VIEWS = """The {view} part is {view_image}
"""

SHIFT_MULTI_QA_TEMPLATES = """These are parts of an image. {all_required_views}. Carefully analysis these images and pay attention to their original position. Answer the question from the given options. Question: {question}. Options: {option}. Answer:"""

ZOOM_MANUAL_DECISION_TEMPLATES = """This is the full image {image}, which is split in to {num_splits} equal parts, numbered from 1 to {num_splits}, where {description_of_splits}. 
Response with the number of part (at least one part, at most {num_splits} parts), that must be used to answer the question. The question is: {question}
Do not directly answer the given question. Response with the selected number of parts, split by ',' if there are multiple selections. 
Your Response:"""

ZOOM_MANUAL_DECISION_TEMPLATES_ANY = """This is the full image {image}, which is split in to {num_splits} equal parts, numbered from 1 to {num_splits}, where {description_of_splits}. 
Response with the number of part (at least one part, at most {num_splits} parts), that must be used to answer the question. Multiple parts are recommanded. The question is: {question}
Do not directly answer the given question. Response with the selected number of parts, split by ',' if there are multiple selections. 
Your Response:"""

ZOOM_MANUAL_DECISION_TEMPLATES_CHAT = """{image} is the full image, which is split in to {num_splits} equal parts, numbered from 1 to {num_splits}, where {description_of_splits}. 
Response with the number of part (at least one part, at most {num_splits} parts), that must be used to answer the question. The question is: {question}
Do not directly answer the given question. Response with the selected number of parts, split by ',' if there are multiple selections. 
Your Response:"""

ZOOM_AUTO_DECISION_TEMPLATES = """This is the full image {image}. Your should split it in to {num_splits} equal parts and numbered them from 1 to {num_splits} according to this order: first left to right, and then up to down. \n
Response with the number of part (at least one part, at most {num_splits-1} parts), that must be used to answer the question. The question is:{question} 
Your Response:"""

ZOOM_QA_TEMPLATES = """This is the full image {image}. These are your selected part of image that must be used to answer the question {zoomed_images}. Please answer question according to the given images from the the given options. Question: {question} Options: {option}. Answer:"""

ZOOM_QA_TEMPLATES_BROTE = """image 0 is <image0>{replace_token}. image 0 is the full image. {zoomed_images}These are your selected part of image that must be used to answer the question. Please answer question according to the given images from the the given options. Question: {question} Options: {option}. Answer:"""

ZOOM_QA_TEMPLATES_CHAT = """{image} is the full image. These are your selected part of image that must be used to answer the question {zoomed_images}. Please answer question according to the given images from the the given options. Question: {question} Options: {option}. Answer:"""

MIX_INIT_DECISION_TEMPLATE = """You will be presented with a full image {image} and a corresponding question to answer. The image is split in to {num_splits} equal parts, numbered from 1 to {num_splits}, where {description_of_splits}.
You can check for detailed visual information via zooming operation that zoom in to your selected part or parts iwth from the above numbers. Response with the the numbers of parts you wish to zoom in, or response with "none" if you don't need to can check for details. 
The quesiton is: {question} 
You should not directly answer the question. You should generate the a json dict containing 2 fields:
- "part": type str, the selected numbers of index of parts, split by ',', or 'none' if no zooming required;
- "reason": type str, why you choose these parts
Your response:"""

MIX_INTER_DECISION_TEMPLATE = """Your are given a full image {image} and a corresponding question to answer. The image is split in to {num_splits} equal parts, numbered from 1 to {num_splits}, where {description_of_splits}. Your have chosen to zoom in to these parts, {zoomed_images}, for detailed checking if they can help to ansewr the quesiton. 
Question: {question} Options: {option}.
Now, there are two operations: "keep" and "shift". 
- "keep": choose none or more parts from the zoomed ones to answer the question; 
- "shift": you can shift to the rest parts to answer questions or answer question with none sub-parts. 
You should not directly answer the question. You should return you answer in a json dict containing two fields:
- "keep": type str, the index numbers of required parts split by ',', or "none" if the zoomed parts are useless;  
- "shift": type str, the index numbers of the rest parts, that are useful to the question split by ',', or "none" if you don't wish to shift.
Your response:"""

MIX_DECISION_TEMPLATE = """You will be presented with an image and a corresponding question to answer. The image is split in to {num_splits} equal parts, numbered from 1 to {num_splits}, where {description_of_splits}.
You can check for detailed visual information via two operations: "zooming" and "shifting". The "zooming" operation refers to zoom into one or more parts of the image to acquire for fine-grained visual details; and the "shifting" operation refers to change to another parts if the zoomed part or parts do not provide sufficient information to answer the question. 
Question: {question} Options: {option}. 
Your selected parts of the given image are {zoomed_images}.
You should not directly answer the question. You should generate the selected operation and the index of image part to be zoomed or shifted to, the operation and the indexes should be separated by ", ", such as "zooming, 1, 3". If you believe the current visual informations are sufficient to answer the question, then generate "No, -1".
Your Response:"""
