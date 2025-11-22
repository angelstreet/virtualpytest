# Automation Prompts - Platform Selection

Choose the appropriate automation prompt for your device type:

---

## 🌐 Web/Desktop Automation
**Use for**: Websites, web apps, desktop browsers  
**Device Models**: `host_vnc`, `web`  
**Selectors**: CSS (#id, .class), XPath  
**Navigation**: Click, BACK

→ **[Web Automation Prompt](automate-prompt-web.md)**

**Example apps**: E-commerce sites, SaaS apps, content sites

---

## 📱 Mobile Automation
**Use for**: Android mobile apps  
**Device Model**: `android_mobile`  
**Selectors**: resource-id, content-desc, XPath  
**Navigation**: Touch, swipe, BACK

→ **[Mobile Automation Prompt](automate-prompt-mobile.md)**

**Example apps**: Streaming apps, social media, mobile e-commerce

---

## 📺 TV/STB Automation
**Use for**: TV apps, Set-top boxes, Android TV  
**Device Models**: `android_tv`, `stb`, IR-controlled devices  
**Selectors**: D-pad navigation (dual-layer)  
**Navigation**: UP/DOWN/LEFT/RIGHT, OK, BACK

→ **[TV/STB Automation Prompt](automate-prompt-tv.md)**

**Example apps**: IPTV, VOD, streaming boxes, cable/satellite STBs

---

## 🎯 Quick Reference

| Platform | Prompt | Strategy | Time Savings |
|----------|--------|----------|--------------|
| **Web** | [Web Prompt](automate-prompt-web.md) | AI Exploration (click) | ~67% |
| **Mobile** | [Mobile Prompt](automate-prompt-mobile.md) | AI Exploration (touch) | ~70% |
| **TV/STB** | [TV Prompt](automate-prompt-tv.md) | AI Exploration (dpad) | ~70% |

---

## 📖 Complete Examples

**Sauce Demo (E-commerce Web)**  
→ [sauce-demo-optimal-prompt.md](demo/sauce-demo-optimal-prompt.md)

**More examples coming soon:**
- Netflix Mobile (Streaming)
- Horizon TV (IPTV)
- Social Media App

---

## 🚀 AI Exploration vs Manual

All platform prompts use **AI Exploration** (recommended):

**AI Exploration (3 steps):**
1. `start_ai_exploration` → AI analyzes screen
2. `approve_exploration_plan` → Batch create nodes/edges
3. `validate_exploration_edges` → Auto-test all edges

**Manual (10+ steps per edge):**
1. `dump_ui_elements` → Inspect screen
2. `analyze_screen_for_action` → Get selector
3. `create_node` → Create one node
4. `create_edge` → Create one edge
5. `execute_edge` → Test edge
6. Repeat for each edge...

**Time Saved: 60-90% depending on complexity**

---

## 📚 Full Documentation

For detailed MCP tool documentation:
→ [MCP Server Documentation](../docs/mcp.md)

For AI Exploration tools:
→ [AI Exploration Tools](../docs/mcp/mcp_tools_exploration.md)

---

**Not sure which platform?**
- Web URL (https://...) → **Web**
- Android app package (com.netflix...) → **Mobile** or **TV**
- Remote control (D-pad) → **TV/STB**
- Touch screen → **Mobile**
