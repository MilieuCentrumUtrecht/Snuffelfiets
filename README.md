# Snuffelfiets

## Omschrijving

Rapportage en analyse scripts voor het Milieucentrum Utrecht Snuffelfiets project.

## Installatie

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
