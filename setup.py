from setuptools import find_packages, setup

setup(
    name="Your FastAPI App",
    version="0.1",
    packages=find_packages(),
    install_requires=["sphinx_autodoc_typehints", "sphinx.ext.autodoc"],
)
