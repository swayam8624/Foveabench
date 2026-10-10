"""FB-VISUAL-01: replay *captured* Vulkan compute frames in a local HTML viewer.

The experience is an offline playback of the actual headless Vulkan output,
not a live headset renderer, Vulkan raster VRS, physical GPU acceleration,
or a human-calibrated perceptual benchmark. No network dependencies or browser
packages are needed. The local standalone HTML can open via file://.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import struct
import webbrowser
import zlib
from datetime import datetime, timezone
from pathlib import Path
from tqdm.auto import tqdm

from . import phase2

POLICIES = ("full", "fixed", "tracked", "tracked_lag40")
SCENES = ("chirp", "edges")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for block in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)


def ppm_to_png(raw: bytes) -> bytes:
    """Strict converter for our own P6 output, no PIL/image libraries required."""
    found = re.match(rb"P6\s+(\d+)\s+(\d+)\s+255\s", raw)
    if found is None:
        raise ValueError("Expected FoveaBench binary P6 RGB image")
    width, height = map(int, found.groups())
    if not 1 <= width <= 4096 or not 1 <= height <= 4096:
        raise ValueError("Unreasonable PPM frame dimensions")
    pixels = raw[found.end():]
    if len(pixels) != width * height * 3:
        raise ValueError("PPM pixel payload has wrong byte count")
    stride = width * 3
    scanlines = b"".join(b"\0" + pixels[y*stride:(y+1)*stride] for y in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return PNG_SIGNATURE + png_chunk(b"IHDR", ihdr) + png_chunk(b"IDAT", zlib.compress(scanlines, 6)) + png_chunk(b"IEND", b"")


def demo_trace(path: Path, frames: int, hz: int, motion: str, delay_ms: float):
    """Synthetic image-space trace. The predictor's 'used' gaze is past-held."""
    if motion not in ("pursuit", "jump", "hybrid", "fixation"):
        raise ValueError("Invalid motion")
    if not 8 <= frames <= 1000 or not 1 <= hz <= 500 or not 0 <= delay_ms <= 300:
        raise ValueError("Invalid showcase timing settings")
    phase2.non_overwrite(path)
    truth = []
    for i in range(frames):
        t = i / hz
        if motion == "fixation":
            x, y = .68 + .003 * math.sin(t*4), .45
        elif motion == "pursuit":
            x, y = .50 + .32 * math.sin(t*3.8), .50 + .18 * math.cos(t*2)
        elif motion == "jump":
            x, y = ((.25, .30) if (i//max(5,int(hz*.30)))%2==0 else (.77, .68))
        else:
            x, y = .5 + .22*math.sin(t*3.8), .50 + .12*math.cos(t*2.4)
            if (i//max(5,int(hz*.42)))%2: x = .80 - .15*math.sin(t*3.8)
        truth.append((min(1,max(0,x)),min(1,max(0,y))))
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="") as fp:
        writer=csv.writer(fp)
        writer.writerow(phase2.REQUIRED)
        for i, (x,y) in enumerate(truth):
            index=max(0,math.floor(i-delay_ms*hz/1000))
            px,py=truth[index]
            writer.writerow((round(i*1e9/hz),x,y,px,py,1))
    return path


def _read_metrics(run:Path):
    data = {scene: {policy: [] for policy in POLICIES} for scene in SCENES}
    with (run/"frames.csv").open(newline="") as fp:
        for row in csv.DictReader(fp):
            scene=row["scene"];policy=row["policy"]
            if scene not in data or policy not in data[scene]:
                raise ValueError("Unknown native render scene/policy")
            data[scene][policy].append({
                "index":int(row["frame_index"]),
                "time_ns":int(row["timestamp_ns"]),
                "truth":[float(row["truth_x"]),float(row["truth_y"])],
                "used":[float(row["used_x"]),float(row["used_y"])],
                "mse":float(row["weighted_mse"]),
                "foveal_mse":float(row["foveal_mse"]),
                "sample_proxy":float(row["sample_fraction_proxy"]),
                "dispatch_ms":None if not row["device_dispatch_ms"] else float(row["device_dispatch_ms"]),
            })
    counts={len(data[scene][policy]) for scene in SCENES for policy in POLICIES}
    if len(counts)!=1 or next(iter(counts))<2:
        raise ValueError("Missing or mismatched recorded policy frames")
    n=next(iter(counts))
    for scene in SCENES:
        for policy in POLICIES:
            if [p["index"] for p in data[scene][policy]]!=list(range(n)):
                raise ValueError("Nonconsecutive frame sequence")
    return data,n


def generate_viewer(run: Path):
    """Generate a self-contained local webpage plus captured native PNG images."""
    native=run/"native"
    manifest=json.loads((native/"manifest.json").read_text())
    if manifest.get("suite")!="FB-RENDER-01/2.0":
        raise ValueError("Expected real Vulkan backend manifest")
    if manifest.get("full_reference_pixel_mismatch_max")!=0:
        raise ValueError("Native full-render reference invariant failed")
    if manifest.get("capture_every")!=1:
        raise ValueError("Full recorded replay requires --capture-every 1")
    dataset,frames=_read_metrics(native)
    images=run/"viewer"/"assets"
    images.mkdir(parents=True,exist_ok=False)
    print("[IMAGES] Converting native Vulkan PPM captures to browser PNG...",flush=True)
    tasks=[(scene,policy,i) for scene in SCENES for policy in POLICIES for i in range(frames)]
    for scene,policy,i in tqdm(tasks,desc="Native Vulkan frames -> PNG",unit="frame",dynamic_ncols=True):
        source=native/"frames"/(f"{scene}_{policy}_{i}.ppm")
        if not source.is_file():raise FileNotFoundError(f"Missing actual Vulkan frame: {source}")
        (images/f"{scene}_{policy}_{i}.png").write_bytes(ppm_to_png(source.read_bytes()))
    viewer_meta={
        "suite":"FB-VISUAL-01/1.0","source_suite":manifest["suite"],
        "device":manifest["device_name"],"result_class":manifest["results_class"],
        "resolution":manifest["resolution"],"frames":frames,
        "total_dispatches":manifest["frame_policy_evaluations"],
        "timestamp_available":manifest.get("timestamp_query_available",False),
        "hardware_vrs":manifest.get("actual_hardware_vrs",False),
        "hardware_score_eligible":manifest.get("hardware_score_eligible",False),
        "trace_sha256":sha256(run/"trace.csv"),
        "native_frames_sha256":sha256(native/"frames.csv"),
        "captured_images":len(tasks),"created_utc":datetime.now(timezone.utc).isoformat(),
        "scientific_status":"Offline replay of real headless Vulkan compute captures. Not live XR, true VRS, or physical-GPU benchmark.",
    }
    (run/"viewer"/"manifest.json").write_text(json.dumps(viewer_meta,indent=2)+"\n")
    html=VIEWER_HTML.replace("__FRAME_DATA__",json.dumps({"meta":viewer_meta,"metrics":dataset},separators=(",",":")))
    (run/"viewer"/"index.html").write_text(html,encoding="utf-8")
    (run/"report.md").write_text("# FB-VISUAL-01 native Vulkan visual replay\n\n"
        f"- Vulkan device: **{viewer_meta['device']}** ({viewer_meta['result_class']}).\n"
        f"- Native Vulkan dispatches: **{viewer_meta['total_dispatches']}**.\n"
        f"- Captured image frames: **{len(tasks)}** (two scenes × four policies × {frames} frames).\n"
        "- Full-reference pixel correctness: **PASS**.\n"
        "- No actual fragment VRS, live headset tracking, or human perceptual validation.\n"
        "- Vulkan software CPU device timings cannot be claimed as physical GPU performance.\n"
        "- Browser playback is offline visualization of recorded frames, not the graphics pipeline itself.\n"
        "- To watch, open `viewer/index.html` using Firefox/Chromium in the VM.\n")
    print(f"[VIEWER] Rendered {len(tasks)} real native frame images; open {(run/'viewer'/'index.html').resolve()}",flush=True)
    return viewer_meta


def run(args):
    if args.output.exists():raise FileExistsError("Refusing to overwrite previous benchmark evidence")
    if args.frames<8 or args.frames>600 or args.width<32 or args.height<32 or args.width>1024 or args.height>1024:
        raise ValueError("Showcase accepts 8..600 frames and resolutions 32..1024")
    args.output.mkdir(parents=True)
    trace=args.output/"trace.csv"
    if args.trace:
        if not args.trace.is_file():raise FileNotFoundError(args.trace)
        shutil.copyfile(args.trace,trace)
        print("[GAZE] Using supplied canonical gaze trace, unmodified",flush=True)
    else:
        demo_trace(trace,args.frames,args.hz,args.motion,args.delay_ms)
        print(f"[GAZE] Synthetic motion={args.motion} latency={args.delay_ms}ms frames={args.frames}",flush=True)
    repo=Path(__file__).resolve().parent.parent
    print(f"[VULKAN] Compiling/dispatching native C++ and SPIR-V at {args.width}x{args.height}; "
          "native images, NOT browser-only simulation",flush=True)
    phase2.run_native(repo,args.output/"native",trace,frames=args.frames,
                      width=args.width,height=args.height,capture_every=1)
    meta=generate_viewer(args.output)
    print(f"[DONE] {meta['total_dispatches']} genuine Vulkan compute dispatches; "
          f"viewer={(args.output/'viewer'/'index.html').resolve()}",flush=True)
    if args.open:
        opened=webbrowser.open((args.output/"viewer"/"index.html").resolve().as_uri())
        print(f"[BROWSER] Launch requested; open manually if unavailable (desktop returned {opened})",flush=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest="action",required=True)
    p=sub.add_parser("run",help="Run Vulkan scene captures then generate autoplay visual HTML")
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--trace",type=Path,help="Optional existing canonical timestamped gaze trace")
    p.add_argument("--frames",type=int,default=72)
    p.add_argument("--width",type=int,default=256)
    p.add_argument("--height",type=int,default=144)
    p.add_argument("--hz",type=int,default=90)
    p.add_argument("--motion",choices=("fixation","pursuit","jump","hybrid"),default="hybrid")
    p.add_argument("--delay-ms",type=float,default=60.0)
    p.add_argument("--open",action="store_true",help="Ask the desktop browser to open the generated replay")
    args=ap.parse_args()
    run(args)


VIEWER_HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>FoveaBench // Vulkan visual benchmark</title><style>
:root{color-scheme:dark;--bg:#070b12;--panel:#111927;--line:#273850;--ink:#e7f1fb;--mute:#99aac0;--cyan:#40d7ff;--amber:#ffd073;--violet:#a78bfa;--green:#7ef2b3}
*{box-sizing:border-box}body{background:radial-gradient(circle at 20% 2%,#183252 0,#080e18 32%,#070b12 70%);color:var(--ink);font:14px/1.5 ui-sans-serif,system-ui,Segoe UI,Arial;margin:0;min-height:100vh}
main{max-width:1540px;margin:0 auto;padding:26px}header{display:flex;flex-wrap:wrap;gap:15px;justify-content:space-between;align-items:start;margin-bottom:20px}.eyebrow{font-size:11px;letter-spacing:2.8px;color:var(--cyan);text-transform:uppercase;font-weight:700}
h1{font-size:clamp(24px,3vw,38px);margin:4px 0 0;font-weight:800;letter-spacing:-1.5px}h1 em{color:var(--cyan);font-style:normal}p{color:var(--mute);margin:5px 0 0}.pill{border:1px solid #2b5266;padding:8px 11px;border-radius:999px;color:var(--cyan);font-size:11px;font-weight:700;background:#102431}
.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:18px 0}.stat,.controls,.plotbox,.framepanel,.methods{background:linear-gradient(150deg,#132136dd,#101827f3);border:1px solid var(--line);border-radius:13px;box-shadow:0 10px 35px #0003}.stat{padding:12px 15px}.stat b{display:block;color:var(--mute);font-size:11px;text-transform:uppercase;letter-spacing:1px}.stat strong{font-variant-numeric:tabular-nums;font-size:24px;letter-spacing:-.6px}.stat small{display:block;color:var(--mute);font-size:11px}.controls{padding:14px 18px;display:flex;align-items:center;flex-wrap:wrap;gap:16px;margin-bottom:16px}label{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--mute)}select,button,input{accent-color:var(--cyan)}select,button{background:#182943;color:var(--ink);border:1px solid #34516f;border-radius:7px;padding:8px 12px;font:inherit;cursor:pointer}button:hover{border-color:var(--cyan)}input[type=range]{min-width:190px;flex:1;cursor:pointer}.control{display:flex;align-items:center;gap:9px}.film{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.framepanel{padding:12px;position:relative;min-width:0}.framepanel .head{display:flex;justify-content:space-between;margin:0 0 8px;font-size:12px}.head b{letter-spacing:.7px}.head span{color:var(--mute);font-variant-numeric:tabular-nums}.framepanel canvas{display:block;width:100%;aspect-ratio:16/9;background:#05080d;border-radius:6px;image-rendering:pixelated}.legend{color:var(--mute);font-size:11px;margin:7px 0 0;display:flex;gap:15px}.legend i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}.lower{display:grid;grid-template-columns:2fr 1fr;gap:15px;margin-top:15px}.plotbox{padding:14px;min-width:0}.plotbox canvas{width:100%;height:155px;display:block}.methods{padding:16px;font-size:12px;color:var(--mute)}.methods strong{color:var(--ink)}footer{font-size:11px;color:var(--mute);padding:18px 0}.warn{color:var(--amber);font-weight:600}
@media(max-width:850px){.metrics{grid-template-columns:repeat(2,1fr)}.film,.lower{grid-template-columns:1fr}.control{flex:1}.framepanel canvas{max-height:300px}}
</style></head><body><main>
<header><div><div class="eyebrow">FoveaBench / reproducible XR research</div><h1>Visual <em>Vulkan</em> Benchmark</h1><p>Actual offscreen compute captures · replayed frame by frame · gaze-conditioned image quality</p></div><div><span class="pill" id="deviceClass">LOADING</span><p id="device" style="text-align:right"></p></div></header>
<section class="metrics"><div class="stat"><b>Native dispatches</b><strong id="dispatches">–</strong><small>Measured Vulkan operations</small></div><div class="stat"><b>Frame replay</b><strong id="frameCounter">–</strong><small>Captured native images</small></div><div class="stat"><b>Tracked weighted MSE</b><strong id="wMse">–</strong><small>Lower is better; uncalibrated proxy</small></div><div class="stat"><b>Sampling demand proxy</b><strong id="proxy">–</strong><small>Not counted shader invocations</small></div></section>
<section class="controls"><div class="control"><label for="scene">Scene</label><select id="scene"><option value="chirp">Chirp / spatial frequency</option><option value="edges">Edges / checker detail</option></select></div><button id="play">▶ Play replay</button><div class="control"><label for="speed">Playback</label><select id="speed"><option value="0.5">0.5×</option><option value="1" selected>1×</option><option value="2">2×</option><option value="4">4×</option></select></div><input id="frameSlider" aria-label="Select recorded Vulkan frame" type="range" min="0" max="71" value="0"><strong id="position">0 / 71</strong></section>
<section class="film"><div class="framepanel"><div class="head"><b>REFERENCE / FULL QUALITY</b><span id="fullmeta">100% proxy</span></div><canvas id="cfull" width="256" height="144"></canvas></div><div class="framepanel"><div class="head"><b>FIXED CENTER FOVEATION</b><span id="fixedmeta">–</span></div><canvas id="cfixed" width="256" height="144"></canvas></div><div class="framepanel"><div class="head"><b>TRACKED GAZE FOVEATION</b><span id="trackedmeta">–</span></div><canvas id="ctracked" width="256" height="144"></canvas></div><div class="framepanel"><div class="head"><b>40 ms LAG + TRACKING</b><span id="lagmeta">–</span></div><canvas id="clag" width="256" height="144"></canvas></div></section>
<div class="legend"><span><i style="background:var(--cyan)"></i> True synthetic gaze</span><span><i style="background:var(--amber)"></i> Gaze used by policy</span><span>Ring = illustration of gaze location, not calibrated retinal size</span></div>
<section class="lower"><div class="plotbox"><div class="eyebrow">Frame-by-frame tracked error</div><canvas id="chart" width="960" height="155"></canvas></div><aside class="methods"><strong>Measurement and interpretation</strong><p id="methodData"></p><p class="warn">This is recorded headless Vulkan compute output, not a live GPU stress test or a VR headset. Every pixel dispatches; no actual hardware VRS is performed.</p><p>Shader timings are Vulkan query values and may reflect CPU software-driver execution. Image-error proxies are not human opinion scores.</p></aside></section>
<footer>FB-VISUAL-01 · Self-contained local playback · No cloud calls · Reproducible captures, hashes and manifests stored beside this page.</footer>
</main><script>
'use strict';
const model=__FRAME_DATA__;
const meta=model.meta, metrics=model.metrics;
const sceneEl=document.getElementById('scene'),slider=document.getElementById('frameSlider');
const playBtn=document.getElementById('play'), speedEl=document.getElementById('speed');
const mapping=[['full','cfull','fullmeta'],['fixed','cfixed','fixedmeta'],['tracked','ctracked','trackedmeta'],['tracked_lag40','clag','lagmeta']];
let frame=0, playing=false,lastTick=0, accumulator=0;
const cache=new Map();
function imageFor(scene,policy,i){const url='assets/'+scene+'_'+policy+'_'+i+'.png';if(!cache.has(url)){const im=new Image();im.src=url;cache.set(url,im);if(cache.size>75){const first=cache.keys().next().value;cache.delete(first)}}return cache.get(url)}
function marker(ctx,x,y,color,w,h){if(x===undefined)return;const px=x*w,py=y*h;ctx.strokeStyle=color;ctx.lineWidth=Math.max(1.4,w/160);ctx.beginPath();ctx.arc(px,py,w*.047,0,2*Math.PI);ctx.stroke();ctx.beginPath();ctx.moveTo(px-w*.013,py);ctx.lineTo(px+w*.013,py);ctx.moveTo(px,py-w*.013);ctx.lineTo(px,py+w*.013);ctx.stroke()}
function drawPolicy(scene,policy,canvasId,labelId){const rec=metrics[scene][policy][frame];const el=document.getElementById(canvasId),ctx=el.getContext('2d');const w=meta.resolution[0],h=meta.resolution[1];if(el.width!==w||el.height!==h){el.width=w;el.height=h}const img=imageFor(scene,policy,frame);if(img.complete && img.naturalWidth){ctx.drawImage(img,0,0,w,h)}else{ctx.fillStyle='#05070c';ctx.fillRect(0,0,w,h);img.onload=()=>{if(frame===rec.index)drawPolicy(scene,policy,canvasId,labelId)}}marker(ctx,rec.truth[0],rec.truth[1],'#40d7ff',w,h);if(policy!=='full'&&(Math.abs(rec.truth[0]-rec.used[0])+Math.abs(rec.truth[1]-rec.used[1])>0.0003)){marker(ctx,rec.used[0],rec.used[1],'#ffd073',w,h)}document.getElementById(labelId).textContent= 'MSE '+rec.mse.toFixed(1)+' · proxy '+(100*rec.sample_proxy).toFixed(1)+'%'}
function chart(){const canvas=document.getElementById('chart'),ctx=canvas.getContext('2d');const w=canvas.width,h=canvas.height;ctx.clearRect(0,0,w,h);ctx.fillStyle='#0c1623';ctx.fillRect(0,0,w,h);const scene=sceneEl.value;const a=metrics[scene].tracked,b=metrics[scene].fixed,c=metrics[scene].tracked_lag40;const max=Math.max(1,...a.map(r=>r.mse),...b.map(r=>r.mse),...c.map(r=>r.mse))*1.06;for(let k=1;k<4;k++){ctx.strokeStyle='#26374b';ctx.beginPath();ctx.moveTo(0,k*h/4);ctx.lineTo(w,k*h/4);ctx.stroke()}const curves=[[a,'#40d7ff'],[b,'#a78bfa'],[c,'#ffd073']];for(const [rows,color] of curves){ctx.strokeStyle=color;ctx.lineWidth=2;ctx.beginPath();rows.forEach((r,i)=>{const x=(i/(rows.length-1))*w,y=h-8-(r.mse/max)*(h-16);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)});ctx.stroke()}ctx.strokeStyle='#f7faff';ctx.lineWidth=1;const x=frame/(a.length-1)*w;ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();ctx.fillStyle='#b8c8dd';ctx.font='12px system-ui';ctx.fillText('cyan = tracked   violet = fixed   amber = lag40',15,20)}
function update(){const scene=sceneEl.value;for(const [p,c,l] of mapping)drawPolicy(scene,p,c,l);const r=metrics[scene].tracked[frame];document.getElementById('frameCounter').textContent=(frame+1)+' / '+meta.frames;document.getElementById('wMse').textContent=r.mse.toFixed(1);document.getElementById('proxy').textContent=(r.sample_proxy*100).toFixed(1)+'%';document.getElementById('position').textContent=frame+' / '+(meta.frames-1);slider.value=frame;chart()}
function tick(ts){if(!playing)return;if(!lastTick)lastTick=ts;accumulator+=(ts-lastTick)*Number(speedEl.value);lastTick=ts;while(accumulator>=1000/30){accumulator-=1000/30;frame=(frame+1)%meta.frames}update();requestAnimationFrame(tick)}
function setPlay(value){playing=value;playBtn.textContent=value?'❚❚ Pause replay':'▶ Play replay';lastTick=0;if(value)requestAnimationFrame(tick)}
playBtn.addEventListener('click',()=>setPlay(!playing));slider.addEventListener('input',()=>{setPlay(false);frame=Number(slider.value);update()});sceneEl.addEventListener('change',update);document.addEventListener('keydown',e=>{if(e.code==='Space'&&e.target.tagName!=='SELECT'){e.preventDefault();setPlay(!playing)}else if(e.code==='ArrowRight'){setPlay(false);frame=Math.min(meta.frames-1,frame+1);update()}else if(e.code==='ArrowLeft'){setPlay(false);frame=Math.max(0,frame-1);update()}});
slider.max=meta.frames-1;document.getElementById('deviceClass').textContent=meta.result_class.toUpperCase();document.getElementById('device').textContent=meta.device;document.getElementById('dispatches').textContent=meta.total_dispatches.toLocaleString();document.getElementById('methodData').textContent=meta.frames+' frames, '+meta.resolution.join('×')+' pixels, 2 scenes, 4 policies. '+meta.scientific_status;
for(let i=0;i<Math.min(meta.frames,10);i++)for(const [p] of mapping)imageFor('chirp',p,i);
update();setPlay(true);
</script></body></html>'''

if __name__ == "__main__":
    main()
