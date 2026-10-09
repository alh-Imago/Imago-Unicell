// unicell_unit_web.ino -- WiFi remote control of the small unit (Tang Nano 20K + SD card) from an ESP32 (ledger #1036).
//
//  * Open  http://unicell.local/   (or the IP address printed on the Serial Monitor) in a browser on the same WiFi.
//  * Login: user "unicell", password = the web password (printed at first boot; change it with  webpass <new>  in the Serial Monitor).
//  * First time:  Serial Monitor (115200, Newline), type   wifi <ssid> <password>   then it joins your WiFi and prints the address.
//    Until WiFi is set (or if it cannot connect) the ESP32 makes its own network "UniCell-Unit" (password = the web password): join it and open http://192.168.4.1/
//  * SECURITY: this is plain HTTP with a password, for a trusted home/lab network only. Do not expose it to the internet. It can overwrite raw SD-card blocks (never blocks below 16).
//
// Upload this sketch, then on the web page's Setup card pick the design that is loaded on the FPGA (it must match the bitstream) and which sensor feeds each input.
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <FS.h>
#include <SD.h>
#include "unit_link.h"
#include "sensors.h"

// ---- which design is on the FPGA, and which sensor feeds each input: chosen at run time (web page "Setup" card, or `design relay` in the Serial Monitor), kept in flash ----
#include "design.h"
#include "sampler.h"

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

#include "page.h"   // the web page (kept in a header so the Arduino IDE does not mangle its JavaScript)

static bool authed() {
  if (server.authenticate("unicell", webPass.c_str())) return true;
  server.requestAuthentication(BASIC_AUTH, "UniCell unit");
  return false;
}
static void sendJson(int code, const String& body) { server.sendHeader("Cache-Control", "no-store"); server.send(code, "application/json", body); }
static void sendErr(int code, const String& e) { sendJson(code, String("{\"ok\":false,\"error\":\"") + e + "\"}"); }

static String exampleJson() { String s = dsg().example; s.replace("\n", "\\n"); return s; }

static void handleRoot() { if (!authed()) return; server.sendHeader("Cache-Control", "no-store"); server.send_P(200, "text/html", PAGE); }

static void handleStatus() {
  if (!authed()) return;
  uint32_t id = rd_reg(R_ID), s = rd_reg(R_STATUS), cap = rd_reg(R_CAP_COUNT), did = (id == UNIT_ID) ? rd_reg(R_DESIGN_ID) : 0;
  int loaded = design_by_id(did);
  String j = "{\"ok\":true,\"design\":\"" + String(dsg().name) + "\",\"lanes\":" + String(dsg().lanes) + ",\"laneNames\":\"" + dsg().laneNames + "\",\"example\":\"" + exampleJson() + "\"";
  j += ",\"id\":\"0x" + String(id, HEX) + "\",\"idOk\":" + (id == UNIT_ID ? "true" : "false");
  j += ",\"loaded\":\"" + String(loaded >= 0 ? DESIGNS[loaded].name : (did ? "an unknown design" : "an older bitstream (no ID)")) + "\",\"loadedKey\":\"" + String(loaded >= 0 ? DESIGNS[loaded].key : "") + "\",\"match\":" + (loaded == g_design ? "true" : "false");
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
  const int L = dsg().lanes;
  if (n == 0 || n % L) { sendErr(400, String("need a multiple of ") + L + " numbers per run (" + dsg().laneNames + ")"); return; }
  int items = n / L;
  const char* err = run_items(in, items, L, out);
  if (*err) { sendErr(500, err); return; }
  String j = "{\"ok\":true,\"results\":[";
  for (int i = 0; i < items; i++) { if (i) j += ","; j += String((long)out[i]); }
  sendJson(200, j + "]}");
}

// Live sensor feed: read the sensor chosen for each input lane, make one item (one word per lane), run it through the design, return readings + result.
// Tree / relay designs get the packed SensorTrix word (amount<<16 | location); the CORDIC gets the raw 16-bit amount as its angle (scale it in your sensor function).
static void handleLive() {
  if (!authed()) return;
  const int L = dsg().lanes;
  int32_t in[MAX_LANES], out[1]; String r = "";
  uint32_t t0 = millis();
  for (int i = 0; i < L; i++) {
    const Sensor& sn = SENSORS[g_laneSensor[i]];
    uint16_t a = g_latest[i];                      // sampled continuously on core 0 (sampler.h)
    in[i] = dsg().rawAngle ? (int32_t)a : (int32_t)sensor_word(sn, a);
    if (i) r += ",";
    r += String("{\"name\":\"") + sn.name + "\",\"loc\":" + sn.loc + ",\"amount\":" + a + "}";
  }
  const char* err = run_items(in, 1, L, out);
  if (*err) { sendErr(500, err); return; }
  sendJson(200, String("{\"ok\":true,\"readings\":[") + r + "],\"seq\":" + String((unsigned long)g_sampleSeq) + ",\"result\":" + String((long)out[0]) + ",\"ms\":" + String(millis() - t0) + "}");
}

// Setup: which design is on the FPGA and which sensor feeds each input lane. Saved in flash; read back at start-up.
static void handleConfig() {
  if (!authed()) return;
  String j = String("{\"ok\":true,\"design\":\"") + dsg().key + "\",\"designs\":[";
  for (int i = 0; i < DESIGN_COUNT; i++) { if (i) j += ","; j += String("{\"key\":\"") + DESIGNS[i].key + "\",\"name\":\"" + DESIGNS[i].name + "\",\"lanes\":" + DESIGNS[i].lanes + "}"; }
  j += "],\"sensors\":[";
  for (int i = 0; i < SENSOR_COUNT; i++) { if (i) j += ","; j += String("\"") + SENSORS[i].name + "\""; }
  j += "],\"laneSensor\":[";
  for (int i = 0; i < MAX_LANES; i++) { if (i) j += ","; j += String(g_laneSensor[i]); }
  sendJson(200, j + "]}");
}
static void saveConfig() {
  prefs.putString("design", dsg().key);
  String l = ""; for (int i = 0; i < MAX_LANES; i++) { if (i) l += ","; l += String(g_laneSensor[i]); }
  prefs.putString("lsens", l);
}
static void handleConfigSet() {
  if (!authed()) return;
  int d = design_index(server.arg("design").c_str());
  if (d < 0) { sendErr(400, "unknown design"); return; }
  int ls[MAX_LANES]; for (int i = 0; i < MAX_LANES; i++) ls[i] = g_laneSensor[i];
  for (int i = 0; i < MAX_LANES; i++) {
    String k = String("s") + i;
    if (server.hasArg(k)) { int v = server.arg(k).toInt(); if (v < 0 || v >= SENSOR_COUNT) { sendErr(400, "unknown sensor"); return; } ls[i] = v; }
  }
  g_design = d; for (int i = 0; i < MAX_LANES; i++) g_laneSensor[i] = ls[i];
  saveConfig();
  sendJson(200, "{\"ok\":true}");
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
  else if (!strcmp(cmd, "id")) { uint32_t v = rd_reg(R_ID); Serial.printf("ID = 0x%08X %s\n", (unsigned)v, v == UNIT_ID ? "OK" : "WRONG"); if (v == UNIT_ID) { uint32_t d = rd_reg(R_DESIGN_ID); int k = design_by_id(d); Serial.printf("design on the Tang = 0x%08X (%s); Setup says %s\n", (unsigned)d, k >= 0 ? DESIGNS[k].name : (d ? "unknown" : "older bitstream, no ID"), dsg().name); } }
  else if (!strcmp(cmd, "design") && a && design_index(a) >= 0) { g_design = design_index(a); saveConfig(); Serial.printf("design: %s (it must match the bitstream on the FPGA)\n", dsg().name); }
  else if (!strcmp(cmd, "design")) Serial.printf("design now: %s.  usage: design cordic | relay | tree\n", dsg().name);
  else if (!strcmp(cmd, "reboot")) ESP.restart();
  else Serial.println("commands: wifi <ssid> <password> | wificlear | webpass <pw> | ip | id | design <cordic|relay|tree> | reboot");
}

void setup() {
  Serial.begin(115200);
  link_begin();
  sensors_begin();
  sampler_begin();
  fileSpi.begin(FILE_SCK, FILE_MISO, FILE_MOSI, FILE_CS);
  haveFiles = SD.begin(FILE_CS, fileSpi, 4000000);
  Serial.println(haveFiles ? "ESP32 SD card: found" : "ESP32 SD card: none (fine; the file panel will say so)");
  prefs.begin("unicell", false);
  wifiSsid = prefs.getString("ssid", ""); wifiPass = prefs.getString("pass", ""); webPass = prefs.getString("webpass", "");
  if (webPass.length() < 8) { webPass = randomPass(); prefs.putString("webpass", webPass); Serial.printf("\nFirst boot: web password generated: %s   (change with: webpass <new>)\n", webPass.c_str()); }
  g_design = design_index(prefs.getString("design", "cordic").c_str()); if (g_design < 0) g_design = 0;
  design_parse_lanes(prefs.getString("lsens", "").c_str());
  Serial.printf("\nUniCell unit web control. Design: %s  (change it on the page's Setup card, or: design cordic|relay|tree)\n", dsg().name);
  startNetwork();
  server.on("/", HTTP_GET, handleRoot);
  server.on("/api/status", HTTP_GET, handleStatus);
  server.on("/api/run", HTTP_POST, handleRun);
  server.on("/api/live", HTTP_GET, handleLive);
  server.on("/api/config", HTTP_GET, handleConfig);
  server.on("/api/config", HTTP_POST, handleConfigSet);
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
