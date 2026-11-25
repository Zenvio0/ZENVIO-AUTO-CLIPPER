import json,re,shutil,subprocess
from pathlib import Path

THEMES={
"Viral Yellow":("Arial","&H0000E5FF","&H00000000",-1),
"Bold Creator":("Arial Black","&H00FFFFFF","&H00000000",-1),
"Cinematic":("Georgia","&H00D2E9F3","&H00101010",0),
"Neon Glow":("Arial","&H00FFF765","&H00A00070",-1),
"Karaoke":("Arial","&H00FFFFFF","&H00000000",-1),
"Minimal White":("Arial","&H00FFFFFF","&H00000000",0)}

def run(cmd):
 p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 if p.returncode: raise RuntimeError((p.stderr or p.stdout)[-3000:])
 return p.stdout

def ffmpeg_ready():
 return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

def download_youtube(url,output_dir,quality="720p",progress_hook=None):
 try:
  import yt_dlp
 except Exception as exc:
  raise RuntimeError("YouTube import ke liye yt-dlp install nahi hai. Run: J:\\python.exe -m pip install -U yt-dlp") from exc
 url=url.strip()
 if not re.match(r"^https?://(www\.)?(youtube\.com|youtu\.be)/",url,re.I):
  raise ValueError("Please valid YouTube video URL paste karein.")
 limits={"480p":480,"720p":720,"1080p":1080}
 if quality not in limits: quality="720p"
 max_height=limits[quality]
 folder=Path(output_dir); folder.mkdir(parents=True,exist_ok=True)
 opts={
  "format":f"best[height<={max_height}][ext=mp4]/best[height<={max_height}]/best",
  "outtmpl":str(folder/"source_%(id)s.%(ext)s"),
  "noplaylist":True,
  "quiet":True,
  "no_warnings":True,
  "overwrites":True,
  "continuedl":True,
  "socket_timeout":20,
  "retries":2,
  "fragment_retries":2,
  "extractor_retries":2,
  "file_access_retries":2,
  "concurrent_fragment_downloads":4,
  "progress_hooks":[progress_hook] if progress_hook else []
 }
 try:
  with yt_dlp.YoutubeDL(opts) as ydl:
   info=ydl.extract_info(url,download=True)
   prepared=Path(ydl.prepare_filename(info))
  candidates=[prepared]
  if info.get("requested_downloads"):
   candidates += [Path(x["filepath"]) for x in info["requested_downloads"] if x.get("filepath")]
  candidates += sorted(folder.glob("source_*.*"),key=lambda p:p.stat().st_mtime,reverse=True)
  for candidate in candidates:
   if candidate.exists() and candidate.is_file() and candidate.stat().st_size>0 and candidate.suffix.lower() not in (".part",".ytdl"):
    return str(candidate)
  raise RuntimeError("Download complete hua lekin output video file nahi mili.")
 except Exception as exc:
  raise RuntimeError(f"YouTube import failed: {exc}") from exc

def probe_video(path):
 data=json.loads(run(["ffprobe","-v","error","-show_entries","format=duration:stream=width,height,r_frame_rate","-of","json",path]))
 v=next(s for s in data["streams"] if "width" in s); n,d=v.get("r_frame_rate","30/1").split("/")
 return {"duration":float(data["format"]["duration"]),"width":int(v["width"]),"height":int(v["height"]),"fps":float(n)/max(float(d),1)}

def detect_scenes(path,sensitivity=2.0):
 threshold=max(.05,min(.95,sensitivity/10))
 raw=run(["ffmpeg","-hide_banner","-i",path,"-vf",f"select='gt(scene,{threshold})',showinfo","-an","-f","null","-"])
 return sorted(set(float(x) for x in re.findall(r"pts_time:([0-9.]+)",raw)))

def make_candidates(duration,scenes,target):
 points=[0.0]+[x for x in scenes if 2<x<duration-2]+[duration]; result=[]
 for start in points[:-1]:
  end=min(duration,start+target)
  if end-start>=min(10,target*.55): result.append((round(start,2),round(end,2)))
 if len(result)<3 and duration>target*1.5:
  result=[]; t=0; step=max(8,target*.65)
  while t<duration-5:
   result.append((round(t,2),round(min(duration,t+target),2))); t+=step
 return result[:30] or [(0.0,round(min(duration,target),2))]

def parse_srt(path):
 blocks=re.split(r"\n\s*\n",Path(path).read_text(encoding="utf-8-sig",errors="replace").strip()); rows=[]
 def seconds(t):
  h,m,s=t.replace(",",".").split(":"); return int(h)*3600+int(m)*60+float(s)
 for block in blocks:
  lines=block.strip().splitlines(); timing=next((x for x in lines if "-->" in x),None)
  if not timing: continue
  a,b=[x.strip().split()[0] for x in timing.split("-->")]
  txt=" ".join(x.strip() for x in lines[lines.index(timing)+1:] if x.strip())
  rows.append((seconds(a),seconds(b),txt))
 return rows

def ass_time(t):
 h=int(t//3600); m=int((t%3600)//60); return f"{h}:{m:02d}:{t%60:05.2f}"

def write_ass(srt_path,ass_path,style,start,end):
 font,primary,outline_color,bold=THEMES.get(style.get("theme"),THEMES["Viral Yellow"])
 size=int(style.get("font_size",48)); outline=int(style.get("outline",3)); margin=int(style.get("vertical_pos",15))*10
 header=f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{primary},&H0000FFFF,{outline_color},&H80000000,{bold},0,0,0,100,100,0,0,1,{outline},1,2,55,55,{margin},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
 events=[]
 for a,b,txt in parse_srt(srt_path):
  a=max(a,start); b=min(b,end)
  if b<=a: continue
  if style.get("theme")=="Karaoke":
   words=txt.split(); each=max(1,int((b-a)*100/max(1,len(words))))
   txt=" ".join("{\\k"+str(each)+"}"+w for w in words)
  txt=txt.replace("{","(").replace("}",")").replace("\n"," ")
  events.append(f"Dialogue: 0,{ass_time(a-start)},{ass_time(b-start)},Default,,0,0,0,,{txt}")
 Path(ass_path).write_text(header+"\n".join(events)+"\n",encoding="utf-8")

def transcribe_local(path):
 try:
  from faster_whisper import WhisperModel
 except Exception as exc:
  raise RuntimeError("Optional local transcription requires faster-whisper. Python 3.11/3.12 is recommended; install with pip install faster-whisper.") from exc
 model=WhisperModel("base",device="cpu",compute_type="int8")
 segments,_=model.transcribe(path,word_timestamps=True)
 def stamp(t):
  ms=int(round(t*1000)); h=ms//3600000; m=(ms%3600000)//60000; s=(ms%60000)//1000; ms%=1000
  return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
 out=[]; idx=1
 for seg in segments:
  parts=seg.words if seg.words else [seg]
  for word in parts:
   text=word.word.strip() if seg.words else word.text.strip()
   out.extend([str(idx),f"{stamp(word.start)} --> {stamp(word.end)}",text,""]); idx+=1
 return "\n".join(out)

def render_clip(source,output,start,end,aspect,resolution,srt_path=None,style=None):
 sizes={
 (9,16):{"4K":(2160,3840),"1080p":(1080,1920),"720p":(720,1280)},
 (1,1):{"4K":(2160,2160),"1080p":(1080,1080),"720p":(720,720)},
 (16,9):{"4K":(3840,2160),"1080p":(1920,1080),"720p":(1280,720)}}
 width,height=sizes[aspect][resolution]
 filters=f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1"
 ass_path=None
 if srt_path:
  ass_path=str(Path(output).with_suffix(".ass")); write_ass(srt_path,ass_path,style or {},start,end)
  escaped=ass_path.replace("\\","/").replace(":","\\:")
  filters+=f",ass='{escaped}'"
 run(["ffmpeg","-y","-ss",str(start),"-i",source,"-t",str(end-start),"-vf",filters,"-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-movflags","+faststart",output])
 if ass_path and Path(ass_path).exists(): Path(ass_path).unlink()
 return output
