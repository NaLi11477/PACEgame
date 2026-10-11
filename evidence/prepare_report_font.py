"""Create an OFL derivative with this report's full glyph coverage and unique name."""
from pathlib import Path
import hashlib,json,shutil
from fontTools.ttLib import TTFont
from fontTools import subset
A=Path(__file__).resolve().parent.parent;B=A/'evidence';F=A/'render_fonts';F.mkdir(exist_ok=True)
source=A.parent/'audit_v029/fonts/NotoSerifCJKsc-Regular.otf';text=(B/'build_revision_report.py').read_text()+(B/'report_style.py').read_text()
chars=set(text)|set(chr(i) for i in range(32,127));font=TTFont(source);opts=subset.Options();opts.name_IDs=['*'];opts.name_legacy=True;opts.name_languages=['*'];sub=subset.Subsetter(options=opts);sub.populate(unicodes={ord(c) for c in chars});sub.subset(font)
family='PACEgame Revision 0211 CJK'
for n in font['name'].names:
 if n.nameID in (1,3,4,6,16):
  v='PACEgameRevision0211CJK-Regular' if n.nameID==6 else family+' Regular' if n.nameID in (3,4) else family
  n.string=v.encode(n.getEncoding(),errors='replace')
 elif n.nameID in (2,17):n.string='Regular'.encode(n.getEncoding())
out=F/'PACEgameRevision0211CJK-Regular.otf';font.save(out);shutil.copyfile(A.parent/'audit_v029/fonts/OFL.txt',F/'OFL.txt')
meta={'source':'Noto Serif CJK SC Regular; frozen full OFL source','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'derivative_family':family,'requested_unicode_count':len(chars),'derivative_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'license':'SIL Open Font License 1.1; bundled OFL.txt','purpose':'Unique family avoids collision with older incomplete audit font subsets.'}
(F/'font_provenance.json').write_text(json.dumps(meta,indent=2)+'\n')
(F/'fonts.conf').write_text(f'''<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig><dir>{F}</dir><dir>/usr/share/fonts/truetype</dir><dir>/opt/libreoffice/share/fonts/truetype</dir><cachedir>{F}/cache</cachedir><config></config></fontconfig>''')
print(meta)
