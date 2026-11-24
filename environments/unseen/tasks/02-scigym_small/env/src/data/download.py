import os
from argparse import ArgumentParser
from pathlib import Path

from datasets import load_dataset


def main(args):
                                                                      
    dataset = load_dataset("h4duan/scigym-sbml", split=args.split)

                                              
    os.makedirs(args.save_dir, exist_ok=True)
    args.save_dir = Path(args.save_dir) / args.split
    os.makedirs(args.save_dir, exist_ok=True)

                                                                                     
    for i, row in enumerate(dataset):
                                       
        instance_folder = Path(args.save_dir) / row["folder_name"]
        os.makedirs(instance_folder, exist_ok=True)

                                
        path_to_truth = instance_folder / "truth.xml"
        path_to_partial = instance_folder / "partial.xml"
        path_to_sedml = instance_folder / "truth.sedml"

        if args.overwrite or not path_to_truth.exists():
            with open(path_to_truth, "w") as f:
                f.write(row["truth_xml"])

        if args.overwrite or not path_to_partial.exists():
            with open(path_to_partial, "w") as f:
                f.write(row["partial"])

        if args.overwrite or not path_to_sedml.exists():
            with open(path_to_sedml, "w") as f:
                f.write(row["truth_sedml"])


if __name__ == "__main__":
    parser = ArgumentParser(description="Download the SciGym SBML dataset.")
    parser.add_argument(
        "--split",
        type=str,
        default="small",
        help="Specify the split to download (small, large). Default is 'small'.",
    )
    parser.add_argument(
        "--save_dir",
        type=str,
        default=Path(__file__).parent,
        help="Directory to save the downloaded dataset. Default is current file directory.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the existing files in the save directory.",
    )

    args = parser.parse_args()

    main(args)
