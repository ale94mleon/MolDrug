

# moldrug

**moldrug** is a Python package for drug-oriented optimization in chemical space. It leverages genetic algorithms, multi-criteria optimization, and Derringer-Suich desirability functions to navigate and optimize molecular structures for drug design applications. The toolkit integrates structure-based docking (AutoDock Vina), cheminformatics (RDKit, Meeko), and customizable fitness scoring to guide evolutionary search strategies.

## Installation

`moldrug` requires Python 3.8 to 3.11. Key dependencies include `rdkit`, `meeko`, `crem`, `numpy`, `pandas`, and `autodock-vina`.

### From PyPI
```bash
pip install moldrug
```

### From Source
```bash
git clone https://github.com/ale94mleon/moldrug.git
cd moldrug
pip install .
```

### Using Conda
```bash
conda create -n moldrug_env python=3.9
conda activate moldrug_env
conda install -c conda-forge rdkit meeko vina
pip install moldrug
```

## Usage

`moldrug` is primarily driven via command-line interface using YAML configuration files. It supports multi-step evolutionary workflows, custom fitness functions, and constraint-based docking.

### Command Line Interface
Run an optimization workflow by pointing to a configuration file:
```bash
moldrug config.yml
```

Specify a custom fitness scoring script (e.g., integrating MolSkill or predictive models):
```bash
moldrug config.yml --fitness /path/to/custom_fitness.py
```

For constraint-based conformation generation:
```bash
constrainconf_moldrug [options]
```

### Configuration Example
Workflows are defined in YAML format. A typical configuration chains sequential optimization steps, genetic algorithm parameters, docking settings, and desirability functions:
```yaml
01_grow:
  type: GA
  njobs: 32
  seed_mol: "CCCO"
  costfunc: Cost
  costfunc_kwargs:
    vina_executable: vina
    receptor_pdbqt_path: /path/to/receptor.pdbqt
    boxcenter: [23.56, 8.74, 15.40]
    boxsize: [22.5, 19.2, 27.4]
    exhaustiveness: 9
    desirability:
      vina_score:
        SmallerTheBest:
          Target: -10
          UpperLimit: -2
          r: 1
        w: 1
  maxiter: 20
  popsize: 100
  deffnm: 01_grow

02_local:
  mutate_crem_kwargs:
    radius: 3
    min_size: 0
    max_size: 1
    ncores: 128
  maxiter: 15
  deffnm: 02_local
```

### Interactive Dashboard
`moldrug` includes a Streamlit dashboard for visualizing optimization results, analyzing molecular grids, and exploring ligand-protein interactions using ProLIF:
```bash
streamlit run streamlit/moldrug-dashboard.py
```
Upload your `.pbz2` result files and protein PDB structures to interactively explore generations, filter by properties, and check molecular novelty against PubChem.

## Documentation & Community
- 📖 [Full Documentation](https://moldrug.readthedocs.io/en/latest/)
- 💬 [Discussions](https://github.com/ale94mleon/moldrug/discussions)
- 🐛 [Issue Tracker](https://github.com/ale94mleon/moldrug/issues)
- 📜 [Changelog](https://github.com/ale94mleon/moldrug/blob/main/docs/source/CHANGELOG.md)

## Acknowledgments
This project originated during Ph.D. research at the [Computational Biophysics Group](https://biophys.uni-saarland.de/) at Saarland University, in collaboration with Boehringer Ingelheim. It received funding from the European Union's Marie Skłodowska-Curie Actions (PROTON ITN, Project ID: 860592).

## License
Distributed under the Apache Software License. See `LICENSE` for details.
