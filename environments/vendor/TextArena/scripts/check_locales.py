#!/usr/bin/env python3
                                                            

                                                    

                                                                   
                                                          
                                                                                
                                                                             
                                                                           
                                                                                  
                                                                                 
                                                                                 
                                                                           
                                                                               
                                                                                 
                                                                       
                                                                               
                                                                               
                                                                               

                                                                                
                                                        

                                                                               
                                                             

      
                                                                          
                                                                       
                                                                              
                                                                                
   
import argparse
import ast
import json
import os
import re
import string
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENVS_DIR = os.path.join(REPO_ROOT, "textarena", "envs")
DEFAULT_LANGS = ["ar", "de", "en", "es", "fr", "he", "ms", "zh", "kn", "be", "gu", "pa", "mr", "ps", "te", "sd", "ne", "lo", "uz", "ml", "zu", "as", "km", "hy", "cy", "si", "kk", "or", "my", "so", "mg", "ky", "ka", "ha", "ig", "mn", "eu", "yo", "am", "ceb", "bjn", "ars", "arz", "acq", "crh", "apc", "ajp", "bho", "ace", "acm", "ary", "ckb", "aeb", "ast", "bug", "ayr", "bam", "bem", "cjk", "ban", "awa", "bak", "azb", "bod", "aka", "epo", "gla", "fur", "gle", "fao", "fij", "grn", "gaz", "ewe", "fuv", "dzo", "dik", "fon", "dyu", "jav", "hat", "lmo", "lim", "ltz", "hne", "mai", "mag", "kmr", "ilo", "lij", "kas", "lus", "kin", "ltg", "kea", "lin", "lug", "luo", "lua", "kac", "kik", "kab", "kon", "knc", "kbp", "kmb", "kam", "sun", "scn", "pap", "oci", "sot", "min", "nya", "sna", "srd", "smo", "szl", "mri", "mlt", "nno", "pag", "mni", "tat", "nso", "ssw", "san", "run", "shn", "sat", "quy", "nus", "sag", "mos", "taq", "vec", "ydd", "tgk", "xho", "war", "uig", "tir", "tso", "tuk", "tsn", "tpi", "tum", "tzm", "twi", "wol", "umb"]

SLOT_RE = re.compile(r"{[^{}]*}")
ALPHA_RE = re.compile(r"[^\W\d_]", re.UNICODE)                      


                                                                               
def _no_dupes(pairs):
    seen, dupes = {}, []
    for k, v in pairs:
        if k in seen:
            dupes.append(k)
        seen[k] = v
    if dupes:
        raise ValueError("duplicate keys: " + ", ".join(sorted(set(dupes))))
    return seen


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=_no_dupes)


                                                                             
def flatten(data, prefix=()):
    pass                                                                   
    for k, v in data.items():
        if not prefix and k.startswith("_"):
            continue
        path = prefix + (k,)
        if isinstance(v, dict):
            yield from flatten(v, path)
        elif isinstance(v, str):
            yield path, v


def all_strings(data, prefix=()):
    pass                                                           
    for k, v in data.items():
        path = prefix + (k,)
        if isinstance(v, dict):
            yield from all_strings(v, path)
        elif isinstance(v, str):
            yield path, v


def slots_of(value):
    return sorted(SLOT_RE.findall(value))


class SafeDict(dict):
    def __missing__(self, key):
        return "<%s>" % key


def render_smoke(value):
    try:
        string.Formatter().vformat(value, (), SafeDict())
        return None
    except (ValueError, IndexError, KeyError) as e:
        return f"{type(e).__name__}: {e}"


                                                                                
def code_keys(env_path):
    pass                                                              

                                                                                
                                                                            
                                                                   
    with open(env_path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=env_path)
    literal, dynamic = set(), False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if not (isinstance(fn, ast.Attribute) and fn.attr in ("m", "t")):
            continue
        if not (isinstance(fn.value, ast.Name) and fn.value.id == "self"):
            continue
        parts, is_dynamic = [], False
        for arg in node.args:                                     
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                parts.append(arg.value)
            else:
                is_dynamic = True
                break
                                                                                 
                                                                                   
                                                                             
        if is_dynamic or not parts:
            dynamic = dynamic or (is_dynamic and bool(node.args))
        else:
            literal.add(".".join(parts))
    return literal, dynamic


                                                                                 
def check_game(game_dir, required_langs):
    errors, warnings = [], []
    loc_dir = os.path.join(game_dir, "locales")
                                                                                     
    present = sorted(
        f[:-5] for f in os.listdir(loc_dir)
        if f.endswith(".json") and not f.startswith("_")
    )

                                                                                
                                                                              
                                                   
    supported_path = os.path.join(loc_dir, "_supported_langs.json")
    if os.path.exists(supported_path):
        try:
            declared = load_json(supported_path)
            required_langs = [l for l in required_langs if l in declared]
        except (json.JSONDecodeError, ValueError) as e:
            errors.append(f"_supported_langs.json: {e}")

    missing_langs = [l for l in required_langs if l not in present]
    extra_langs = [l for l in present if l not in required_langs]
    if missing_langs:
        errors.append(f"missing language files: {', '.join(missing_langs)}")
    if extra_langs:
        warnings.append(f"extra (non-standard) language files: {', '.join(extra_langs)}")

                                    
    data = {}
    for lang in present:
        try:
            data[lang] = load_json(os.path.join(loc_dir, f"{lang}.json"))
        except (json.JSONDecodeError, ValueError) as e:
            errors.append(f"{lang}.json: {e}")

    if "en" not in data:
        errors.append("no valid en.json (needed as reference); skipping content checks")
        return errors, warnings

    en_leaves = dict(flatten(data["en"]))
    en_keys = set(en_leaves)
    en_slots = {k: slots_of(v) for k, v in en_leaves.items()}

                                         
    for path, val in all_strings(data["en"]):
        err = render_smoke(val)
        if err:
            errors.append(f"en.json {'.'.join(path)}: render error: {err}")

                         
    for lang in present:
        if lang == "en" or lang not in data:
            continue
        leaves = dict(flatten(data[lang]))
        keys = set(leaves)
        for k in sorted(en_keys - keys):
            errors.append(f"{lang}.json: missing key '{'.'.join(k)}'")
        for k in sorted(keys - en_keys):
            errors.append(f"{lang}.json: extra key '{'.'.join(k)}' not in en.json")
        for k in sorted(en_keys & keys):
            if slots_of(leaves[k]) != en_slots[k]:
                errors.append(
                    f"{lang}.json: slot mismatch at '{'.'.join(k)}': "
                    f"en={en_slots[k]} {lang}={slots_of(leaves[k])}"
                )
            elif leaves[k] == en_leaves[k] and ALPHA_RE.search(SLOT_RE.sub('', en_leaves[k])):
                warnings.append(f"{lang}.json: value identical to English at '{'.'.join(k)}' (untranslated?)")
        for path, val in all_strings(data[lang]):
            err = render_smoke(val)
            if err:
                errors.append(f"{lang}.json {'.'.join(path)}: render error: {err}")

                                                         
    env_path = os.path.join(game_dir, "env.py")
    if os.path.isfile(env_path):
        used, dynamic = code_keys(env_path)
        en_keys_dotted = {".".join(k) for k in en_keys}
        for k in sorted(used - en_keys_dotted):
            errors.append(f"env.py uses key '{k}' missing from en.json")
                                                                      
        if not dynamic:
            for k in sorted(en_keys_dotted - used):
                warnings.append(f"en.json key '{k}' is never used in env.py (dead key?)")
        if dynamic:
            warnings.append("env.py builds some locale keys dynamically; code coverage is partial")
    else:
        warnings.append("no env.py found next to locales/; skipped code coverage")

    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("games", nargs="*", help="specific game names (default: all localized games)")
    ap.add_argument("--langs", default=",".join(DEFAULT_LANGS), help="comma-separated required languages")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args()
    required_langs = [l.strip() for l in args.langs.split(",") if l.strip()]

    games = args.games or sorted(
        d for d in os.listdir(ENVS_DIR)
        if os.path.isdir(os.path.join(ENVS_DIR, d, "locales"))
    )

    total_err = total_warn = 0
    for game in games:
        loc_dir = os.path.join(ENVS_DIR, game, "locales")
        if not os.path.isdir(loc_dir):
            print(f"SKIP {game}: no locales/ folder")
            continue
        errors, warnings = check_game(os.path.join(ENVS_DIR, game), required_langs)
        if args.strict:
            errors = errors + warnings
            warnings = []
        if not errors and not warnings:
            print(f"OK   {game}")
        else:
            print(f"{'FAIL' if errors else 'WARN'} {game}")
            for w in warnings:
                print(f"       warn: {w}")
            for e in errors:
                print(f"       err:  {e}")
        total_err += len(errors)
        total_warn += len(warnings)

    print()
    if total_err:
        print(f"FAILED: {total_err} error(s), {total_warn} warning(s) across {len(games)} game(s).")
        return 1
    print(f"PASSED: {len(games)} game(s), 0 errors, {total_warn} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
