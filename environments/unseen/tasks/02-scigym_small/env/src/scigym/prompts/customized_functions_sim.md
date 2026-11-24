```python
def simulate(sbml_string: str) -> pd.DataFrame:
   """
   Simulates an SBML model and returns time series data.

   You can use this function to run simulations on your hypothesis model and compare it with the data gathered from the experiments.

   Args:
       sbml_string: an SBML model in xml format

   Returns:
       - A pandas dataframe of time series data for the given sbml models (with columns 'Time' and the species ID.)
   """
```
