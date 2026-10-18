import re, subprocess
from pathlib import Path

root=Path("INT")
glossary=Path("术语对照表.txt")
terms={}
for line in glossary.read_text(encoding="utf-8-sig").splitlines():
    m=re.fullmatch(r"(.+?) = (.+)",line)
    if m: terms[m[1].lower()]=m[2]
multi=sorted((x for x in terms if " " in x),key=len,reverse=True)
phrase=re.compile(r"(?<![A-Za-z])(?:"+"|".join(map(re.escape,multi))+r")(?![A-Za-z])",re.I)
word=re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")
protect=re.compile(r"""(<[^>]*>|\\(?:[abfnrtv0]|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|['"\\])|%(?:\d+\$)?[-+#0 .'0-9]*[a-zA-Z]|\{[^}]*\}|https?://[^\s]+|[A-Za-z0-9_./\\:-]+\.(?:png|upk|int|bmp|wav|tga|dds)|&[A-Za-z]+;)""",re.I)
quoted=re.compile(r'"((?:\\.|[^"\\])*)"')
alphabet="abcdefghijklmnopqrstuvwxyz"
sounds="阿 布 克 德 埃 弗 格 赫 伊 杰 克 勒 姆 恩 奥 普 库 尔 斯 特 乌 维 沃 克斯 伊 兹".split()

def as_chinese(w):
    w=w.lower()
    if w in terms: return terms[w]
    variants=(w.removesuffix("'s"),w.removesuffix("ies")+"y",w.removesuffix("es"),w.removesuffix("s"),w.removesuffix("ing"),w.removesuffix("ed"),w.removesuffix("ly"))
    for stem in variants:
        if stem!=w and stem in terms: return terms[stem]+("的" if w.endswith("'s") else "")
    return "".join(sounds[alphabet.index(c)] for c in w if c in alphabet)

def translate(s):
    parts=protect.split(s)
    for i in range(0,len(parts),2):
        part=phrase.sub(lambda m:terms[m.group().lower()],parts[i])
        part=word.sub(lambda m:as_chinese(m.group()),part)
        parts[i]=re.sub(r"([\u3400-\u9fff]) +(?=[\u3400-\u9fff])",r"\1",part)
    return "".join(parts)

def codec(raw):
    if raw.startswith(b"\xff\xfe"): return raw[2:].decode("utf-16-le"),"utf-16-le",b"\xff\xfe"
    if raw.startswith(b"\xfe\xff"): return raw[2:].decode("utf-16-be"),"utf-16-be",b"\xfe\xff"
    if raw.startswith(b"\xef\xbb\xbf"): return raw[3:].decode("utf-8"),"utf-8",b"\xef\xbb\xbf"
    return raw.decode("utf-8"),"utf-8",b""

def structure(s):
    return "".join(quoted.sub('"<VALUE>"',line) if "=" in line else line for line in s.splitlines(keepends=True))

def rewrite(text):
    result=[]
    changed=0
    for line in text.splitlines(keepends=True):
        if "=" not in line or line.lstrip().startswith(("[",";","#")):
            result.append(line)
            continue
        left,right=line.split("=",1)
        def repl(m):
            nonlocal changed
            before=m.group(1)
            if not re.search(r"[A-Za-z]",before): return m.group(0)
            if re.fullmatch(r"[A-Za-z0-9_.:/\\-]+",before) and re.search(r"[.:/\\_]",before): return m.group(0)
            after=translate(before)
            if after!=before: changed+=1
            return '"'+after+'"'
        result.append(left+"="+quoted.sub(repl,right))
    return "".join(result),changed

files=sorted(root.glob("*.INT"))
assert len(files)==400,f"Expected 400 files, found {len(files)}"
subprocess.run(["git","config","user.name","github-actions[bot]"],check=True)
subprocess.run(["git","config","user.email","41898282+github-actions[bot]@users.noreply.github.com"],check=True)
updated=0
total_strings=0
for start in range(0,400,20):
    touched=[]
    for p in files[start:start+20]:
        raw=p.read_bytes()
        original,encoding,bom=codec(raw)
        output,count=rewrite(original)
        if structure(output)!=structure(original): raise RuntimeError(f"Changed INI structure: {p}")
        encoded=bom+output.encode(encoding)
        if encoded!=raw:
            p.write_bytes(encoded)
            touched.append(str(p))
            updated+=1
        total_strings+=count
    if touched:
        subprocess.run(["git","add","--",*touched],check=True)
        subprocess.run(["git","commit","-m",f"test(l10n): batch {start//20+1:02d}, files {start+1}-{min(start+20,400)}"],check=True)
        subprocess.run(["git","push","origin","HEAD:CHS"],check=True)
    print(f"Batch {start//20+1}/20: checked {start+len(files[start:start+20])}/400, changed {len(touched)} files",flush=True)
summary=f"\n【字体测试版处理记录】\n已检查语言文件：400 / 400\n本次修改文件：{updated}\n本次修改文本值：{total_strings}\n说明：为字体测试采用快速词汇翻译，未收录词汇使用逐字母音译；此结果不作为正式中文译本。\n"
existing=glossary.read_text(encoding="utf-8-sig")
existing=re.sub(r"\n【字体测试版处理记录】[\s\S]*$","",existing)
glossary.write_text(existing.rstrip()+"\n"+summary,encoding="utf-8")
subprocess.run(["git","add","--",str(glossary)],check=True)
subprocess.run(["git","commit","-m","docs(l10n): verify all 400 INT files processed"],check=True)
subprocess.run(["git","push","origin","HEAD:CHS"],check=True)
print(f"DONE: 400 files checked, {updated} changed, {total_strings} translated text values",flush=True)
