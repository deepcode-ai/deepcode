# Use a base image with CUDA 10.2
FROM nvidia/cuda:12.5.0-devel-ubuntu22.04

# Set environment variables
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# Set the working directory
WORKDIR /app

# Copy the rest of the code
COPY . .

# Install Apex
RUN cd third_party/apex && \
    pip3 install -v --no-cache-dir --global-option="--cpp_ext" --global-option="--cuda_ext" .

# Expose the necessary port (example: 8000)
EXPOSE 8000

# Command to run the application
CMD ["python3", "setup.py"]
