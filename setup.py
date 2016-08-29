from setuptools import setup, find_packages

setup(
    name='pymux',
    version='0.1.0.dev1',
    install_requires=[
        'Click',
    ],
    entry_points="""
        [console_scripts]
        pymux=pymux.pymux:pymux
    """,
    packages=find_packages(),
)
