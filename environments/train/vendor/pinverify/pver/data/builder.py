import os
import json
import glob
import random
from tqdm import tqdm
from pathlib import Path


class IndexBuilder:
    pass                                                               
                                                                               
                                                                  
       

    def __init__(self, dataset_root, capture_subdir="pin_capture", split="val"):
        self.dataset_root = dataset_root
        self.capture_subdir = capture_subdir
        self.split = split

    def build_index(self, output_path, seed=42):
        random.seed(seed)

        search_pattern = os.path.join(
            self.dataset_root, self.capture_subdir, self.split, "*", "*", "meta.json"
        )
        print(f"Searching: {search_pattern}")
        meta_files = glob.glob(search_pattern)

        episodes = []
        stats = {"total": 0, "skipped_no_valid_start": 0}

        print(f"Found {len(meta_files)} meta.json files. Parsing...")

        for mf in tqdm(meta_files):
            try:
                with open(mf, 'r', encoding='utf-8') as f:
                    meta = json.load(f)

                scene_key = meta.get("scene_key")
                episode_id = str(meta.get("episode_id", ""))
                object_id = meta.get("object_id")
                object_cat = meta.get("object_category")

                                                       
                episode_path = str(Path(mf).parent.relative_to(self.dataset_root)).replace("\\", "/")

                                                                         
                valid_start_sectors, navigable_sectors = self._parse_sector_info(meta)

                                                             
                if not valid_start_sectors:
                    stats["skipped_no_valid_start"] += 1
                    continue

                                                                  
                episode_entry = {
                                                                                             
                    "episode_path": episode_path,
                    "scene": scene_key,
                    "episode": episode_id,
                    "meta_path": episode_path + "/meta.json",
                    "rgb_dir": episode_path + "/rgb",
                    "depth_dir": episode_path + "/depth",
                    "target_object_id": object_id,
                    "target_object_category": object_cat,
                                           
                    "valid_start_sectors": sorted(valid_start_sectors),
                    "navigable_sectors": sorted(navigable_sectors),
                    "n_navigable": len(navigable_sectors),
                    "n_mask_visible": len(valid_start_sectors),
                }

                episodes.append(episode_entry)
                stats["total"] += 1

            except Exception as e:
                print(f"Error parsing {mf}: {e}")

              
        print(f"Saving {stats['total']} episodes to {output_path}")
        if stats["skipped_no_valid_start"]:
            print(f"  Skipped {stats['skipped_no_valid_start']} episodes (no valid start sector)")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            for ep in episodes:
                f.write(json.dumps(ep) + "\n")

        return episodes

    def _parse_sector_info(self, meta):
        pass                                                                   
        viewpoints = meta.get("viewpoints")
        captures = meta.get("captures", [])

        valid_start_sectors = set()
        navigable_sectors = set()

        if viewpoints is not None:
                                                    
            for vp in viewpoints:
                tag = vp.get("tag", "")
                sector_idx = vp.get("sector_index", self._parse_sector_from_tag(tag))
                navigable = vp.get("navigable", False)
                has_mask = vp.get("mask_meets_threshold", False)
                rgb = vp.get("rgb")

                if navigable and rgb:
                    navigable_sectors.add(sector_idx)
                if has_mask:
                    valid_start_sectors.add(sector_idx)
        else:
                                                                   
            for cap in captures:
                tag = cap.get("tag", "")
                sector_idx = self._parse_sector_from_tag(tag)
                rgb = cap.get("rgb", "")
                navigable = cap.get("navigable", True)
                has_mask = cap.get("mask_meets_threshold", True)

                if navigable and rgb:
                    navigable_sectors.add(sector_idx)
                if has_mask:
                    valid_start_sectors.add(sector_idx)

        return valid_start_sectors, navigable_sectors

    @staticmethod
    def _parse_sector_from_tag(tag):
        pass                                                          
        if tag.startswith("s"):
            try:
                return int(tag.split("_")[0][1:])
            except (ValueError, IndexError):
                pass
        return -1


class NegativeSampler:
    pass                                                              
                                                                         
       

    def __init__(self, distractors_map_path):
        with open(distractors_map_path, 'r', encoding='utf-8') as f:
            self.distractors_map = json.load(f)
        print(f"Loaded distractors map: {len(self.distractors_map)} target objects")

    def augment_index(self, index_path, output_path):
        pass                                                        
                                                                  
                                                                  
                                                                       

                                                                   
                                                                      
           
        with open(index_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        print(f"Augmenting {len(lines)} episodes with 1:1:1 pairs...")

        pairs = []
        skipped = {"no_distractors": 0, "no_neg_same": 0, "no_neg_diff": 0}

        for line in tqdm(lines):
            ep = json.loads(line)
            obj_id = ep["target_object_id"]
            obj_cat = ep["target_object_category"]

                                                        
            entry = self.distractors_map.get(obj_id)
            if entry is None:
                skipped["no_distractors"] += 1
                continue

            distractors = entry.get("distractors", [])
            same_cat = [d for d in distractors if d["object_category"] == obj_cat]
            diff_cat = [d for d in distractors if d["object_category"] != obj_cat]

            if not same_cat:
                skipped["no_neg_same"] += 1
                continue
            if not diff_cat:
                skipped["no_neg_diff"] += 1
                continue

                                   
            pos = dict(ep)
            pos["query_object_id"] = obj_id
            pos["query_object_category"] = obj_cat
            pos["label"] = 1
            pos["pair_type"] = "positive"
            pairs.append(pos)

                                   
            neg_s_entry = random.choice(same_cat)
            neg_s = dict(ep)
            neg_s["query_object_id"] = neg_s_entry["object_id"]
            neg_s["query_object_category"] = neg_s_entry["object_category"]
            neg_s["label"] = 0
            neg_s["pair_type"] = "neg_same"
            pairs.append(neg_s)

                                   
            neg_d_entry = random.choice(diff_cat)
            neg_d = dict(ep)
            neg_d["query_object_id"] = neg_d_entry["object_id"]
            neg_d["query_object_category"] = neg_d_entry["object_category"]
            neg_d["label"] = 0
            neg_d["pair_type"] = "neg_diff"
            pairs.append(neg_d)

                                               
        random.shuffle(pairs)

        with open(output_path, 'w', encoding='utf-8') as f:
            for p in pairs:
                f.write(json.dumps(p) + "\n")

        n_pos = sum(1 for p in pairs if p["pair_type"] == "positive")
        n_ns = sum(1 for p in pairs if p["pair_type"] == "neg_same")
        n_nd = sum(1 for p in pairs if p["pair_type"] == "neg_diff")
        print(f"  Generated {len(pairs)} pairs (positive={n_pos}, neg_same={n_ns}, neg_diff={n_nd})")
        if any(skipped.values()):
            print(f"  Skipped episodes: {skipped}")


def sample_balanced_episodes(raw_index_path, output_path, max_episodes, seed=42):
    pass                                                                   

             
                                                                      
                                                                      
                                                                                     

         
                                                                          
                                                  
                                                         
                         
       
    random.seed(seed)

    with open(raw_index_path, 'r', encoding='utf-8') as f:
        episodes = [json.loads(line) for line in f if line.strip()]

    total = len(episodes)
    if total <= max_episodes:
        print(f"  No sampling needed: {total} episodes <= {max_episodes} max")
                   
        import shutil
        shutil.copy2(raw_index_path, output_path)
        return episodes

                                                   
    by_cat = {}                                           
    for ep in episodes:
        cat = ep.get("target_object_category", "unknown")
        obj_id = ep["target_object_id"]
        by_cat.setdefault(cat, {}).setdefault(obj_id, []).append(ep)

    n_cats = len(by_cat)
    base_quota = max_episodes // n_cats
    remainder = max_episodes - base_quota * n_cats

    print(f"  Category-balanced sampling: {max_episodes} from {total} episodes")
    print(f"  Categories: {n_cats}, base quota: {base_quota}, remainder: {remainder}")

                                                                                       
    sorted_cats = sorted(by_cat.keys(), key=lambda c: sum(len(eps) for eps in by_cat[c].values()))

                                                                          
    quotas = {}
    for i, cat in enumerate(sorted_cats):
        quotas[cat] = base_quota + (1 if i >= n_cats - remainder else 0)

    sampled = []
    cat_stats = {}

    for cat in sorted_cats:
        obj_dict = by_cat[cat]
        quota = quotas[cat]
        cat_episodes = []

                                                                        
        obj_ids = list(obj_dict.keys())
        random.shuffle(obj_ids)
        for oid in obj_ids:
            if len(cat_episodes) >= quota:
                break
            cat_episodes.append(random.choice(obj_dict[oid]))

                                                                                      
        if len(cat_episodes) < quota:
                                                                   
            selected_set = set(id(ep) for ep in cat_episodes)
            remaining_pool = [
                ep for oid in obj_ids for ep in obj_dict[oid]
                if id(ep) not in selected_set
            ]
            random.shuffle(remaining_pool)
            need = quota - len(cat_episodes)
            cat_episodes.extend(remaining_pool[:need])

                          
        actual = min(len(cat_episodes), quota)
        cat_episodes = cat_episodes[:actual]

        n_unique_ids = len(set(ep["target_object_id"] for ep in cat_episodes))
        cat_stats[cat] = {"sampled": len(cat_episodes), "unique_ids": n_unique_ids,
                          "available": sum(len(eps) for eps in obj_dict.values())}
        sampled.extend(cat_episodes)

                          
    random.shuffle(sampled)

    with open(output_path, 'w', encoding='utf-8') as f:
        for ep in sampled:
            f.write(json.dumps(ep) + "\n")

    print(f"  Sampled {len(sampled)} episodes:")
    for cat in sorted(cat_stats.keys()):
        s = cat_stats[cat]
        print(f"    {cat:20s}: {s['sampled']:3d} episodes, "
              f"{s['unique_ids']:2d} unique IDs (of {s['available']} available)")

    total_unique = len(set(ep["target_object_id"] for ep in sampled))
    print(f"  Total unique object IDs: {total_unique}")

    return sampled


def generate_subsets(full_index_path, output_dir, sizes=(50, 100, 500, 1000), seed=42):
    pass                                                                              
    random.seed(seed)
    with open(full_index_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    total = len(lines)
    print(f"Full index: {total} pairs")

                                                
    by_type = {}                            
    for line in lines:
        ep = json.loads(line)
        pt = ep.get("pair_type", "positive")
        by_type.setdefault(pt, []).append(line)

    type_ratios = {pt: len(lst) / total for pt, lst in by_type.items()}
    print(f"Full index pair_type distribution: { {pt: len(lst) for pt, lst in by_type.items()} }")

    for n in sizes:
        if n >= total:
            print(f"  Subset {n}: skipped (>= total {total})")
            continue

                                                       
        sampled = []
        remaining = n
        sorted_types = sorted(by_type.keys())
        for i, pt in enumerate(sorted_types):
            pool = by_type[pt]
            if i == len(sorted_types) - 1:
                                                                    
                k = remaining
            else:
                k = round(n * type_ratios[pt])
            k = min(k, len(pool), remaining)
            sampled.extend(random.sample(pool, k))
            remaining -= k

        random.shuffle(sampled)
        out_path = os.path.join(output_dir, f"pv_index_{n}.jsonl")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.writelines(sampled)

                                    
        dist = {}
        for line in sampled:
            pt = json.loads(line).get("pair_type", "positive")
            dist[pt] = dist.get(pt, 0) + 1
        print(f"  Subset {n}: saved to {out_path}  distribution={dist}")

                              
    nav_counts = []
    mask_counts = []
    cats = {}
    for line in lines:
        ep = json.loads(line)
        nav_counts.append(ep.get("n_navigable", 0))
        mask_counts.append(ep.get("n_mask_visible", 0))
        cat = ep.get("target_object_category", "unknown")
        cats[cat] = cats.get(cat, 0) + 1

    print(f"\n--- Dataset Statistics ---")
    print(f"Total pairs: {total}")
    if nav_counts:
        print(f"Navigable sectors:  min={min(nav_counts)}, max={max(nav_counts)}, avg={sum(nav_counts)/len(nav_counts):.1f}")
        print(f"Mask-visible sectors: min={min(mask_counts)}, max={max(mask_counts)}, avg={sum(mask_counts)/len(mask_counts):.1f}")
    print(f"Categories ({len(cats)}): {dict(sorted(cats.items(), key=lambda x: -x[1]))}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Dataset root (e.g. ./data/pv_dataset)")
    parser.add_argument("--distractors-map", required=True,
                        help="Path to object_goal_distractors_map.json")
    parser.add_argument("--out-dir", required=True, help="Output directory for index files (e.g. ./data/pv_dataset/val)")
    parser.add_argument("--subsets", type=int, nargs="*", default=[50, 100, 500, 1000], help="Subset sizes to generate")
    parser.add_argument("--max-episodes", type=int, default=None,
                        help="Max raw episodes before pair generation (e.g. 1000 -> 3000 total pairs). "
                             "Category-balanced sampling is applied. Default: use all episodes.")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

                                                          
    builder = IndexBuilder(args.root)
    tmp_index = os.path.join(args.out_dir, "_tmp_raw.jsonl")
    builder.build_index(tmp_index, seed=args.seed)

    sampler = NegativeSampler(args.distractors_map)

                                                        
    full_index_all = os.path.join(args.out_dir, "pv_index_all.jsonl")
    random.seed(args.seed)
    sampler.augment_index(tmp_index, full_index_all)

    if args.max_episodes is not None:
                                     
        with open(full_index_all, 'r') as f:
            n_full = sum(1 for _ in f)

                                                          
        archive_name = os.path.join(args.out_dir, f"pv_index_all_{n_full}.jsonl")
        os.rename(full_index_all, archive_name)
        print(f"\nArchived full index: {archive_name} ({n_full} pairs)")

                                                                   
        print(f"\n--- Category-balanced sampling: {args.max_episodes} episodes ---")
        sampled_index = os.path.join(args.out_dir, "_tmp_sampled.jsonl")
        sample_balanced_episodes(tmp_index, sampled_index, args.max_episodes, seed=args.seed)

        random.seed(args.seed)
        sampler.augment_index(sampled_index, full_index_all)
        os.remove(sampled_index)

    os.remove(tmp_index)

                                                                                                                
    if args.subsets:
        generate_subsets(full_index_all, args.out_dir, sizes=args.subsets, seed=args.seed)
