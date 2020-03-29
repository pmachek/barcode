import setuptools


with open("README.md", "r") as readme_file:
    readme = readme_file.read()

setuptools.setup(
    name="stripes-and-squares",
    version="0.0.1-rc1",
    author="Petr Machek",
    description="Barcode generator with no dependencies",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/pmachek/barcode",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.3"
)
