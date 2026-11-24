from datasets import DatasetDict, load_dataset

def load_my_multi_split_dataset():
    things = DatasetDict({
        "train": load_dataset("yizheapple/entity-deduction-arena", name="things", split="train"),
        "dev": load_dataset("yizheapple/entity-deduction-arena", name="things", split="dev"),
        "test": load_dataset("yizheapple/entity-deduction-arena", name="things", split="test")
    })

    celebs = DatasetDict({
        "train": load_dataset("yizheapple/entity-deduction-arena", name="celebs", split="train"),
        "dev": load_dataset("yizheapple/entity-deduction-arena", name="celebs", split="dev"),
        "test": load_dataset("yizheapple/entity-deduction-arena", name="celebs", split="test")
    })

    return {"things": things, "celebs": celebs}