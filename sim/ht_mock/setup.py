from setuptools import setup

setup(
    name="ht_mock",
    version="0.0.1",
    packages=["ht_mock"],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/ht_mock"]),
        ("share/ht_mock", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    entry_points={"console_scripts": ["controller = ht_mock.controller:main"]},
)
