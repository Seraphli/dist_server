import re
from setuptools import setup, find_packages


# Read property from project's package init file
def get_property(prop, project):
    result = re.search(r'{}\s*=\s*[\'"]([^\'"]*)[\'"]'.format(prop),
                       open(project + '/__init__.py').read())
    return result.group(1)


setup(
    name='dist_server',
    version=get_property('__version__', 'dist_server'),
    description='Python Distribute Package.',
    author='SErAphLi',
    url='https://github.com/Seraphli/dist_server.git',
    license='MIT License',
    packages=find_packages(),
    install_requires=[
        'thrift',
    ]
)
