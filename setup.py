from setuptools import setup, find_packages

setup(
    name="bank-analyzer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
        "matplotlib>=3.8.0",
    ],
    python_requires=">=3.8",
) 