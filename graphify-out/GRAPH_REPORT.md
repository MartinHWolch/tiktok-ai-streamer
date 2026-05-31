# Graph Report - tiktok-ai-streamer  (2026-05-30)

## Corpus Check
- 26 files · ~56,818 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 572 nodes · 848 edges · 54 communities (25 shown, 29 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 57 edges (avg confidence: 0.72)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e240b75a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 53|Community 53]]

## God Nodes (most connected - your core abstractions)
1. `EventOrchestrator` - 84 edges
2. `API Details` - 38 edges
3. `TTSClient` - 29 edges
4. `TikTok AI Streamer` - 26 edges
5. `VTubeStudioClient` - 19 edges
6. `ResponsePipeline` - 17 edges
7. `SseFlaskServer` - 16 edges
8. `TikTokClient` - 15 edges
9. `PointsManager` - 13 edges
10. `ColoredFormatter` - 12 edges

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

## Communities (54 total, 29 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (6): EventOrchestrator, Conecta el pipeline con los servicios disponibles., Extrae emotion/sfx de metadatos en respuesta AI (formato [emotion:happy][sfx:din, Extrae emotion/sfx de metadatos en respuesta AI (formato [emotion:happy][sfx:din, Ejecuta acciones temporales sin guardarlas como regla., Ejecuta acciones temporales sin guardarlas como regla.

### Community 1 - "Community 1"
Cohesion: 0.09
Nodes (38): addActionRow(), addChatMsg(), addLog(), addLogSilent(), applyLogFilter(), applyTheme(), closeDropdown(), createActionConfig() (+30 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (38): addActionRow(), addChatMsg(), addLog(), addLogSilent(), applyLogFilter(), applyTheme(), closeDropdown(), createActionConfig() (+30 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (42): getVoiceGender() - Voice Gender Detection, renderRules() - Rules Grid Renderer, showToast() - Undo Notification, config.py Configuration, Web Control Panel, control_panel_server.py, Event Orchestrator, Groq AI Client (+34 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (15): AIClient, Config, ControlPanelServer, ColoredFormatter, main(), setup_logging(), OverlayServer, Clase base para servidores Flask con SSE (Server-Sent Events).          Usa broa (+7 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (18): alertsContainer, createAlert(), createMessage(), emojiExplosion(), ensureDebugLog(), escapeHtml(), evtSource, hasNonAscii() (+10 more)

### Community 7 - "Community 7"
Cohesion: 0.12
Nodes (17): /api/playback_done Endpoint, /api/playback_started Endpoint, createAlert() - Overlay Alert, createMessage() - Chat Message Display, emojiExplosion() - Particle Animation, escapeHtml() - HTML Escaping, initLipSync() - AudioContext Setup, playSfx() - SFX Playback (+9 more)

### Community 8 - "Community 8"
Cohesion: 0.10
Nodes (13): ResponsePipeline: cola de procesamiento 3-etapas.  Etapa 1 - Incoming: mensajes, Llamado cuando llega un mensaje de TikTok., Llamado cuando llega un mensaje de TikTok., Para comandos/bienvenidas que ya tienen texto (saltan IA)., Para comandos/bienvenidas que ya tienen texto (saltan IA)., Llamado cuando el overlay confirma que empezo a reproducir., Llamado cuando el overlay confirma que empezo a reproducir., Llamado cuando el overlay confirma que termino de reproducir. (+5 more)

### Community 9 - "Community 9"
Cohesion: 0.23
Nodes (16): AI response generator (Groq), Intent-based fallback reply system, Admin control panel SSE server, Event orchestrator hub, Gift-to-action event rules engine, Anti-spam rate-limit and duplicate filter, System entry point (main), Browser overlay SSE server (+8 more)

### Community 10 - "Community 10"
Cohesion: 0.16
Nodes (5): Envia request y recibe respuesta sincrona., Cliente WebSocket para VTube Studio API., Lista parametros disponibles del modelo., Inyecta valores de parametros al modelo. silent=True no loguea., VTubeStudioClient

### Community 11 - "Community 11"
Cohesion: 0.07
Nodes (28): Adding new tracking parameters ("custom parameters"), API Details, API Permissions, API Server Discovery (UDP), Asking user to select ArtMeshes, Authentication, Checking if face is currently found by tracker, Delete custom parameters (+20 more)

### Community 12 - "Community 12"
Cohesion: 0.15
Nodes (13): VTube Expression Action Editor, VTube Hotkey Action Editor, VTube Studio Client, VTS ArtMesh Color Tinting, VTS Authentication Token Flow, VTS Expression Activation, VTS Hotkey Trigger, Live2D Items in VTS (+5 more)

### Community 14 - "Community 14"
Cohesion: 0.22
Nodes (8): description, keywords, license, name, scripts, start, test, version

### Community 15 - "Community 15"
Cohesion: 0.50
Nodes (4): Graphify OpenCode Command, GraphifyPlugin OpenCode Plugin, OpenCode Configuration, tool.execute.before Hook

### Community 16 - "Community 16"
Cohesion: 0.50
Nodes (4): initPanel() - Panel Initialization, panel/panel.js (Current), panel/panel_old.js (Deprecated), postJSON() - Panel API Utility

### Community 17 - "Community 17"
Cohesion: 0.50
Nodes (4): /api/vtube_mouth Endpoint, startLipSync() - Lip Sync Analysis, stopLipSync() - Lip Sync Stop, NumPy

### Community 37 - "Community 37"
Cohesion: 0.15
Nodes (12): Backend completo, Características, Ejecución, Estructura, Instalación, Modo TikTok Real, Notas, Requisitos (+4 more)

### Community 38 - "Community 38"
Cohesion: 0.18
Nodes (10): <a href="https://denchisoft.com"><img src="https://raw.githubusercontent.com/DenchiSoft/VTubeStudio/master/Images/vtube_studio_logo_nyan_2.png" width="542" /></a><br> [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/DenchiSoft/VTubeStudio/blob/master/LICENSE) [![VTube Studio Discord](https://discordapp.com/api/guilds/652602255748497449/widget.png?style=shield)](https://discord.gg/VTubeStudio) [![Stars](https://img.shields.io/github/stars/DenchiSoft/VTubeStudio?style=social)](https://github.com/DenchiSoft/VTubeStudio) [![Twitter Follow](https://img.shields.io/twitter/follow/VTubeStudio.svg?style=social)](https://twitter.com/VTubeStudio), Are you a developer looking for a way to receive tracking data from the VTube Studio iPhone app?, Are you a developer who wants to learn about creating VTube Studio Plugins?, Are you looking for a [list of VTube Studio Plugins](https://github.com/DenchiSoft/VTubeStudio/wiki/Plugins)?, Are you looking for the [VTube Studio Manual](https://github.com/DenchiSoft/VTubeStudio/wiki)?, Available Examples, Contents, Event API (+2 more)

### Community 39 - "Community 39"
Cohesion: 0.18
Nodes (10): Arquitectura, Estabilidad, Resumen por batch, Seguridad, Tier 1 — Impacto alto, esfuerzo medio, Tier 2 — Calidad de vida, Tier 3 — Pro / Avanzado, Tier 4 — Locuras (+2 more)

### Community 40 - "Community 40"
Cohesion: 0.67
Nodes (3): General usage advice, How to set individual config values, Set post-processing effects

### Community 41 - "Community 41"
Cohesion: 0.67
Nodes (3): Get list of post-processing effects and state, The `postProcessingEffects` array, When is an effect considered "active"?

### Community 42 - "Community 42"
Cohesion: 0.67
Nodes (3): Options for pinning, Pin items to the model, Pinning to a specific position

## Knowledge Gaps
- **160 isolated node(s):** `name`, `version`, `description`, `start`, `test` (+155 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EventOrchestrator` connect `Community 0` to `Community 8`, `Community 4`, `Community 13`?**
  _High betweenness centrality (0.120) - this node is a cross-community bridge._
- **Why does `ColoredFormatter` connect `Community 4` to `Community 0`, `Community 5`, `Community 10`, `Community 53`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `TTSClient` connect `Community 5` to `Community 4`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `EventOrchestrator` (e.g. with `ResponsePipeline` and `PointsManager`) actually correct?**
  _`EventOrchestrator` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `TikTok AI Streamer` (e.g. with `Viewer Leaderboard` and `Plugin System`) actually correct?**
  _`TikTok AI Streamer` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Conecta el pipeline con los servicios disponibles.`, `Extrae emotion/sfx de metadatos en respuesta AI (formato [emotion:happy][sfx:din`, `Ejecuta acciones temporales sin guardarlas como regla.` to the rest of the system?**
  _188 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.0519219736087206 - nodes in this community are weakly interconnected._