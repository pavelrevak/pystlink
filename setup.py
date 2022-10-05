import setuptools
import os
import codecs


_ABOUT = {
    'APP_NAME': 'pystlink',
    'VERSION': '1.0.0',
    'DESCRIPTION': 'Python tool for manipulating with STM32 MCUs using ST-Link in-system programmer and debugger.',
    'URL': 'https://github.com/pavelrevak/pystlink',
    'AUTHOR': 'Pavel Revak',
    'AUTHOR_EMAIL': 'pavel.revak@gmail.com'
}

def get_long_description():
    current_dir = os.path.abspath(os.path.dirname(__file__))
    readme_file = os.path.join(current_dir, 'README.md')
    with codecs.open(readme_file, encoding='utf-8') as readme_file:
        long_description = readme_file.read()
    return long_description


setuptools.setup(
    name=_ABOUT['APP_NAME'],
    version=_ABOUT['VERSION'],
    description=_ABOUT['DESCRIPTION'],
    long_description=get_long_description(),
    url=_ABOUT['URL'],
    author=_ABOUT['AUTHOR'],
    author_email=_ABOUT['AUTHOR_EMAIL'],
    license='MIT',
    keywords='SWD debugger STM32 STLINK CORTEX-M ARM',

    classifiers=[
        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Embedded Systems',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],

    packages=[
        'stlink'
        '/lib'
    ],

    install_requires=[
        'pyusb (>=1.0.2)'
    ],

    entry_points={
        'console_scripts': [
            'pystlink = stlink.cmd.run_cli'
        ],
    },
)
