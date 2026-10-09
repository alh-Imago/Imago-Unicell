// unicell_unit_web.ino -- WiFi remote control of the small unit (Tang Nano 20K + SD card) from an ESP32 (ledger #1036).
//
//  * Open  http://unicell.local/   (or the IP address printed on the Serial Monitor) in a browser on the same WiFi.
//  * Login: user "unicell", password = the web password (printed at first boot; change it with  webpass <new>  in the Serial Monitor).
//  * First time:  Serial Monitor (115200, Newline), type   wifi <ssid> <password>   then it joins your WiFi and prints the address.
//    Until WiFi is set (or if it cannot connect) the ESP32 makes its own network "UniCell-Unit" (password = the web password): join it and open http://192.168.4.1/
//  * SECURITY: this is plain HTTP with a password, for a trusted home/lab network only. Do not expose it to the internet. It can overwrite raw SD-card blocks (never blocks below 16).
//
// Pick the design that is loaded on the FPGA (one line below), then upload this sketch.
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <FS.h>
#include <SD.h>
#include "unit_link.h"
#include "sensors.h"

// ---- which design is on the FPGA --------------------------------------------------------------------------------------------------------------------
#define DESIGN_CORDIC 1      // 1 input word per item, 1 result: the CORDIC z-convergence (fpga/build/unit_cordic_v1)
// #define DESIGN_TREE4 1    // 4 input words per item, 1 result: the sum of the four (nano/examples/parallel_reduction_tree)
// #define DESIGN_RELAY 1    // 1 input word per item, the same word back (nano/examples/small_relay_chain)

#if defined(DESIGN_TREE4)
  #define DESIGN_NAME  "Parallel reduction tree (sum of 4)"
  #define LANES        4
  #define LANE_NAMES   "four input words per item"
  #define EXAMPLE      "1 2 3 4\n10 20 30 40\n100 200 300 400"
#elif defined(DESIGN_RELAY)
  #define DESIGN_NAME  "Relay chain (word passes through)"
  #define LANES        1
  #define LANE_NAMES   "one input word per item"
  #define EXAMPLE      "7\n123456\n-5"
#else
  #define DESIGN_NAME  "CORDIC z convergence"
  #define LANES        1
  #define LANE_NAMES   "angle z0"
  #define EXAMPLE      "50000\n-50000\n0\n12345\n-12345\n90000"
#endif

// ---- the ESP32's OWN SD card (optional; holds bitstreams, input files, results, the offline kit) ----------------------------------------------------
// A separate SPI bus (HSPI) on four free pins, so it cannot disturb the link to the unit (IO5/18/19/23). Use a 3.3 V-ONLY microSD breakout (see docs/unit_bringup_guide.md).
#define FILE_CS    32
#define FILE_SCK   33
#define FILE_MOSI  25
#define FILE_MISO  26
#define FILE_MAX_BYTES (32UL * 1024UL * 1024UL)
static SPIClass fileSpi(HSPI);
static bool haveFiles = false;
static File upFile;
static String upError;
static uint32_t upBytes = 0;

static WebServer server(80);
static Preferences prefs;
static String wifiSsid, wifiPass, webPass;
static bool apMode = false;

static const char PAGE[] PROGMEM = R"HTML(<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>UniCell unit</title>
<style>
:root{--bg:#10151c;--card:#1a222d;--ink:#e6edf5;--dim:#8fa3b8;--ok:#3fb950;--bad:#f85149;--acc:#58a6ff;--line:#2b3644}
@media (prefers-color-scheme:light){:root{--bg:#f4f6f9;--card:#fff;--ink:#14202e;--dim:#5b6b7e;--line:#d8dee6}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,sans-serif}
main{max-width:760px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:4px 0 2px}p.sub{margin:0 0 14px;color:var(--dim)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin:0 0 14px}
h2{font-size:14px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);margin:0 0 10px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.tile{border:1px solid var(--line);border-radius:8px;padding:8px 10px}.tile b{display:block;font-size:12px;color:var(--dim);font-weight:600}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;background:var(--dim)}.ok{background:var(--ok)}.bad{background:var(--bad)}
textarea,input{width:100%;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:8px;font:14px ui-monospace,monospace}
textarea{min-height:110px}.row{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}.row>*{flex:1 1 120px}
button{background:var(--acc);color:#fff;border:0;border-radius:8px;padding:10px 14px;font:600 14px system-ui;cursor:pointer}button.alt{background:transparent;color:var(--ink);border:1px solid var(--line)}
button:disabled{opacity:.5}table{width:100%;border-collapse:collapse;margin-top:10px;font:14px ui-monospace,monospace}td,th{text-align:right;padding:5px 8px;border-bottom:1px solid var(--line)}th{color:var(--dim);font-weight:600}
#msg{min-height:1.4em;margin-top:8px;color:var(--dim)}#msg.bad{color:var(--bad)}small{color:var(--dim)}
</style></head><body><main>
<h1>UniCell unit</h1><p class="sub" id="design"></p>
<div class="card"><h2>Status</h2><div class="tiles" id="tiles"></div></div>
<div class="card"><h2>Run</h2>
<small id="lanehint"></small>
<textarea id="items" spellcheck="false"></textarea>
<div class="row"><button id="run">Run through the design</button><button class="alt" id="ex">Example</button></div>
<table id="res" hidden><thead><tr><th>#</th><th>input</th><th>result</th></tr></thead><tbody></tbody></table></div>
<div class="card"><h2>Live sensors</h2>
<small id="livehint">Reads the sensors listed in sensors.h and feeds them to the design, one sample at a time.</small>
<div class="row"><button class="alt" id="livebtn">Start live feed</button></div>
<table id="livetab" hidden><thead><tr><th style="text-align:left">sensor</th><th>loc</th><th>amount</th></tr></thead><tbody></tbody></table>
<div id="liveres"></div></div>
<div class="card"><h2>SD card (raw blocks)</h2>
<small>Blocks below 16 are refused. Saving overwrites raw blocks on the card.</small>
<div class="row"><input id="blk" type="number" min="16" value="64" aria-label="start block"><input id="nb" type="number" min="1" max="8" value="1" aria-label="blocks"></div>
<div class="row"><button class="alt" id="sload">Load blocks into the unit</button><button class="alt" id="ssave">Save results to blocks</button><button class="alt" id="sinit">Re-init card</button></div></div>
<div class="card"><h2>Files on the ESP32's own card</h2>
<small id="fhint"></small>
<table id="ftab"><tbody></tbody></table>
<div class="row"><input id="fup" type="file"><button class="alt" id="fsend">Upload</button></div></div>
<div id="msg"></div><p><small>Design and simulate on your own computer: <a href="https://github.com/alh-Imago/Imago-Unicell" target="_blank" rel="noopener">github.com/alh-Imago/Imago-Unicell</a>, then <code>python3 nano/frontend_v1.py</code> (needs internet only to fetch it; this unit works without).</small></p></main>
<script>
const $=id=>document.getElementById(id);let lanes=1;
function msg(t,bad){const m=$('msg');m.textContent=t;m.className=bad?'bad':''}
async function api(path,body){const o=body?{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams(body)}:{};
 const c=new AbortController();const tm=setTimeout(()=>c.abort(),8000);o.signal=c.signal;let r;try{r=await fetch(path,o)}catch(e){throw new Error(e.name==='AbortError'?'no answer from the ESP32 (8 s)':e.message)}finally{clearTimeout(tm)}const j=await r.json().catch(()=>({ok:false,error:'bad reply'}));if(!r.ok||j.ok===false)throw new Error(j.error||('HTTP '+r.status));return j}
function tile(l,v,ok){return '<div class="tile"><b>'+l+'</b><span class="dot '+(ok===true?'ok':ok===false?'bad':'')+'"></span>'+v+'</div>'}
async function status(){try{const s=await api('/api/status');lanes=s.lanes;$('design').textContent=s.design;$('lanehint').textContent='One item per line, '+s.laneNames+' (whole numbers, negatives allowed).';
 $('tiles').innerHTML=tile('Unit link',s.idOk?'answers (ID '+s.id+')':'no answer',s.idOk)+tile('SD card',s.sdReady&&!s.sdError?'ready':(s.sdError?'error '+s.errCode+' (cmd '+s.errCmd+', rx 0x'+s.errRx.toString(16)+')':'not ready'),s.sdReady&&!s.sdError)
 +tile('Results waiting',s.capCount,null)+tile('Network',s.ip+' ('+s.rssi+' dBm)',null)+tile('Uptime',Math.floor(s.uptime/1000)+' s',null)}catch(e){$('tiles').innerHTML=tile('Link',e.message,false)}}
$('ex').onclick=()=>{$('items').value=EXAMPLE};
$('run').onclick=async()=>{$('run').disabled=true;msg('Running...');try{const txt=$('items').value;const r=await api('/api/run',{items:txt});
 const rows=txt.trim().split(/\n+/);$('res').hidden=false;$('res').tBodies[0].innerHTML=r.results.map((v,i)=>'<tr><td>'+(i+1)+'</td><td>'+(rows[i]||'')+'</td><td>'+v+'</td></tr>').join('');msg(r.results.length+' result(s)')}catch(e){msg(e.message,true)}$('run').disabled=false;status()};
async function sd(op){if(op==='save'&&!confirm('Overwrite raw card blocks starting at '+$('blk').value+'?'))return;try{if(op==='init'){await api('/api/sdinit',{x:1})}else{await api('/api/sd',{op:op,block:$('blk').value,n:$('nb').value})}msg('SD '+op+' done')}catch(e){msg(e.message,true)}status()}
async function files(){try{const f=await api('/api/files');$('fhint').textContent=f.card?(f.used+' of '+f.total+' kB used. Names: letters, digits . - _ and space.'):'No SD card in the ESP32 (the ESP32 reads its own card on start-up: insert it and press its reset).';
 $('ftab').tBodies[0].innerHTML=f.files.map(x=>'<tr><td style="text-align:left">'+x.name+'</td><td>'+x.size+' B</td><td><a href="/files?name='+encodeURIComponent(x.name)+'">download</a></td><td><a href="#" data-del="'+x.name+'">delete</a></td></tr>').join('')}catch(e){$('fhint').textContent=e.message}}
$('ftab').onclick=async e=>{const n=e.target.dataset&&e.target.dataset.del;if(!n)return;e.preventDefault();if(!confirm('Delete '+n+'?'))return;try{await api('/api/filedel',{name:n});files()}catch(x){msg(x.message,1)}};
$('fsend').onclick=async()=>{const f=$('fup').files[0];if(!f){msg('choose a file first',1);return}msg('Uploading '+f.name+'...');try{const fd=new FormData();fd.append('file',f,f.name);const r=await fetch('/api/upload',{method:'POST',body:fd});const j=await r.json().catch(()=>({ok:false,error:'bad reply'}));if(!r.ok||j.ok===false)throw new Error(j.error||('HTTP '+r.status));msg('Uploaded '+j.bytes+' bytes');files()}catch(x){msg(x.message,1)}};
let liveOn=false,liveT=null;
async function liveTick(){if(!liveOn)return;try{const j=await api('/api/live');$('livetab').hidden=false;$('livetab').tBodies[0].innerHTML=j.readings.map(r=>'<tr><td style="text-align:left">'+r.name+'</td><td>'+r.loc+'</td><td>'+r.amount+'</td></tr>').join('');$('liveres').textContent='design result: '+j.result+'  ('+j.ms+' ms)'}catch(e){$('liveres').textContent=e.message;liveOn=false;$('livebtn').textContent='Start live feed';return}liveT=setTimeout(liveTick,500)}
$('livebtn').onclick=()=>{liveOn=!liveOn;$('livebtn').textContent=liveOn?'Stop live feed':'Start live feed';if(liveOn)liveTick();else clearTimeout(liveT)};
$('sload').onclick=()=>sd('load');$('ssave').onclick=()=>sd('save');$('sinit').onclick=()=>sd('init');
let EXAMPLE='';fetch('/api/status').then(r=>r.json()).then(s=>{EXAMPLE=s.example;$('items').value=s.example});
status();setInterval(status,3000);files();
</script></body></html>)HTML";

static bool authed() {
  if (server.authenticate("unicell", webPass.c_str())) return true;
  server.requestAuthentication(BASIC_AUTH, "UniCell unit");
  return false;
}
static void sendJson(int code, const String& body) { server.sendHeader("Cache-Control", "no-store"); server.send(code, "application/json", body); }
static void sendErr(int code, const String& e) { sendJson(code, String("{\"ok\":false,\"error\":\"") + e + "\"}"); }

static String exampleJson() { String s = EXAMPLE; s.replace("\n", "\\n"); return s; }

static void handleRoot() { if (!authed()) return; server.sendHeader("Cache-Control", "no-store"); server.send_P(200, "text/html", PAGE); }

static void handleStatus() {
  if (!authed()) return;
  uint32_t id = rd_reg(R_ID), s = rd_reg(R_STATUS), cap = rd_reg(R_CAP_COUNT);
  String j = "{\"ok\":true,\"design\":\"" DESIGN_NAME "\",\"lanes\":" + String(LANES) + ",\"laneNames\":\"" LANE_NAMES "\",\"example\":\"" + exampleJson() + "\"";
  j += ",\"id\":\"0x" + String(id, HEX) + "\",\"idOk\":" + (id == UNIT_ID ? "true" : "false");
  j += ",\"sdReady\":" + String((s & S_SD_READY) ? "true" : "false") + ",\"sdError\":" + String((s & S_SD_ERROR) ? "true" : "false");
  j += ",\"errCode\":" + String((s >> 8) & 31) + ",\"errCmd\":" + String((s >> 16) & 63) + ",\"errRx\":" + String(s >> 24);
  j += ",\"readyPin\":" + String(digitalRead(PIN_READY)) + ",\"capCount\":" + String(cap);
  j += ",\"ip\":\"" + (apMode ? WiFi.softAPIP().toString() : WiFi.localIP().toString()) + "\",\"rssi\":" + String(apMode ? 0 : WiFi.RSSI()) + ",\"uptime\":" + String(millis()) + "}";
  sendJson(200, j);
}

static void handleRun() {
  if (!authed()) return;
  static int32_t in[MAX_WORDS], out[MAX_WORDS];
  String txt = server.arg("items"); int n = 0; const char* p = txt.c_str();
  while (*p) {                                   // numbers separated by anything that is not a digit or a minus sign
    if ((*p >= '0' && *p <= '9') || (*p == '-' && p[1] >= '0' && p[1] <= '9')) {
      if (n >= MAX_WORDS) { sendErr(400, "too many words (limit 512)"); return; }
      char* e; long long v = strtoll(p, &e, 10); in[n++] = (int32_t)v; p = e;
    } else p++;
  }
  if (n == 0 || n % LANES) { sendErr(400, String("need a multiple of ") + LANES + " numbers per run (" + LANE_NAMES + ")"); return; }
  int items = n / LANES;
  const char* err = run_items(in, items, LANES, out);
  if (*err) { sendErr(500, err); return; }
  String j = "{\"ok\":true,\"results\":[";
  for (int i = 0; i < items; i++) { if (i) j += ","; j += String((long)out[i]); }
  sendJson(200, j + "]}");
}

// Live sensor feed: read the first LANES sensors, make one item (one word per lane), run it through the design, return readings + result.
// Tree / relay designs get the packed SensorTrix word (amount<<16 | location); the CORDIC gets the raw 16-bit amount as its angle (scale it in your sensor function).
static void handleLive() {
  if (!authed()) return;
  if (SENSOR_COUNT < LANES) { sendErr(400, String("this design needs ") + LANES + " sensor(s); sensors.h lists " + SENSOR_COUNT); return; }
  int32_t in[LANES], out[1]; String r = "";
  uint32_t t0 = millis();
  for (int i = 0; i < LANES; i++) {
    uint16_t a = sensor_amount(SENSORS[i]);
#if defined(DESIGN_CORDIC)
    in[i] = (int32_t)a;
#else
    in[i] = (int32_t)sensor_word(SENSORS[i], a);
#endif
    if (i) r += ",";
    r += String("{\"name\":\"") + SENSORS[i].name + "\",\"loc\":" + SENSORS[i].loc + ",\"amount\":" + a + "}";
  }
  const char* err = run_items(in, 1, LANES, out);
  if (*err) { sendErr(500, err); return; }
  sendJson(200, String("{\"ok\":true,\"readings\":[") + r + "],\"result\":" + String((long)out[0]) + ",\"ms\":" + String(millis() - t0) + "}");
}

static void handleSd() {
  if (!authed()) return;
  String op = server.arg("op"); uint32_t block = strtoul(server.arg("block").c_str(), NULL, 10), n = strtoul(server.arg("n").c_str(), NULL, 10);
  if (op != "load" && op != "save") { sendErr(400, "op must be load or save"); return; }
  const char* err = sd_op(op == "save", block, n);
  if (*err) { sendErr(500, err); return; }
  sendJson(200, "{\"ok\":true}");
}
static void handleSdInit() { if (!authed()) return; wr_reg(R_CONTROL, C_SD_REINIT); delay(300); sendJson(200, "{\"ok\":true}"); }

// file names: letters, digits, dot, dash, underscore, space; 1-40 characters; no path, no leading dot (the card's root folder only)
static bool goodName(const String& n) {
  if (n.length() < 1 || n.length() > 40 || n[0] == '.') return false;
  for (unsigned i = 0; i < n.length(); i++) { char c = n[i]; if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '.' || c == '-' || c == '_' || c == ' ')) return false; }
  return true;
}
static void handleFiles() {
  if (!authed()) return;
  if (!haveFiles) { sendJson(200, "{\"ok\":true,\"card\":false,\"files\":[]}"); return; }
  // NOTE: SD.usedBytes() scans the whole card's allocation table and can block this single-threaded server for many seconds on a big card (the page then looks dead),
  // so "used" is the sum of the listed files' sizes and "total" is the card size, both instant.
  String list = ""; bool first = true; uint64_t used = 0;
  File root = SD.open("/");
  for (File f = root.openNextFile(); f; f = root.openNextFile()) {
    if (f.isDirectory()) continue;
    String n = f.name(); if (!goodName(n)) continue;
    if (!first) list += ","; first = false; used += f.size();
    list += "{\"name\":\"" + n + "\",\"size\":" + String((unsigned long)f.size()) + "}";
  }
  sendJson(200, "{\"ok\":true,\"card\":true,\"total\":" + String((unsigned long)(SD.cardSize() / 1024)) + ",\"used\":" + String((unsigned long)(used / 1024)) + ",\"files\":[" + list + "]}");
}
static void handleDownload() {
  if (!authed()) return;
  String n = server.arg("name");
  if (!haveFiles || !goodName(n)) { sendErr(404, "no such file"); return; }
  File f = SD.open("/" + n, FILE_READ);
  if (!f || f.isDirectory()) { sendErr(404, "no such file"); return; }
  server.sendHeader("Content-Disposition", "attachment; filename=\"" + n + "\"");
  server.streamFile(f, "application/octet-stream"); f.close();
}
static void handleFileDelete() {
  if (!authed()) return;
  String n = server.arg("name");
  if (!haveFiles || !goodName(n)) { sendErr(400, "bad name"); return; }
  if (!SD.remove("/" + n)) { sendErr(404, "could not delete"); return; }
  sendJson(200, "{\"ok\":true}");
}
static void handleUploadDone() {
  if (!authed()) return;
  if (upError.length()) { sendErr(400, upError); return; }
  sendJson(200, String("{\"ok\":true,\"bytes\":") + upBytes + "}");
}
static void handleUploadData() {            // runs while the file arrives; it cannot send a reply, so it records an error for handleUploadDone
  HTTPUpload& u = server.upload();
  if (u.status == UPLOAD_FILE_START) {
    upError = ""; upBytes = 0;
    if (!server.authenticate("unicell", webPass.c_str())) { upError = "not logged in"; return; }
    if (!haveFiles) { upError = "no SD card in the ESP32"; return; }
    if (!goodName(u.filename)) { upError = "file name not allowed (letters, digits . - _ space; at most 40; no folders)"; return; }
    upFile = SD.open("/" + u.filename, FILE_WRITE);
    if (!upFile) upError = "could not create the file";
  } else if (u.status == UPLOAD_FILE_WRITE) {
    if (upError.length() || !upFile) return;
    upBytes += u.currentSize;
    if (upBytes > FILE_MAX_BYTES) { upError = "file too big (limit 32 MB)"; upFile.close(); return; }
    if (upFile.write(u.buf, u.currentSize) != u.currentSize) upError = "write failed (card full?)";
  } else if (u.status == UPLOAD_FILE_END) { if (upFile) upFile.close(); }
  else if (u.status == UPLOAD_FILE_ABORTED) { if (upFile) upFile.close(); upError = "upload aborted"; }
}
static void handleNotFound() { sendErr(404, "not found"); }

static String randomPass() {
  const char* a = "abcdefghjkmnpqrstuvwxyz23456789"; String s; for (int i = 0; i < 10; i++) s += a[esp_random() % 31]; return s;
}
static void startNetwork() {
  apMode = false;
  if (wifiSsid.length()) {
    WiFi.mode(WIFI_STA); WiFi.begin(wifiSsid.c_str(), wifiPass.c_str());
    Serial.printf("Joining WiFi \"%s\" ...", wifiSsid.c_str());
    for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) { delay(500); Serial.print("."); }
    Serial.println();
  }
  if (WiFi.status() != WL_CONNECTED) {
    apMode = true; WiFi.mode(WIFI_AP); WiFi.softAP("UniCell-Unit", webPass.c_str());
    Serial.printf("No WiFi: own network \"UniCell-Unit\" (password = the web password). Open http://%s/\n", WiFi.softAPIP().toString().c_str());
  } else Serial.printf("WiFi up. Open  http://%s/   or  http://unicell.local/\n", WiFi.localIP().toString().c_str());
  MDNS.begin("unicell");
}

static String line;
static void serialCmd(char* s) {
  char* cmd = strtok(s, " "); if (!cmd) return; char* a = strtok(NULL, " "); char* b = strtok(NULL, "");
  if (!strcmp(cmd, "wifi") && a) { wifiSsid = a; wifiPass = b ? b : ""; prefs.putString("ssid", wifiSsid); prefs.putString("pass", wifiPass); Serial.println("saved; restarting"); delay(300); ESP.restart(); }
  else if (!strcmp(cmd, "wificlear")) { prefs.remove("ssid"); prefs.remove("pass"); Serial.println("WiFi forgotten; restarting"); delay(300); ESP.restart(); }
  else if (!strcmp(cmd, "webpass") && a && strlen(a) >= 8) { webPass = a; prefs.putString("webpass", webPass); Serial.println("web password changed (the own-network password too, after a restart)"); }
  else if (!strcmp(cmd, "webpass")) Serial.println("usage: webpass <at least 8 characters, no spaces>");
  else if (!strcmp(cmd, "ip")) Serial.printf("http://%s/  user: unicell  password: %s\n", (apMode ? WiFi.softAPIP() : WiFi.localIP()).toString().c_str(), webPass.c_str());
  else if (!strcmp(cmd, "id")) { uint32_t v = rd_reg(R_ID); Serial.printf("ID = 0x%08X %s\n", (unsigned)v, v == UNIT_ID ? "OK" : "WRONG"); }
  else if (!strcmp(cmd, "reboot")) ESP.restart();
  else Serial.println("commands: wifi <ssid> <password> | wificlear | webpass <pw> | ip | id | reboot");
}

void setup() {
  Serial.begin(115200);
  link_begin();
  sensors_begin();
  fileSpi.begin(FILE_SCK, FILE_MISO, FILE_MOSI, FILE_CS);
  haveFiles = SD.begin(FILE_CS, fileSpi, 4000000);
  Serial.println(haveFiles ? "ESP32 SD card: found" : "ESP32 SD card: none (fine; the file panel will say so)");
  prefs.begin("unicell", false);
  wifiSsid = prefs.getString("ssid", ""); wifiPass = prefs.getString("pass", ""); webPass = prefs.getString("webpass", "");
  if (webPass.length() < 8) { webPass = randomPass(); prefs.putString("webpass", webPass); Serial.printf("\nFirst boot: web password generated: %s   (change with: webpass <new>)\n", webPass.c_str()); }
  Serial.println("\nUniCell unit web control. Design: " DESIGN_NAME);
  startNetwork();
  server.on("/", HTTP_GET, handleRoot);
  server.on("/api/status", HTTP_GET, handleStatus);
  server.on("/api/run", HTTP_POST, handleRun);
  server.on("/api/live", HTTP_GET, handleLive);
  server.on("/api/sd", HTTP_POST, handleSd);
  server.on("/api/sdinit", HTTP_POST, handleSdInit);
  server.on("/api/files", HTTP_GET, handleFiles);
  server.on("/files", HTTP_GET, handleDownload);
  server.on("/api/filedel", HTTP_POST, handleFileDelete);
  server.on("/api/upload", HTTP_POST, handleUploadDone, handleUploadData);
  server.onNotFound(handleNotFound);
  server.begin();
  Serial.println("Type  ip  to see the address and password; help = any other word.");
}

void loop() {
  server.handleClient();
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') { if (line.length()) { char buf[160]; line.toCharArray(buf, sizeof buf); line = ""; serialCmd(buf); } }
    else if (line.length() < 150) line += c;
  }
  if (!apMode && WiFi.status() != WL_CONNECTED) { static uint32_t t = 0; if (millis() - t > 15000) { t = millis(); WiFi.reconnect(); } }
}
