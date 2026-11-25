import tempfile, zipfile
from pathlib import Path
import streamlit as st
from engine import probe_video, detect_scenes, make_candidates, rank_candidates, render_clip, transcribe_local, ffmpeg_ready, download_youtube

st.set_page_config(page_title="ZENVIO AUTO CLIPPER",page_icon="🎬",layout="wide")
st.markdown("""<style>.stApp{background:#090b12;color:#f5f6fb}.hero{padding:22px;border:1px solid #292e42;border-radius:18px;background:linear-gradient(120deg,#17152d,#101827)}</style>""",unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>🎬 ZENVIO AUTO CLIPPER</h1>Local-first creator studio · YouTube import · Auto clips · Captions · 4K exports</div>',unsafe_allow_html=True)
st.caption("Use only videos you own or are authorized to edit. No paid AI API.")
if not ffmpeg_ready():
 st.error("FFmpeg/FFprobe not found in PATH."); st.stop()

if "workdir" not in st.session_state:
 st.session_state["workdir"]=tempfile.mkdtemp(prefix="zenvio_")
work=Path(st.session_state["workdir"])
with st.sidebar:
 canvas=st.selectbox("Canvas",["9:16 Vertical","1:1 Square","16:9 Landscape"])
 aspect={"9:16 Vertical":(9,16),"1:1 Square":(1,1),"16:9 Landscape":(16,9)}[canvas]
 resolution=st.selectbox("Resolution",["1080p","720p","4K"])
 target=st.slider("Clip length",15,90,35,5)
 sensitivity=st.slider("Scene sensitivity",0.5,5.0,2.0,0.5)

st.subheader("1. Import your video")
url=st.text_input("YouTube video link",placeholder="https://www.youtube.com/watch?v=...")
import_quality=st.selectbox("YouTube import quality",["Best available (recommended)","1080p maximum","720p maximum"],index=0)
quality_map={"Best available (recommended)":"Best available","1080p maximum":"1080p","720p maximum":"720p"}
st.caption("Best available original source is selected by default. 4K export cannot restore detail missing from the source.")
if st.button("⬇️ Import from YouTube",type="primary",disabled=not url.strip()):
 try:
  with st.spinner("YouTube video download ho rahi hai... Please wait."):
   st.session_state["source"]=download_youtube(url,str(work),quality_map[import_quality])
   st.session_state.pop("clips",None)
   st.session_state.pop("ranked_clips",None)
   st.session_state.pop("srt",None)
  st.success("YouTube video successfully import ho gayi!")
 except Exception as exc:
  st.error(f"YouTube import failed: {type(exc).__name__}: {repr(exc)}")

uploaded=st.file_uploader("Or upload a video from your computer",type=["mp4","mov","mkv","webm","m4v"])
if uploaded:
 src=work/("uploaded_source"+(Path(uploaded.name).suffix or ".mp4"))
 if not src.exists() or src.stat().st_size!=uploaded.size:
  src.write_bytes(uploaded.getbuffer())
  st.session_state["source"]=str(src)
  st.session_state.pop("clips",None)

source=st.session_state.get("source")
if source and Path(source).exists():
 src=Path(source)
 info=probe_video(str(src))
 x,y,z=st.columns(3); x.metric("Duration",f"{info['duration']:.1f}s"); y.metric("Size",f"{info['width']} × {info['height']}"); z.metric("FPS",f"{info['fps']:.2f}")
 st.video(str(src))
 t1,t2,t3=st.tabs(["✂️ Clip Studio","💬 Captions","📦 Export"])
 with t1:
  st.write("Scene-change clip suggestions (visual heuristic, not semantic viral detection).")
  if st.button("Analyze video + auto captions",type="primary"):
   with st.spinner("Scenes analyze ho rahe hain aur captions locally generate ho rahe hain..."):
    scene_points=detect_scenes(str(src),sensitivity)
    ranked=rank_candidates(info["duration"],scene_points,target,str(src))
    st.session_state["ranked_clips"]=ranked
    st.session_state["clips"]=[(x["start"],x["end"]) for x in ranked]
    st.session_state["source"]=str(src); st.session_state["work"]=str(work)
    if not st.session_state.get("srt"):
     try:
      txt=transcribe_local(str(src)); p=work/"auto_captions.srt"
      p.write_text(txt,encoding="utf-8"); st.session_state["srt"]=str(p)
      st.session_state["caption_status"]="Auto captions ready"
     except Exception as caption_error:
      st.session_state["caption_status"]=str(caption_error)
   st.success(f"Found and ranked {len(st.session_state['clips'])} segments.")
   if st.session_state.get("srt"): st.success("Automatic captions ready.")
   elif st.session_state.get("caption_status"): st.warning("Scene analysis ready; auto captions issue: "+st.session_state["caption_status"])
  selected=[]
  ranked=st.session_state.get("ranked_clips",[])
  for i,(a,b) in enumerate(st.session_state.get("clips",[])):
   score=ranked[i]["score"] if i<len(ranked) else 0
   reason=ranked[i]["reason"] if i<len(ranked) else ""
   if st.checkbox(f"Clip {i+1}: {a:.1f}s–{b:.1f}s · Potential {score}/99 · {reason}",True,key=f"c{i}"): selected.append((a,b))
  st.session_state["selected"]=selected
 with t2:
  st.write("Generate subtitles from the video's audio using the local Faster-Whisper model.")
  if st.button("🎙️ Generate captions now",type="primary"):
   try:
    with st.spinner("Speech recognition chal rahi hai. Pehli baar model download bhi ho sakta hai..."):
     txt=transcribe_local(str(src))
     if not txt.strip():
      raise RuntimeError("Audio se speech detect nahi hui. Video mein clear spoken audio check karein.")
     p=work/"auto_captions.srt"
     p.write_text(txt,encoding="utf-8")
     st.session_state["srt"]=str(p)
     st.session_state["caption_status"]="Auto captions ready"
    st.success("Captions generate ho gaye. Ab Export tab se render karein.")
   except Exception as exc:
    st.session_state["caption_status"]=f"{type(exc).__name__}: {exc}"
    st.error("Captions generate nahi hue: "+st.session_state["caption_status"])
  uploaded_srt=st.file_uploader("Upload SRT subtitle file",type=["srt"])
  if uploaded_srt:
   p=work/"captions.srt"; p.write_bytes(uploaded_srt.getbuffer()); st.session_state["srt"]=str(p)
   st.success("SRT loaded."); st.text_area("Preview",uploaded_srt.getvalue().decode("utf-8-sig",errors="replace")[:4000])
  if st.session_state.get("srt") and Path(st.session_state["srt"]).exists():
   st.success("Captions ready.")
   st.text_area("Caption preview",Path(st.session_state["srt"]).read_text(encoding="utf-8",errors="replace")[:4000],height=180)
  elif st.session_state.get("caption_status"):
   st.warning(st.session_state["caption_status"])
  if st.button("Retry automatic captions"):
   try:
    with st.spinner("Local speech recognition chal rahi hai..."):
     txt=transcribe_local(str(src)); p=work/"auto_captions.srt"; p.write_text(txt,encoding="utf-8"); st.session_state["srt"]=str(p)
    st.success("Captions generated.")
   except Exception as exc: st.error(str(exc))
  theme=st.selectbox("Theme",["Viral Yellow","Bold Creator","Cinematic","Neon Glow","Karaoke","Minimal White"])
  size=st.slider("Font size",24,80,48,2); pos=st.slider("Vertical position",5,30,15); outline=st.slider("Outline",0,8,3)
  st.session_state["style"]={"theme":theme,"font_size":size,"vertical_pos":pos,"outline":outline}
  sample={"Viral Yellow":"<span style='color:#ffe500;font-weight:900'>THIS IS THE MOMENT!</span>","Bold Creator":"<span style='color:white;font-weight:1000'>MAKE IT COUNT.</span>","Cinematic":"<span style='color:#f3e9d2'>A STORY IN EVERY FRAME</span>","Neon Glow":"<span style='color:#65f7ff;text-shadow:0 0 12px #00d9ff'>LEVEL UP</span>","Karaoke":"<span style='color:white;font-weight:900'>♪ WORD BY WORD ♪</span>","Minimal White":"<span style='color:white'>simple. clean. clear.</span>"}
  st.markdown("<div style='background:#171b27;padding:24px;text-align:center;font-size:28px;border-radius:12px'>"+sample[theme]+"</div>",unsafe_allow_html=True)
 with t3:
  st.write(f"Export: **{resolution} · {canvas} · 30 FPS · MP4**")
  default_folder=str(Path.home()/"Videos"/"ZENVIO_CLIPS")
  save_folder=st.text_input("Save exported clips to this folder",value=st.session_state.get("save_folder",default_folder))
  st.session_state["save_folder"]=save_folder
  if st.button("📁 Choose save folder"):
   try:
    import tkinter as tk
    from tkinter import filedialog
    root=tk.Tk(); root.withdraw(); root.attributes("-topmost",True)
    chosen=filedialog.askdirectory(title="Choose ZENVIO export folder",initialdir=str(Path(save_folder).expanduser()) if Path(save_folder).exists() else str(Path.home()))
    root.destroy()
    if chosen: st.session_state["save_folder"]=chosen; st.rerun()
   except Exception as exc: st.warning("Folder picker unavailable. Folder path box mein paste karein. "+str(exc))
  if st.button("Render selected clips",type="primary"):
   clips=st.session_state.get("selected",[])
   if not clips: st.warning("Analyze and select clips first.")
   else:
    outdir=Path(save_folder).expanduser()
    try: outdir.mkdir(parents=True,exist_ok=True)
    except Exception as exc: st.error(f"Save folder create nahi hua: {exc}"); st.stop()
    results=[]; bar=st.progress(0)
    for i,(a,b) in enumerate(clips):
     out=outdir/f"zenvio_clip_{i+1:02d}.mp4"
     render_clip(str(src),str(out),a,b,aspect,resolution,st.session_state.get("srt"),st.session_state.get("style",{}))
     results.append(out); bar.progress((i+1)/len(clips))
    archive=outdir/"ZENVIO_CLIPS.zip"
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as bundle:
     for p in results: bundle.write(p,p.name)
    st.success(f"Rendered {len(results)} clips. Saved in: {outdir}")
    for p in results: st.download_button("Download "+p.name,p.read_bytes(),file_name=p.name,mime="video/mp4",key=p.name)
    st.download_button("Download all (ZIP)",archive.read_bytes(),file_name=archive.name,mime="application/zip")
else:
 st.info("Paste a YouTube link or upload an MP4, MOV, MKV or WEBM video to begin.")
st.divider(); st.caption("ZENVIO · Local creator workflow")
