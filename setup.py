from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = [
    "pandas",
    "flask",
    "dataset",
    "rsonlite==0.1.0",
    "Flask-WTF==0.14.2",
    "Flask-SQLAlchemy==2.5.1",
    "WTForms==2.2.1",
    "WTForms-Alchemy==0.18",
    "WTForms-Components==0.10.4",
    "Flask-Migrate==2.5.2",
    "python-dotenv==0.10.3"
]

setup(
    name='isdi',
    version='0.1.1',
    description='IPV Spyware Discovery (ISDi) Tool',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/stopipv/isdi',
    author='Clinic to End Tech Abuse',
    include_package_data=True,
    install_requires=requirements,
    python_requires='>=3.5',
    packages=['isdi', 'isdi.templates', 'isdi.static_data'],
    package_data={'isdir': ['isdir/static_data/*', 'isdir/templates/*']},
    entry_points= {
        'console_scripts': [ 'isdi=isdi.cli:main' ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ]
)
