import hashlib,importlib.util,json,re,sys
from pathlib import Path
R=Path(r"D:\mycode\codex\analysis\tools\Enriched_seed_generate")
P=R/"docs"/"logs"/"260906"/"2x2-all-protocols-raw-count65-20260906"/"recover_partial_exports.py"
O=R/"high_quality_seedsv2"/"r65_recovered_partial"
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); sys.modules[name]=m; s.loader.exec_module(m); return m
def safe(v,n):
 return (re.sub(r"[^a-zA-Z0-9_.-]+","-",str(v)).strip("-._") or "item")[:n]
def install(g):
 def export(lib,out):
  if out.exists(): raise FileExistsError(f"output already exists: {out}")
  sd=out/"sequences"; ad=out/"afl_corpus"; sd.mkdir(parents=True); ad.mkdir(parents=True); exported=[]
  for i,seq in enumerate(lib["sequences"]):
   sid=str(seq["seed_id"]); sh=hashlib.sha256(sid.encode()).hexdigest()[:8]; sn=f"{i:03d}-{safe(sid,24)}-{sh}"; d=sd/sn; fd=d/"frames"; fd.mkdir(parents=True)
   for msg in seq["messages"]:
    raw=bytes.fromhex(msg["hex"]); ident=str(msg.get("label",""))+"|"+str(msg.get("direction",""))+"|"+msg["hex"]; mh=hashlib.sha256(ident.encode()).hexdigest()[:12]; fn=f"{int(msg['index']):03d}-{safe(msg.get('direction','msg'),3)}-{mh}.bin"; (fd/fn).write_bytes(raw)
   encoded,fmap=g.encode_sequence(seq["messages"]); cn=f"{i:03d}-{sh}.bin"; (d/"sequence.bin").write_bytes(encoded); (d/"sequence.hex").write_text(encoded.hex()+"\n",encoding="ascii"); (ad/cn).write_bytes(encoded)
   sm=dict(seq); sm["export"]={"sequence_encoding":g.SEQUENCE_ENCODING,"sequence_file":"sequence.bin","encoded_sha256":hashlib.sha256(encoded).hexdigest(),"encoded_bytes":len(encoded),"frames":fmap,"filesystem_naming":{"sequence_directory":sn,"corpus_file":cn,"policy":"short-hash-names-for-windows-path-safety"}}; (d/"sequence.json").write_text(json.dumps(sm,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); exported.append(sm)
  man=dict(lib); man["sequences"]=exported; man["export_metadata"]={"sequence_encoding":g.SEQUENCE_ENCODING,"filesystem_naming":"short-hash-names-for-windows-path-safety","note":"Full labels and seed identifiers remain in JSON. Short names prevent Windows path-length failures and do not alter bytes."}; (out/"manifest.json").write_text(json.dumps(man,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 g.export_library=export
def main():
 rec=load(P,"recovery_v1"); orig=rec.load_module
 def patched():
  g=orig(); install(g); return g
 rec.load_module=patched; rec.OUTPUT_ROOT=O; rec.main()
if __name__=="__main__": main()
