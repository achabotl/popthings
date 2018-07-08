import io
import popthings
from setuptools import setup


with io.open("README.md", "r", encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='popthings',
    version=popthings.__version__,
    author='Alexandre Chabot-Leclerc',
    author_email='github@alexchabot.net',
    description=('iOS and command line tool to import a TaskPaper template'
                 ' with placeholders into Things by Cultured Code'),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/achabotl/popthings",
    scripts=['popthings.py'],
    entry_points={
        'console_scripts': [
            'popthings = popthings:cli',
        ],
    },
    classifiers=(
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: iOS",
        "Operating System :: MacOS :: MacOS X",
        "Natural Language :: English",
    ),
)
