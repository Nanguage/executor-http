from setuptools import setup, find_namespace_packages
import re


classifiers = [
    "Development Status :: 3 - Alpha",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "License :: OSI Approved :: MIT License",
    "Intended Audience :: Science/Research",
    "Intended Audience :: Developers",
]


keywords = [
    'Job Management', "Web"
]


URL = "https://github.com/Nanguage/executor-http"


def get_version():
    with open("executor/http/__init__.py") as f:
        for line in f.readlines():
            m = re.match("__version__ = '([^']+)'", line)
            if m:
                return m.group(1)
        raise IOError("Version information can not found.")


def get_long_description():
    return f"See {URL}"


def get_install_requires():
    requirements = ["executor-engine", "fastapi", "uvicorn", "oneface>=0.1.9", "python-multipart"]
    return requirements


requires_test = ['pytest', 'pytest-cov', 'flake8', 'pytest-order', 'mypy', 'httpx']


setup(
    name='executor-http',
    author='Weize Xu',
    author_email='vet.xwz@gmail.com',
    version=get_version(),
    license='MIT',
    description='Plantform for manage job executions.',
    long_description=get_long_description(),
    keywords=keywords,
    url=URL,
    packages=find_namespace_packages(include=["executor/*"]),
    include_package_data=True,
    zip_safe=False,
    classifiers=classifiers,
    install_requires=get_install_requires(),
    extras_require={
        'test': requires_test,
    },
    python_requires='>=3.7, <4',
)
