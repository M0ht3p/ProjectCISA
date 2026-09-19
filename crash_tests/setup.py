from setuptools import setup
from Cython.Build import cythonize

setup(
    name="exif_processor",
    ext_modules=cythonize("exif_processor.pyx", compiler_directives={'language_level': "3"}),
)
