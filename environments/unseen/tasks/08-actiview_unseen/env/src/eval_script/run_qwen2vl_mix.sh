cd toolkit

FILEPATH=$1
CUDA_ID=$2
MODELPATH=$3
PYTHON=YOUR_PYTHON

CUDA_VISIBLE_DEVICES=${CUDA_ID} ${PYTHON} -u eval_active_bench.py \
            --model_path ${MODELPATH} \
		   	--processor_path ./ \
            --eval_data  ${FILEPATH}\
            --eval_image ${FILEPATH}/images \
            --eval_image_split ${FILEPATH}/images_split \
            --eval_type mix \
			--save_results \
			--model_name qwen2vl 

