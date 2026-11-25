import tempfile, zipfile
from pathlib import Path
import streamlit as st
from engine import probe_video, detect_scenes, make_candidates, render_clip, transcribe_local, ffmpeg_ready, download_youtube

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
import_quality=st.selectbox("YouTube import quality",["480p · Fast","720p · Balanced","1080p · High quality"],index=1)
quality_map={"480p · Fast":"480p","720p · Balanced":"720p","1080p · High quality":"1080p"}
st.caption("Fast import downloads a lower-resolution source. 4K export can upscale it; it does not restore original 4K detail.")
if st.button("⬇️ Import from YouTube",type="primary",disabled=not url.strip()):
 progress=st.progress(0)
 progress_text=st.empty()
 progress_text.info("YouTube se connect ho rahe hain...")
 def update_download_progress(data):
  status=data.get("status")
  if status=="downloading":
   downloaded=data.get("downloaded_bytes",0) or 0
   total=data.get("total_bytes") or data.get("total_bytes_estimate") or 0
   if total:
    pct=max(0,min(99,int(downloaded*100/total)))
    progress.progress(pct)
    amount=f"{downloaded/1048576:.1f} / {total/1048576:.1f} MB"
   else:
    pct=0
    amount=f"{downloaded/1048576:.1f} MB downloaded"
   speed=data.get("speed")
   eta=data.get("eta")
   speed_text=f"{speed/1048576:.2f} MB/s" if speed else "calculating speed..."
   eta_text=f" · ETA {int(eta)}s" if eta is not None else ""
   progress_text.info(f"Downloading: {pct}% · {amount} · {speed_text}{eta_text}")
  elif status=="finished":
   progress.progress(100)
   progress_text.info("Download complete. Video file finalize ho rahi hai...")
 try:
  with st.spinner("Import process chal raha hai..."):
   st.session_state["source"]=download_youtube(url,str(work),quality_map[import_quality],update_download_progress)
   st.session_state.pop("clips",None)
  progress.progress(100)
  progress_text.success("YouTube video successfully import ho gayi!")
 except Exception as exc:
  progress_text.empty()
  st.error(str(exc))

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
  if st.button("Analyze video",type="primary"):
   with st.spinner("Analyzing scenes..."):
    st.session_state["clips"]=make_candidates(info["duration"],detect_scenes(str(src),sensitivity),target)
    st.session_state["source"]=str(src); st.session_state["work"]=str(work)
   st.success(f"Found {len(st.session_state['clips'])} segments.")
  selected=[]
  for i,(a,b) in enumerate(st.session_state.get("clips",[])):
   if st.checkbox(f"Clip {i+1}: {a:.1f}s–{b:.1f}s",True,key=f"c{i}"): selected.append((a,b))
  st.session_state["selected"]=selected
 with t2:
  uploaded_srt=st.file_uploader("Upload SRT subtitle file",type=["srt"])
  if uploaded_srt:
   p=work/"captions.srt"; p.write_bytes(uploaded_srt.getbuffer()); st.session_state["srt"]=str(p)
   st.success("SRT loaded."); st.text_area("Preview",uploaded_srt.getvalue().decode("utf-8-sig",errors="replace")[:4000])
  if st.button("Generate captions locally (optional)"):
   try:
    with st.spinner("Transcribing locally..."):
     txt=transcribe_local(str(src)); p=work/"auto.srt"; p.write_text(txt,encoding="utf-8"); st.session_state["srt"]=str(p)
    st.success("Transcription complete."); st.text_area("Generated SRT",txt,height=200)
   except Exception as exc: st.error(str(exc))
  theme=st.selectbox("Theme",["Viral Yellow","Bold Creator","Cinematic","Neon Glow","Karaoke","Minimal White"])
  size=st.slider("Font size",24,80,48,2); pos=st.slider("Vertical position",5,30,15); outline=st.slider("Outline",0,8,3)
  st.session_state["style"]={"theme":theme,"font_size":size,"vertical_pos":pos,"outline":outline}
  sample={"Viral Yellow":"<span style='color:#ffe500;font-weight:900'>THIS IS THE MOMENT!</span>","Bold Creator":"<span style='color:white;font-weight:1000'>MAKE IT COUNT.</span>","Cinematic":"<span style='color:#f3e9d2'>A STORY IN EVERY FRAME</span>","Neon Glow":"<span style='color:#65f7ff;text-shadow:0 0 12px #00d9ff'>LEVEL UP</span>","Karaoke":"<span style='color:white;font-weight:900'>♪ WORD BY WORD ♪</span>","Minimal White":"<span style='color:white'>simple. clean. clear.</span>"}
  st.markdown("<div style='background:#171b27;padding:24px;text-align:center;font-size:28px;border-radius:12px'>"+sample[theme]+"</div>",unsafe_allow_html=True)
 with t3:
  st.write(f"Export: **{resolution} · {canvas} · MP4**")
  if st.button("Render selected clips",type="primary"):
   clips=st.session_state.get("selected",[])
   if not clips: st.warning("Analyze and select clips first.")
   else:
    outdir=work/"exports"; outdir.mkdir(exist_ok=True); results=[]; bar=st.progress(0)
    for i,(a,b) in enumerate(clips):
     out=outdir/f"zenvio_clip_{i+1:02d}.mp4"
     render_clip(str(src),str(out),a,b,aspect,resolution,st.session_state.get("srt"),st.session_state.get("style",{}))
     results.append(out); bar.progress((i+1)/len(clips))
    archive=work/"ZENVIO_CLIPS.zip"
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as bundle:
     for p in results: bundle.write(p,p.name)
    st.success(f"Rendered {len(results)} clips.")
    for p in results: st.download_button("Download "+p.name,p.read_bytes(),file_name=p.name,mime="video/mp4",key=p.name)
    st.download_button("Download all (ZIP)",archive.read_bytes(),file_name=archive.name,mime="application/zip")
else:
 st.info("Paste a YouTube link or upload an MP4, MOV, MKV or WEBM video to begin.")
st.divider(); st.caption("ZENVIO · Local creator workflow")
