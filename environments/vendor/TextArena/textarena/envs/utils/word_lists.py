                                                                        

import importlib.resources
import re
from collections import defaultdict
from typing import Optional

                     
import nltk
from nltk.corpus import words



def _parse_affix_rules(file_content: list[str]):
                                                         
    pattern = re.compile(r"^(PFX|SFX)\s+(\w+)\s+(Y|N)\s+(\S+)\s+([\'|\w]+)\s+(\S+)$")

                                     
    prefixes = defaultdict(list)
    suffixes = defaultdict(list)

                                                
    for line in file_content:
        match = pattern.match(line.strip())
        if match:
            affix_type, flag, can_merge, strip_char, affix, condition = match.groups()
            rule = {
                "flag": flag,
                "can_merge": can_merge == "Y",
                "strip_char": strip_char if strip_char != "0" else None,
                "affix": affix,
                "condition": condition if condition != "." else None,
            }
            if affix_type == "PFX":
                prefixes[flag].append(rule)
            else:
                suffixes[flag].append(rule)

    return prefixes, suffixes


def _parse_condition(condition):
    pass                                                
    if not condition:
        return None, None
    pattern = re.compile(r"(\[\^\S+\])?(\S+)?")
    match = pattern.match(condition)
    if match:
        exclude, include = match.groups()
        return exclude, include
    return None, None


def _split(line: str) -> tuple[str, str]:
    pass                                                          
    if "/" in line:
        return tuple(line.split("/"))
    return line.strip(), ""


class EnglishDictionary:
    pass                                     

    def __init__(
        self, keep_proper_nouns=False, include_nltk=True, keep_non_alpha=False
    ):
        pass                            
        nltk.download("words")
        
        self.include_nltk = include_nltk
        self.keep_non_alpha = keep_non_alpha
        self.keep_proper_nouns = keep_proper_nouns
        self.uk_words = self._load_dic("en_GB.dic", "en.aff")
                                                                  
        self.us_words = self._load_dic("en_US.dic", "en.aff")
                                                                  
        self.nltk_words = self._load_nltk(basic=False) if include_nltk else set()
        self.nltk_basic_words = self._load_nltk(basic=True) if include_nltk else set()

    def _filter(
        self,
        word_set: set[str],
    ) -> set[str]:
        filtered = set()
        for word in word_set:
            if word[0].isalpha() or self.keep_non_alpha:
                if word[0].islower() or self.keep_proper_nouns:
                    filtered.add(word)
        return filtered

    def _load_dic(
        self,
        filename: str,
        acc_filename: str,
    ) -> set[str]:
        pass                                                               
        with (
            importlib.resources.files("textarena.envs.utils.data")
            .joinpath(filename)
            .open("r") as f
        ):
            lines = f.readlines()[1:]                                
        with (
            importlib.resources.files("textarena.envs.utils.data")
            .joinpath(acc_filename)
            .open("r") as f
        ):
            acc_lines = f.readlines()
        prefixes, suffixes = _parse_affix_rules(acc_lines)
        entries = set(_split(line) for line in lines)
        filtered = self._filter(entries)
        all_words = set()
                                     
        for word, flag in filtered:
            all_words.add(word)
        prefixed_words = set()
        for word, flags in filtered:
            for flag in list(flags):
                if flag in prefixes:
                                  
                    for rule in prefixes[flag]:
                                                       
                        exclude, include = _parse_condition(rule["condition"])
                        if exclude and any(
                            [word.endswith(exclude_char) for exclude_char in exclude]
                        ):
                            continue
                        if include and not word.endswith(include):
                            continue
                        if rule["strip_char"]:
                            if word.startswith(rule["strip_char"]):
                                new_word = (
                                    word[len(rule["strip_char"]) :] + rule["affix"]
                                )
                                all_words.add(new_word)
                                prefixed_words.add((new_word, flags))
                        else:
                            new_word = rule["affix"] + word
                            all_words.add(new_word)
                            prefixed_words.add(
                                (new_word, flags)
                            )                                    
        for word, flags in filtered:
            for flag in list(flags):
                if flag in suffixes:
                                  
                    for rule in suffixes[flag]:
                                                       
                        exclude, include = _parse_condition(rule["condition"])
                        if exclude and any(
                            [word.endswith(exclude_char) for exclude_char in exclude]
                        ):
                            continue
                        if include and not word.endswith(include):
                            continue
                        if rule["strip_char"]:
                            if word.endswith(rule["strip_char"]):
                                new_word = (
                                    word[: -len(rule["strip_char"])] + rule["affix"]
                                )
                                all_words.add(new_word)
                        else:
                            new_word = word + rule["affix"]
                            all_words.add(new_word)
                                                    
        for word, flags in prefixed_words:
            for flag in list(flags):
                if flag in suffixes:
                                  
                    for rule in suffixes[flag]:
                                                           
                        if not rule["can_merge"]:
                            continue
                                                       
                        exclude, include = _parse_condition(rule["condition"])
                        if exclude and word.endswith(exclude):
                            continue
                        if include and not word.endswith(include):
                            continue
                        if rule["strip_char"]:
                            if word.endswith(rule["strip_char"]):
                                new_word = (
                                    word[: -len(rule["strip_char"])] + rule["affix"]
                                )
                                all_words.add(new_word)
                        else:
                            new_word = word + rule["affix"]
                            all_words.add(new_word)
        all_words = self._filter(all_words)
        return all_words

    def _load_nltk(self, basic: bool) -> set[str]:
        nltk_words = set(words.words("en-basic") if basic else words.words("en"))
        return self._filter(nltk_words)

    def is_english_word(self, word: str) -> bool:
        pass                                                                        
        word = word.lower()
        return word in self.uk_words or word in self.us_words or word in self.nltk_words

                                                                            
    def is_valid(self, word: str) -> bool:
        pass                                                     
        return self.is_english_word(word)

    def get_all_words(self) -> set[str]:
        pass                                          
        return self.uk_words | self.us_words | self.nltk_words

    def get_basic_words(self) -> set[str]:
        pass                                                     
        return self.nltk_basic_words


                                                                            
                                                    
                                                                            
                                                                              
                                                                              
                                                                               
                                                                    
                                                                                
                         

                                                                        
                                                                                
DEFAULT_MIN_ZIPF = 2.5

                                                                            
                                                                        
                                                                               
                                    
NON_ALPHABETIC_LANGS = {"zh", "ja", "ko", "hi", "bn", "ta"}

                                                                     
                                                                           
                                                                                  
WORDFREQ_ALIASES = {"sr": "sh", "hr": "sh"}


class WordFreqDictionary:
    pass                                                                     

    def __init__(self, lang: str, min_zipf: float = DEFAULT_MIN_ZIPF, pool_size: int = 40000):
        try:
            import wordfreq
        except ImportError as e:                                                
            raise RuntimeError(
                f"Word games in language '{lang}' require the optional 'wordfreq' "
                f"package. Install it with:  pip install textarena[wordgames]  "
                f"(or: pip install wordfreq). English needs no extra install."
            ) from e
        self.ui_lang = lang
                                                                           
        wf_lang = WORDFREQ_ALIASES.get(lang, lang)
        if wf_lang not in wordfreq.available_languages():
            raise ValueError(f"wordfreq has no word data for language '{lang}'.")
        self._wf = wordfreq
        self.lang = wf_lang
        self.min_zipf = min_zipf
        self.pool_size = pool_size
        self._pool = None                                     

    def is_valid(self, word: str) -> bool:
        pass                                                                       
        return self._wf.zipf_frequency(word.lower(), self.lang) >= self.min_zipf

    def zipf(self, word: str) -> float:
        pass                                                                   

                                                                             
                                                             
        return self._wf.zipf_frequency(word.lower(), self.lang)

    def get_all_words(self) -> set[str]:
        pass                                                                       
        if self._pool is None:
            self._pool = {
                w.lower()
                for w in self._wf.top_n_list(self.lang, self.pool_size)
                if w.isalpha()
            }
        return self._pool

    def sample_pool(self, length: Optional[int] = None) -> list:
        pass                                                                            
        pool = self.get_all_words()
        if length is not None:
            return [w for w in pool if len(w) == length]
        return list(pool)

    def letter_frequencies(self) -> "dict":
        pass                                                        

                                                                                
                                                                           
           
        from collections import Counter
        counter = Counter()
        for w in self.get_all_words():
            counter.update(w)
        return dict(counter)

    def alphabet(self) -> list:
        pass                                                           

                                                                               
                                                              
        freqs = self.letter_frequencies()
        return [ch for ch, _ in sorted(freqs.items(), key=lambda kv: (-kv[1], kv[0]))]


def get_dictionary(lang: str, **english_kwargs):
    pass                                   

                                                                                
                                                                                
                                                                        
                   
       
    if lang == "en":
        return EnglishDictionary(**english_kwargs)
    return WordFreqDictionary(lang)
