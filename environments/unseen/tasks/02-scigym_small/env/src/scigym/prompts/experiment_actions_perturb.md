## Available Experiment Actions

### Observe
This experiment runs the system with default settings.

```json
{
   "action": "observe",
   "meta_data": {}
}
```

### change initial concentrations

This perturbation changes the initial concentrations of the given species. You cannot change the concentration of boundary and constant species.

```json
{
    "action": "change_initial_concentration",
    "meta_data": {
        "id_species1": 0.2, // Set the initial concentration of species id_species1 to 0.2.
        "id_species2": 0.5
        // Only include the id of the species you want to modify. Any species not listed will keep their default values
    }
}
```
