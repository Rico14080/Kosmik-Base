from pathlib import Path
import re
root=Path(__file__).parent
checks={
 "index.html": ["data-home-hero-image"],
 "us.html": ["data-us-sound-image"],
 "shop.html": ["data-gallery-image"],
 "admin.html": ["data-clear-image=\"home-hero\"", "data-clear-image=\"us-photo\"", "data-clear-image=\"live-background\""],
}
for fn,pats in checks.items():
 s=(root/fn).read_text(encoding='utf-8')
 print(fn)
 for p in pats: print(' ',p, bool(re.search(p,s)))
print('OK')
