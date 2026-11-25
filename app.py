import tempfile, zipfile
from pathlib import Path
import streamlit as st
from engine import probe_video, detect_scenes, make_candidates, render_clip, transcribe_local, ffmpeg_ready

st.set_page_config(page_title="ZENVIO AUTO CLIPPER",page_icon="🎬",layout="wide")
st.markdown("""<style>.stApp{background:#090b12;color:#f5f6fb}.hero{padding:22px;border:1px solid #292e42;border-radius:18px;background:linear-gradient(120deg,#17152d,#101827)}</style>""",unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>🎬 ZENVIO AUTO CLIPPER</h1>Local-first creator studio · Auto clips · Captions · 4K exports</div>',unsafe_allow_html=True)
st.caption("Use only footage you own or are authorized to edit. No paid AI API.")
if not ffmpeg_ready():
 st.error("FFmpeg/FFprobe not found in PATH."); st.stop()
with st.sidebar:
 canvas=st.selectbox("Canvas",["9:16 Vertical","1:1 Square","16:9 Landscape"])
 aspect={"9:16 Vertical":(9,16),"1:1 Square":(1,1),"16:9 Landscape":(16,9)}[canvas]
 resolution=st.selectbox("Resolution",["1080p","720p","4K"])
 target=st.slider("Clip length",15,90,35,5)
 sensitivity=st.slider("Scene sensitivity",0.5,5.0,2.0,0.5)
video=st.file_uploader("Upload source video",type=["mp4","mov","mkv","webm","m4v"])
if video:
 work=Path(tempfile.mkdtemp(prefix="zenvio_")); src=work/("source"+(Path(video.name).suffix or ".mp4")); src.write_bytes(video.getbuffer())
 info=probe_video(str(src)); x,y,z=st.columns(3); x.metric("Duration",f"{info['duration']:.1f}s"); y.metric("Size",f"{info['width']} × {info['height']}"); z.metric("FPS",f"{info['fps']:.2f}")
 st.video(video)
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
  uploaded=st.file_uploader("Upload SRT subtitle file",type=["srt"])
  if uploaded:
   p=work/"captions.srt"; p.write_bytes(uploaded.getbuffer()); st.session_state["srt"]=str(p)
   st.success("SRT loaded."); st.text_area("Preview",uploaded.getvalue().decode("utf-8-sig",errors="replace")[:4000])
  if st.button("Generate captions locally (optional)"):
   try:
    with st.spinner("Transcribing locally..."):
     txt=transcribe_local(str(src)); p=work/"auto.srt"; p.write_text(txt,encoding="utf-8"); st.session_state["srt"]=str(p)
    st.success("Transcription complete."); st.text_area("Generated SRT",txt,height=200)
   except Exception as e: st.error(str(e))
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
else: st.info("Upload an MP4, MOV, MKV or WEBM video to begin.")
st.divider(); st.caption("ZENVIO · Local creator workflow")
