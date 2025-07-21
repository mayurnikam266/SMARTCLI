from setuptools import setup, find_packages

setup(
    name="smartcli",
    version="0.1.0",
    description="🤖 SmartCLI - AI Terminal Assistant using LLMs",
    author="Mayur Nikam",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pyyaml>=5.1",                  
        "requests>=2.20",              
        "openai>=0.28",                 
        "google-generativeai>=0.3.2",   
        "rich>=10.0",                   
        "importlib-metadata>=1.0; python_version<'3.8'", 
        "colorama>=0.4.0",              
        "prompt_toolkit>=3.0",        
        "questionary>=1.10",           
    ],
    entry_points={
        "console_scripts": [
            "scli = smartcli.main:main", 
        ]
    },
    python_requires=">=3.6",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
