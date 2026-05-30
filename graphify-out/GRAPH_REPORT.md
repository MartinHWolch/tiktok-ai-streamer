# Graph Report - E:\tiktok-ai-streamer  (2026-05-30)

## Corpus Check
- 29 files · ~54,898 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 448 nodes · 726 edges · 37 communities (13 shown, 24 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 55 edges (avg confidence: 0.72)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Event Orchestration Core|Event Orchestration Core]]
- [[_COMMUNITY_Panel Old (Legacy UI)|Panel Old (Legacy UI)]]
- [[_COMMUNITY_Panel New (Refactored UI)|Panel New (Refactored UI)]]
- [[_COMMUNITY_Documentation & Roadmap|Documentation & Roadmap]]
- [[_COMMUNITY_Server Infrastructure|Server Infrastructure]]
- [[_COMMUNITY_TTS Engine|TTS Engine]]
- [[_COMMUNITY_OBS Overlay Client|OBS Overlay Client]]
- [[_COMMUNITY_Overlay-Panel Shared Functions|Overlay-Panel Shared Functions]]
- [[_COMMUNITY_Response Pipeline|Response Pipeline]]
- [[_COMMUNITY_Core Service Instances|Core Service Instances]]
- [[_COMMUNITY_VTube Studio Integration|VTube Studio Integration]]
- [[_COMMUNITY_TikTok Live Integration|TikTok Live Integration]]
- [[_COMMUNITY_VTube Studio API Reference|VTube Studio API Reference]]
- [[_COMMUNITY_Points & Loyalty System|Points & Loyalty System]]
- [[_COMMUNITY_Package Metadata|Package Metadata]]
- [[_COMMUNITY_OpenCode Configuration|OpenCode Configuration]]
- [[_COMMUNITY_Panel Initialization|Panel Initialization]]
- [[_COMMUNITY_Overlay VTube & Dependencies|Overlay VTube & Dependencies]]
- [[_COMMUNITY_OpenCode Schema Config|OpenCode Schema Config]]
- [[_COMMUNITY_OpenCode Package Dependencies|OpenCode Package Dependencies]]
- [[_COMMUNITY_Panel HTML Pages|Panel HTML Pages]]
- [[_COMMUNITY_Panel UI Helpers|Panel UI Helpers]]
- [[_COMMUNITY_Configuration Module|Configuration Module]]
- [[_COMMUNITY_Edge TTS Engine|Edge TTS Engine]]
- [[_COMMUNITY_Flask Web Framework|Flask Web Framework]]
- [[_COMMUNITY_Python Dotenv|Python Dotenv]]
- [[_COMMUNITY_VTube Studio JS API|VTube Studio JS API]]
- [[_COMMUNITY_Overlay HTML Page|Overlay HTML Page]]
- [[_COMMUNITY_Panel Rule Loading|Panel Rule Loading]]
- [[_COMMUNITY_VTS Status Check|VTS Status Check]]
- [[_COMMUNITY_Panel Setup Rendering|Panel Setup Rendering]]
- [[_COMMUNITY_Panel Stats Display|Panel Stats Display]]
- [[_COMMUNITY_Panel Voice Options|Panel Voice Options]]
- [[_COMMUNITY_Panel Voice Population|Panel Voice Population]]
- [[_COMMUNITY_Spam Config Save|Spam Config Save]]
- [[_COMMUNITY_OpenCode Dependency List|OpenCode Dependency List]]

## God Nodes (most connected - your core abstractions)
1. `EventOrchestrator` - 84 edges
2. `TTSClient` - 29 edges
3. `TikTok AI Streamer` - 26 edges
4. `VTubeStudioClient` - 18 edges
5. `ResponsePipeline` - 16 edges
6. `TikTokClient` - 15 edges
7. `SseFlaskServer` - 13 edges
8. `PointsManager` - 12 edges
9. `ColoredFormatter` - 11 edges
10. `sseOnMessage()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `VTube Expression Action Editor` --semantically_similar_to--> `VTS Expression Activation`  [INFERRED] [semantically similar]
  panel/panel.js → README_vtubestudioAPI.md
- `VTube Hotkey Action Editor` --semantically_similar_to--> `VTS Hotkey Trigger`  [INFERRED] [semantically similar]
  panel/panel.js → README_vtubestudioAPI.md
- `Event Orchestrator` --shares_data_with--> `renderRules() - Rules Grid Renderer`  [INFERRED]
  README.md → panel/panel.js
- `Kokoro Voice Blend` --shares_data_with--> `getVoiceGender() - Voice Gender Detection`  [INFERRED]
  README.md → panel/panel.js
- `startLipSync() - Lip Sync Analysis` --conceptually_related_to--> `NumPy`  [INFERRED]
  overlay/overlay.js → requirements.txt

## Hyperedges (group relationships)
- **3-stage message processing pipeline (incoming → generated → playback)** — pipeline_ResponsePipeline, ai_client_AIClient, tts_client_TTSClient, overlay_server_OverlayServer [INFERRED 0.85]
- **SSE publish-subscribe broadcast system** — event_orchestrator_EventOrchestrator, sse_server_SseFlaskServer, overlay_server_OverlayServer, control_panel_server_ControlPanelServer [INFERRED 0.85]
- **TTS Audio Playback and Lip Sync Pipeline** — overlay_playTts, overlay_processTtsQueue, overlay_initLipSync, overlay_startLipSync, overlay_stopLipSync, overlay_VtubeMouthAPI [EXTRACTED 1.00]
- **SSE Real-Time Event Stream** — overlay_sseOnMessage, panel_sseOnMessage, panel_connectSSE, readme_OBSOverlay, readme_ControlPanel [EXTRACTED 1.00]
- **VTube Studio Integration Flow** — readme_VTubeClient, vtubeapi_VTubeStudioAPI, vtubeapi_WebSocket, vtubeapi_Authentication, panel_refreshVtsStatus, panel_ActionEditorVtubeExpr, panel_ActionEditorVtubeHotkey [EXTRACTED 1.00]

## Communities (37 total, 24 thin omitted)

### Community 1 - "Panel Old (Legacy UI)"
Cohesion: 0.09
Nodes (38): addActionRow(), addChatMsg(), addLog(), addLogSilent(), applyLogFilter(), applyTheme(), closeDropdown(), createActionConfig() (+30 more)

### Community 2 - "Panel New (Refactored UI)"
Cohesion: 0.09
Nodes (38): addActionRow(), addChatMsg(), addLog(), addLogSilent(), applyLogFilter(), applyTheme(), closeDropdown(), createActionConfig() (+30 more)

### Community 3 - "Documentation & Roadmap"
Cohesion: 0.05
Nodes (42): getVoiceGender() - Voice Gender Detection, renderRules() - Rules Grid Renderer, showToast() - Undo Notification, config.py Configuration, Web Control Panel, control_panel_server.py, Event Orchestrator, Groq AI Client (+34 more)

### Community 4 - "Server Infrastructure"
Cohesion: 0.09
Nodes (8): AIClient, Config, ControlPanelServer, ColoredFormatter, main(), setup_logging(), OverlayServer, SseFlaskServer

### Community 6 - "OBS Overlay Client"
Cohesion: 0.15
Nodes (18): alertsContainer, createAlert(), createMessage(), emojiExplosion(), ensureDebugLog(), escapeHtml(), evtSource, hasNonAscii() (+10 more)

### Community 7 - "Overlay-Panel Shared Functions"
Cohesion: 0.12
Nodes (17): /api/playback_done Endpoint, /api/playback_started Endpoint, createAlert() - Overlay Alert, createMessage() - Chat Message Display, emojiExplosion() - Particle Animation, escapeHtml() - HTML Escaping, initLipSync() - AudioContext Setup, playSfx() - SFX Playback (+9 more)

### Community 9 - "Core Service Instances"
Cohesion: 0.23
Nodes (16): AI response generator (Groq), Intent-based fallback reply system, Admin control panel SSE server, Event orchestrator hub, Gift-to-action event rules engine, Anti-spam rate-limit and duplicate filter, System entry point (main), Browser overlay SSE server (+8 more)

### Community 12 - "VTube Studio API Reference"
Cohesion: 0.15
Nodes (13): VTube Expression Action Editor, VTube Hotkey Action Editor, VTube Studio Client, VTS ArtMesh Color Tinting, VTS Authentication Token Flow, VTS Expression Activation, VTS Hotkey Trigger, Live2D Items in VTS (+5 more)

### Community 14 - "Package Metadata"
Cohesion: 0.22
Nodes (8): description, keywords, license, name, scripts, start, test, version

### Community 15 - "OpenCode Configuration"
Cohesion: 0.50
Nodes (4): Graphify OpenCode Command, GraphifyPlugin OpenCode Plugin, OpenCode Configuration, tool.execute.before Hook

### Community 16 - "Panel Initialization"
Cohesion: 0.50
Nodes (4): initPanel() - Panel Initialization, panel/panel.js (Current), panel/panel_old.js (Deprecated), postJSON() - Panel API Utility

### Community 17 - "Overlay VTube & Dependencies"
Cohesion: 0.50
Nodes (4): /api/vtube_mouth Endpoint, startLipSync() - Lip Sync Analysis, stopLipSync() - Lip Sync Stop, NumPy

## Knowledge Gaps
- **91 isolated node(s):** `name`, `version`, `description`, `start`, `test` (+86 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EventOrchestrator` connect `Event Orchestration Core` to `Response Pipeline`, `Server Infrastructure`, `Points & Loyalty System`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **Why does `TTSClient` connect `TTS Engine` to `Server Infrastructure`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `ColoredFormatter` connect `Server Infrastructure` to `Event Orchestration Core`, `VTube Studio Integration`, `TikTok Live Integration`, `TTS Engine`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `EventOrchestrator` (e.g. with `ResponsePipeline` and `PointsManager`) actually correct?**
  _`EventOrchestrator` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `TikTok AI Streamer` (e.g. with `Viewer Leaderboard` and `Plugin System`) actually correct?**
  _`TikTok AI Streamer` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `version`, `description` to the rest of the system?**
  _91 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Event Orchestration Core` be split into smaller, more focused modules?**
  _Cohesion score 0.057124310288867254 - nodes in this community are weakly interconnected._