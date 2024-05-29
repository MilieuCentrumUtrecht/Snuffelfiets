# Snuffelfiets

## Omschrijving

Rapportage en analyse scripts voor het Milieucentrum Utrecht Snuffelfiets project.


## Installatie

> NB. If you do not have a working conda setup, please first follow [Setup the analysis environment](#setup-the-analysis-environment)

Clone the repository.
```
git clone https://github.com/MilieuCentrumUtrecht/Snuffelfiets.git
cd Snuffelfiets
```

Create a conda environment.
```
conda env create -f environment.yml
conda activate snuffelfiets
conda develop .
```

Start a notebook server.
```
python -m ipykernel install --user --name=snuffelfiets
jupyter notebook
```

---

---

## Setup the analysis environment
These are short instructions for setting up the general frameworks that I use for the Snuffelfiets analysis pipeline.


1. Install Miniforge
- Download Miniforge from : https://github.com/conda-forge/miniforge
    - e.g. windows version: https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe

2. Install VScode
- Add the VScode extension 'Jupyter'
- some optional extensions:
    - Python
    - Pylance
    - Rainbow CSV
    - Github copilot

3. Create the conda environment (e.g. for 'snuffelfiets')
- Open a Miniforge terminal
- Follow instructions detailed in [Installatie](#installatie)
    - If git is not found on your sytem, please install it first in the base environment with:
    `conda install git`

4. Choose the 'snuffelfiets' environment in VScode (background: https://code.visualstudio.com/docs/python/environments)
- Add the project folder 'Snuffelfiets' in VScode Explorer (i.e. File -> Open Folder)
- Open een Jupyter notebook, e.g. demos.ipynb
- On the top right there will probably be a button 'Select Kernel'
    - OR: open the command Palette with Ctrl-Shift-P and search the command by starting to type 'Python: Select Interpreter'
- if the 'snuffelfiets' environment is not listed, choose 'Select Another Kernel' => 'Python Environments'
- type the path where the environment's python is installed, probably '~\miniforge3\envs\snuffelfiets\python.exe'
