from setuptools import setup, find_packages
from pipenv import find_install_requires

setup(
    name='air_quality_monitor',
    version='1.0.0',
    author='Nikita Batov',
    author_email='nikitabatov@gmail.com',
    description='Air quality monitor',
    packages=find_packages(),
    install_requires=find_install_requires()
)