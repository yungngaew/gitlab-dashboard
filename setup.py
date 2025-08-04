#!/usr/bin/env python3
"""Setup script for GitLab Tools."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / 'README.md'
long_description = ''
if readme_file.exists():
    long_description = readme_file.read_text()

# Read requirements
requirements_file = Path(__file__).parent / 'requirements.txt'
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip() 
        for line in requirements_file.read_text().splitlines()
        if line.strip() and not line.startswith('#')
    ]

setup(
    name='gitlab-tools',
    version='0.2.0',
    author='Your Name',
    author_email='your.email@example.com',
    description='Enhanced GitLab management tools for bulk operations',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tkhongsap/tcctech-gitlab',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    package_data={
        'gitlab_tools': ['templates/**/*.yaml']
    },
    python_requires='>=3.8',
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'gitlab-rename-branches=scripts.rename_branches:main',
            'gitlab-create-issues=scripts.create_issues:main',
            'gitlab-analyze=scripts.analyze_projects:main',
            'glt=glt:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Version Control :: Git',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='gitlab api automation devops git',
    project_urls={
        'Bug Reports': 'https://github.com/tkhongsap/tcctech-gitlab/issues',
        'Source': 'https://github.com/tkhongsap/tcctech-gitlab',
    },
)