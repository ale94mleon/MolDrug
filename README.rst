MolDrug
=======

|logo|

.. list-table::
    :widths: 12 35

    * - **Documentation**
      - |docs|
    * - **Tutorials**
      - |binder|
    * - **CI/CD**
      - |tests| |codecov| |lgtm|
    * - **Build**
      - |pypi-version| |conda|
    * - **Source Code**
      - |github|
    * - **Python Versions**
      - |pyversions|
    * - **Dependencies**
      - |rdkit| |crem| |meeko|
    * - **License**
      - |license|
    * - **Downloads**
      - |downloads|


Description
-----------

**MolDrug** is a python package for lead generation and optimization of small molecules.
It use a Genetic Algorithm (GA) as searching engine in the chemical space and
`CReM <https://github.com/DrrDom/crem>`__ library as chemical structure generator.

You can try it out prior to any installation on `Binder <https://mybinder.org/v2/gh/ale94mleon/moldrug/HEAD?labpath=%2Fdocs%2Fnotebooks%2F>`__.

Documentation
-------------

The installation instructions, documentation and tutorials can be found online on `ReadTheDocs <https://moldrug.readthedocs.io/en/latest/>`_.

Issues
------

If you have found a bug, please open an issue on the `GitHub Issues <https://github.com/ale94mleon/moldrug/issues>`_.

Discussion
----------

If you have questions on how to use MolDrug, or if you want to give feedback or share ideas and new features, please head to the `GitHub Discussions <https://github.com/ale94mleon/moldrug/discussions>`_.

Citing **MolDrug**
------------------

Please refer to the `citation page <https://moldrug.readthedocs.io/en/latest/source/citations.html>`__ on the documentation.

..  |logo|  image:: https://github.com/ale94mleon/moldrug/blob/main/row_data/logo.png?raw=true
    :target: https://github.com/ale94mleon/moldrug/
    :alt: logo
..  |docs|  image:: https://readthedocs.org/projects/moldrug/badge/?version=latest
    :target: https://moldrug.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation
..  |binder| image:: https://mybinder.org/badge_logo.svg
    :target: https://mybinder.org/v2/gh/ale94mleon/moldrug/HEAD?labpath=%2Fdocs%2Fnotebooks%2F
    :alt: binder
..  |tests| image:: https://github.com/ale94mleon/MolDrug/actions/workflows/python-package.yml/badge.svg
    :target: https://github.com/ale94mleon/MolDrug/actions/workflows/python-package.yml
    :alt: tests
..  |codecov| image:: https://codecov.io/gh/ale94mleon/MolDrug/branch/main/graph/badge.svg?token=RTLKQ070YX
    :target: https://codecov.io/gh/ale94mleon/MolDrug
    :alt: codecov
..  |lgtm| image::  https://img.shields.io/lgtm/grade/python/g/ale94mleon/MolDrug.svg?logo=lgtm&logoWidth=18
    :target: https://lgtm.com/projects/g/ale94mleon/MolDrug/context:python
    :alt: lgtm
..  |pypi-version|  image:: https://img.shields.io/pypi/v/moldrug.svg
    :target: https://pypi.python.org/pypi/moldrug/
    :alt: pypi-version
..  |conda|  image:: https://anaconda.org/ale94mleon/moldrug/badges/version.svg
    :target: https://anaconda.org/ale94mleon/moldrug
    :alt: conda
..  |github|    image:: https://badgen.net/badge/icon/github?icon=github&label
    :target: https://github.com/ale94mleon/moldrug
    :alt: GitHub-Repo
..  |pyversions|    image:: https://img.shields.io/pypi/pyversions/moldrug.svg
    :target: https://pypi.python.org/pypi/moldrug/
..  |rdkit| image:: https://img.shields.io/static/v1?label=Powered%20by&message=RDKit&color=3838ff&style=flat&logo=data:image/x-icon;base64,AAABAAEAEBAQAAAAAABoAwAAFgAAACgAAAAQAAAAIAAAAAEAGAAAAAAAAAMAABILAAASCwAAAAAAAAAAAADc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nz/FBT/FBT/FBT/FBT/FBT/FBTc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nz/FBT/PBT/PBT/PBT/PBT/PBT/PBT/FBTc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nz/FBT/PBT/ZGT/ZGT/ZGT/ZGT/ZGT/ZGT/PBT/FBTc3Nzc3Nzc3Nzc3Nzc3Nz/FBT/PBT/ZGT/ZGT/ZGT/ZGT/ZGT/ZGT/ZGT/ZGT/PBT/FBTc3Nzc3Nzc3Nz/FBT/PBT/ZGT/ZGT/ZGT/jIz/jIz/jIz/jIz/ZGT/ZGT/ZGT/PBT/FBTc3Nzc3Nz/FBT/PBT/ZGT/ZGT/jIz/jIz/jIz/jIz/jIz/jIz/ZGT/ZGT/PBT/FBTc3Nzc3Nz/FBT/PBT/ZGT/ZGT/jIz/jIz/tLT/tLT/jIz/jIz/ZGT/ZGT/PBT/FBTc3Nzc3Nz/FBT/PBT/ZGT/ZGT/jIz/jIz/tLT/tLT/jIz/jIz/ZGT/ZGT/PBT/FBTc3Nzc3Nz/FBT/PBT/ZGT/ZGT/jIz/jIz/jIz/jIz/jIz/jIz/ZGT/ZGT/PBT/FBTc3Nzc3Nz/FBT/PBT/ZGT/ZGT/ZGT/jIz/jIz/jIz/jIz/ZGT/ZGT/ZGT/PBT/FBTc3Nzc3Nzc3Nz/FBT/PBT/ZGT/ZGT/ZGT/ZGT/ZGT/ZGT/ZGT/ZGT/PBT/FBTc3Nzc3Nzc3Nzc3Nzc3Nz/FBT/PBT/ZGT/ZGT/ZGT/ZGT/ZGT/ZGT/PBT/FBTc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nz/FBT/PBT/PBT/PBT/PBT/PBT/PBT/FBTc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nz/FBT/FBT/FBT/FBT/FBT/FBTc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nz/////+B////AP///gB///wAP//4AB//+AAf//gAH//4AB//+AAf//gAH//8AD///gB///8A////gf////////
    :target: https://www.rdkit.org/docs/index.html
    :alt: rdkit
..  |meeko| image:: https://img.shields.io/static/v1?label=Powered%20by&message=Meeko&color=6858ff&style=flat
    :target: https://github.com/forlilab/Meeko
    :alt: Meeko
..  |crem| image:: https://img.shields.io/static/v1?label=Powered%20by&message=CReM&color=9438ff&style=flat
    :target: https://crem.readthedocs.io/en/latest/
    :alt: crem
..  |license| image:: https://badgen.net/pypi/license/moldrug/
    :target: https://pypi.python.org/pypi/moldrug/
    :alt: license
..  |downloads| image:: https://static.pepy.tech/personalized-badge/moldrug?period=month&units=international_system&left_color=grey&right_color=brightgreen&left_text=Downloads
    :target: https://pepy.tech/project/moldrug
    :alt: download
