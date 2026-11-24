#!/bin/bash
set -Eeuo pipefail

remote=${1:-"yimjk/ale-bench"}

     
                        
docker build ./dockerfiles -t ${remote}:cpp17-201907 -f ./dockerfiles/Dockerfile_cpp17_201907_base

                        
docker build ./dockerfiles -t ${remote}:cpp17-202301 -f ./dockerfiles/Dockerfile_cpp17_202301_base
docker build ./dockerfiles -t ${remote}:cpp20-202301 -f ./dockerfiles/Dockerfile_cpp20_202301_base
docker build ./dockerfiles -t ${remote}:cpp23-202301 -f ./dockerfiles/Dockerfile_cpp23_202301_base

        
                        
docker build ./dockerfiles -t ${remote}:python-201907 -f ./dockerfiles/Dockerfile_python_201907_base

                        
docker build ./dockerfiles -t ${remote}:python-202301 -f ./dockerfiles/Dockerfile_python_202301_base

      
                        
docker build ./dockerfiles -t ${remote}:rust-201907 -f ./dockerfiles/Dockerfile_rust_201907_base

                        
docker build ./dockerfiles -t ${remote}:rust-202301 -f ./dockerfiles/Dockerfile_rust_202301_base
