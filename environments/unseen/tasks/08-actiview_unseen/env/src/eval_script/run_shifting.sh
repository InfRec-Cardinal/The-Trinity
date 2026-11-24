FILENAME=$1
CUDA_ID=$2
MODELPATH=$3

CUDA_VISIBLE_DEVICES=${CUDA_ID} python -u eval_active_bench.py \
            --model_path ${MODELPATH} \
            --processor_path ./ \
            --eval_data ${FILENAME} \
            --eval_image ${FILENAME}/images \
            --eval_image_split ${FILENAME}/images_split \
            --eval_type shifting \
	    --model_name Brote \
            --model_scale xl

CUDA_VISIBLE_DEVICES=${CUDA_ID} python -u eval_active_bench.py \
            --model_path ${MODELPATH} \
            --processor_path ./ \
            --eval_data ${FILENAME} \
            --eval_image ${FILENAME}/images\
            --eval_image_split ${FILENAME}/images_split  \
            --eval_type shifting \
	    --model_name Brote \
            --model_scale xxl


CUDA_VISIBLE_DEVICES=${CUDA_ID} python -u eval_active_bench.py \
            --model_path ${MODELPATH} \
            --processor_path ./ \
            --eval_data ${FILENAME} \
            --eval_image ${FILENAME}/images \
            --eval_image_split ${FILENAME}/images_split \
            --eval_type shifting \
	    --save_results \
     	    --pre_define_view easy \
	    --model_name Brote \
            --model_scale xl

CUDA_VISIBLE_DEVICES=${CUDA_ID} python -u eval_active_bench.py \
            --model_path ${MODELPATH} \
            --processor_path ./ \
            --eval_data ${FILENAME} \
            --eval_image ${FILENAME}/images \
            --eval_image_split ${FILENAME}/images_split \
            --eval_type shifting \
	    --save_results \
	    --pre_define_view medium \
	    --model_name Brote \
            --model_scale xl

CUDA_VISIBLE_DEVICES=${CUDA_ID} python -u eval_active_bench.py \
            --model_path ${MODELPATH} \
            --processor_path ./ \
            --eval_data ${FILENAME} \
            --eval_image ${FILENAME}/images \
            --eval_image_split ${FILENAME}/images_split \
            --eval_type shifting \
	    --save_results \
	    --pre_define_view hard \
	    --model_name Brote \
            --model_scale xl

