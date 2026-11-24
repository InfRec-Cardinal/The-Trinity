import json
from pathlib import Path
import datasets

class MyMultiSplitDataset(datasets.GeneratorBasedBuilder):
    BUILDER_CONFIGS = [
        datasets.BuilderConfig(name="things", version=datasets.Version("1.0.0"), description="Things dataset"),
        datasets.BuilderConfig(name="celebs", version=datasets.Version("1.0.0"), description="Celebs dataset"),
    ]

    def _info(self):
        if self.config.name == "things":
            features = datasets.Features({
                "text": datasets.Value("string"),
            })
        elif self.config.name == "celebs":
            features = datasets.Features({
                "text": datasets.Value("string"),
            })
        return datasets.DatasetInfo(
            description="Description of the dataset",
            features=features,
        )

    def _split_generators(self, dl_manager):
        # Datasets may cache this module away from the local resource directory.
        root = Path(getattr(dl_manager, 'base_path', '') or '.')
        if not (root / 'download-bindings.json').is_file():
            root = Path(__file__).resolve().parent
        bindings = json.loads((root / 'download-bindings.json').read_text(encoding='utf-8'))
        local = {f['rfilename']: f['packagedPath'] for f in bindings['files'] if 'packagedPath' in f}
        return [datasets.SplitGenerator(name=key, gen_kwargs={'filepath': str((root / local[f'{self.config.name}/{name}.txt']).resolve(strict=True))})
                for key, name in ((datasets.Split.TRAIN, 'train'), (datasets.Split.VALIDATION, 'dev'), (datasets.Split.TEST, 'test'))]

    def _generate_examples(self, filepath):
        with open(filepath, encoding="utf-8") as f:
            for idx, line in enumerate(f):
                yield idx, {
                    "text": line.split(",")[0],
                }