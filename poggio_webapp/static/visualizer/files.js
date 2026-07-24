import { $ } from "./dom.js";
import { ingest } from "./schema.js";
import { state } from "./state.js";
import { ready } from "./view.js";

function readJSON(file, which){
  const r=new FileReader();
  r.onload=()=>{try{const d=ingest(JSON.parse(r.result));
    if(which==="A"){state.dataA=d; mark("jsonLabelA",file.name);}
    else {state.dataB=d; mark("jsonLabelB",file.name);}
    ready();}catch(e){alert("Not valid JSON:\n"+e.message);}};
  r.readAsText(file);
}
function mark(id,name){const el=$(id);el.classList.add("loaded");el.querySelector("span").textContent="✓ "+name;}
function readIMG(file){if(state.imageUrl)URL.revokeObjectURL(state.imageUrl);state.calibration=null;state.imageUrl=URL.createObjectURL(file);
  state.imageKey="file:"+file.name+":"+file.size;mark("imgLabel",file.name);ready();}

$("jsonInputA").onchange=e=>e.target.files[0]&&readJSON(e.target.files[0],"A");
$("jsonInputB").onchange=e=>e.target.files[0]&&readJSON(e.target.files[0],"B");
$("imgInput").onchange=e=>e.target.files[0]&&readIMG(e.target.files[0]);

$("compareMode").onchange=e=>{
  state.compare=e.target.checked;
  $("rowB").style.display=state.compare?"flex":"none";
  $("dropSub").textContent=state.compare?"image + JSON A + JSON B":"image + one JSON";
  ready();
};

const drop=$("drop");
["dragover","dragenter"].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add("hot");}));
["dragleave","drop"].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove("hot");}));
document.body.addEventListener("dragover",e=>e.preventDefault());
document.body.addEventListener("drop",e=>{
  e.preventDefault();
  const files=[...e.dataTransfer.files];
  const imgs=files.filter(f=>f.type.startsWith("image/"));
  const jsons=files.filter(f=>f.type.includes("json")||f.name.endsWith(".json"));
  if(imgs[0])readIMG(imgs[0]);
  if(jsons[0])readJSON(jsons[0], "A");
  if(jsons[1]){ if(!state.compare){state.compare=true;$("compareMode").checked=true;$("rowB").style.display="flex";}
    readJSON(jsons[1],"B"); }
});

// --- auto-load from the pipeline job -------------------------------------
// When opened from the app as /visualizer?job=<id>, fetch the job's scan and
// extraction JSON from the server instead of making the user re-pick files
// it already has. The pickers stay live as overrides — loading a different
// JSON into slot B for an A/B compare works exactly as before.
(async function autoloadFromJob(){
  const job = new URLSearchParams(location.search).get("job");
  if(!job) return;
  try{
    const r = await fetch(`/api/jobs/${job}/visualizer-files`);
    if(!r.ok) return;               // unknown job — fall back to manual pickers
    const f = await r.json();
    state.calibration = f.calibration || null;
    if(f.image_url){
      state.imageUrl = f.image_url;        // plain URL; revokeObjectURL no-ops on it
      state.imageKey = "job:"+job+":"+f.image_url;
      mark("imgLabel", "auto: job scan");
    }
    if(f.jsons && f.jsons.length){
      const a = f.jsons[0];
      state.dataA = ingest(await (await fetch(a.url)).json());
      mark("jsonLabelA", "auto: " + a.label);
      if(f.jsons.length > 1){
        // pre-fetch the runner-up (e.g. raw extraction vs normalized) into
        // slot B so ticking "Compare two runs" shows it instantly
        const b = f.jsons[1];
        state.dataB = ingest(await (await fetch(b.url)).json());
        mark("jsonLabelB", "auto: " + b.label);
      }
    }
    if(state.dataA || state.imageUrl) ready();
  }catch(e){
    console.warn("autoload from job failed; use the file pickers", e);
  }
})();
