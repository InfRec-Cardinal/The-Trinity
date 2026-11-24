                                                                                       

                                                                   
                                                                                            
                                                                                     
                                                                                      
                                                                                                  
   
import hashlib, io, json, os, sys, zipfile
import numpy as np

EXPECTED = {
    'glove.6B.100d.f64.npy': '167d9dfad441ea35b033618e11f89c21b61b3350e83410ccd8c2407314182f03',
    'glove.6B.50d.f64.npy': '5cca5c6e49d2af2b23d9638685e6d52cfd9fba4c2064e00385b213e949fda539',
    'glove.6B.100d.vocab.json': '495eb5242173e8967ff241ba5a6e93bf677207d946df69d860252805e777882f',
}

def main(zip_path, out):
    os.makedirs(out, exist_ok=True)
    vocab = None
    with zipfile.ZipFile(zip_path) as z:
        for dim in (100, 50):
            words, rows = [], []
            with z.open(f'glove.6B.{dim}d.txt') as raw:
                for line in io.TextIOWrapper(raw, encoding='utf-8'):
                    parts = line.rstrip('\n').split(' ')
                    words.append(parts[0])
                    rows.append([float(x) for x in parts[1:]])
            np.save(os.path.join(out, f'glove.6B.{dim}d.f64.npy'), np.array(rows, dtype=np.float64))
            if vocab is None:
                vocab = words
                with open(os.path.join(out, 'glove.6B.100d.vocab.json'), 'w', encoding='utf-8') as f:
                    json.dump(vocab, f)
            elif words != vocab:
                sys.exit('50d and 100d vocabularies differ')
    ok = True
    for name, want in EXPECTED.items():
        with open(os.path.join(out, name), 'rb') as f:
            got = hashlib.sha256(f.read()).hexdigest()
        print(name, 'OK' if got == want else f'MISMATCH {got}')
        ok &= got == want
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
