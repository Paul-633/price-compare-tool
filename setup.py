from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="price-compare-tool",
    version="1.2.0",
    author="Paul-633",
    description="电商商品价格自动化采集与对比工具 - 支持京东/淘宝/拼多多",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Paul-633/price-compare-tool",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.25.0",
        "beautifulsoup4>=4.9.0",
        "lxml>=4.6.0",
        "pymysql>=1.0.0",
        "schedule>=1.1.0",
    ],
    entry_points={
        "console_scripts": [
            "price-compare=price_compare:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Office/Business :: Financial",
    ],
)
