
def load_prompt(filename: str) -> str:
    pass                                      
    with open(f"textarena/envs/Diplomacy/prompts/{filename}", "r") as f:
        return f.read().strip()

def get_state_specific_prompt(state: str) -> str:
    return load_prompt(f"state_specific/{state.lower()}_system_prompt.txt")





