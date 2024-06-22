import torch
from setuptools import setup, find_packages
from torch.utils.cpp_extension import CUDAExtension, BuildExtension

cmdclass = {}
ext_modules = []
cmdclass['build_ext'] = BuildExtension

ext_modules.append(
    CUDAExtension(name='fused_lamb_cuda',
                  sources=['csrc/fused_lamb_cuda.cpp',
                           'csrc/fused_lamb_cuda_kernel.cu'],
                  extra_compile_args={
                      'cxx': [
                          '-O3',
                      ],
                      'nvcc': ['-O3',
                               '--use_fast_math']
                  }))

setup(name='deepcode',
      version='0.1',
      description='DeepCode library',
      author='DeepCode Team',
      author_email='info@khulnasoft.com',
      url='http://github.com/deepcode-ai/deepcode',
      packages=find_packages(exclude=[
          "docker",
          "third_party",
          "csrc"
      ]),
      scripts=[
          'bin/deepcode',
          'bin/dc'
      ],
      classifiers=['Programming Language :: Python :: 3.6'],
      ext_modules=ext_modules,
      cmdclass=cmdclass)
