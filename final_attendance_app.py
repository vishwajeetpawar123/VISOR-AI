import os
import cv2
import numpy as np
import time
import socket # Restored for Mobile URL display
from datetime import datetime
import threading
import logging
from flask import Flask, render_template_string, jsonify, send_from_directory, request, Response

import csv
import requests # Restore requests for Ollama check

# ==========================================
# CONFIGURATION
# ==========================================
BASE_DIR = os.getcwd() # Force use of current directory for external files
manual_recording_active = False 
frame_buffer = None 
show_local_preview = True 
FACES_DIR = os.path.join(BASE_DIR, "faces")
PHOTOS_DIR = os.path.join(BASE_DIR, "attendance_photos")
LOG_FILE = os.path.join(BASE_DIR, "lobby_log.csv")
NOTES_FILE = os.path.join(BASE_DIR, "student_notes.md")
EXIT_THRESHOLD = 3.0  # Seconds before considering someone "Gone"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"
current_mode = "SURVEILLANCE" # Default Mode

# ==========================================
# PREMIUM "vishwajeet" UI TEMPLATE
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visor AI Attendance</title>
    <style>
        /* STRIPE-INSPIRED THEME */
        :root {
            --stripe-bg: #0a2540;
            --stripe-accent: #635bff; /* Blurple */
            --stripe-success: #00d924;
            --stripe-text: #ffffff;
            --stripe-text-dim: #adbdcc;
            --card-bg: rgba(255, 255, 255, 0.08); /* Glassy */
            --card-border: rgba(255, 255, 255, 0.1);
            --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }

        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

        body {
            font-family: var(--font-family);
            background-color: var(--stripe-bg);
            color: var(--stripe-text);
            margin: 0; padding: 0; min-height: 100vh;
            /* Mesh Gradient Background */
            background-image: 
                radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), 
                radial-gradient(at 50% 0%, hsla(225,39%,30%,1) 0, transparent 50%), 
                radial-gradient(at 100% 0%, hsla(339,49%,30%,1) 0, transparent 50%);
            background-attachment: fixed;
            background-size: cover;
            overflow-x: hidden;
        }

        .container { 
            max-width: 1200px; margin: 0 auto; padding: 20px; 
            display: flex; flex-direction: column; gap: 24px; 
        }

        /* HEADER */
        header {
            display: flex; justify-content: space-between; align-items: center; 
            padding: 10px 0;
            border-bottom: 2px solid rgba(255,255,255,0.05);
        }
        .brand {
            font-size: 1.5rem; font-weight: 800; letter-spacing: -0.5px;
            display: flex; align-items: center; gap: 10px;
        }
        .brand-icon {
            width: 32px; height: 32px; background: var(--stripe-accent);
            border-radius: 8px; display: flex; align-items: center; justify-content: center;
            box-shadow: 0 4px 12px rgba(99, 91, 255, 0.4);
        }
        .status-pill {
            background: rgba(0, 217, 36, 0.15); color: var(--stripe-success);
            padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600;
            border: 1px solid rgba(0, 217, 36, 0.2);
        }

        /* TABS - Pill Design */
        .tabs { 
            display: flex; gap: 8px; overflow-x: auto; padding-bottom: 5px; 
            scrollbar-width: none; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 15px;
        }
        .tabs::-webkit-scrollbar { display: none; }
        .tab-btn {
            background: transparent; color: var(--stripe-text-dim);
            padding: 8px 16px; border-radius: 20px; border: none;
            cursor: pointer; font-size: 0.95rem; font-weight: 500;
            transition: all 0.2s cubic-bezier(0.165, 0.84, 0.44, 1);
            white-space: nowrap;
        }
        .tab-btn:hover { color: #fff; background: rgba(255,255,255,0.05); }
            background: var(--stripe-text); color: var(--stripe-bg); font-weight: 600;
        }
        
        /* REC BUTTON */
        /* REC BUTTON (Redesigned) */
        .rec-btn {
            background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.1); color: var(--stripe-text-dim);
            padding: 8px 16px; border-radius: 20px; cursor: pointer; font-size: 0.85rem; font-weight: 600;
            transition: all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94); outline: none; display: flex; align-items: center; gap: 8px;
        }
        .rec-btn:hover { background: rgba(255,255,255,0.15); color: #fff; }
        
        .rec-btn.active {
            background: #ff4f4f; color: white; border-color: #ff4f4f;
            box-shadow: 0 0 15px rgba(255, 79, 79, 0.6);
            animation: pulse-red 1.5s infinite; font-weight: 700;
        }
        @keyframes pulse-red { 0% { box-shadow: 0 0 0 0 rgba(255, 79, 79, 0.6); transform: scale(1); } 70% { box-shadow: 0 0 0 6px rgba(255, 79, 79, 0); transform: scale(1.02); } 100% { box-shadow: 0 0 0 0 rgba(255, 79, 79, 0); transform: scale(1); } }

        /* LAYOUT */
        /* LAYOUT */
        .main-layout { 
            display: grid; grid-template-columns: 250px 1fr 320px; gap: 24px; 
            height: calc(100vh - 140px); /* Fixed height to force scroll */
            overflow: hidden; 
        }

        /* SETTINGS SIDEBAR */
        .settings-sidebar {
            background: var(--card-bg); backdrop-filter: blur(20px);
            border: 1px solid var(--card-border); border-radius: 16px;
            padding: 20px; display: flex; flex-direction: column; gap: 20px;
            height: 100%; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        }
        .sidebar-title { font-size: 0.9rem; font-weight: 700; color: var(--stripe-text-dim); text-transform: uppercase; margin-bottom: 10px; letter-spacing: 0.5px; }

        /* CARDS & CONTENT */
        .content-area {
            background: var(--card-bg); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--card-border); border-radius: 16px;
            padding: 24px; overflow-y: auto; height: 100%;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        }

        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 16px; }
        
        .card {
            background: rgba(0,0,0,0.2); border-radius: 12px; overflow: hidden;
            border: 1px solid rgba(255,255,255,0.05); cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s; position: relative;
        }
        .card:hover { 
            transform: translateY(-4px); 
            box-shadow: 0 12px 24px rgba(0,0,0,0.2); 
            border-color: rgba(255,255,255,0.15);
        }
        .card:active { transform: scale(0.98); }
        
        .card img { width: 100%; height: 110px; object-fit: cover; display: block; }
        
        .card-body { padding: 12px; }
        .card-name { font-weight: 600; font-size: 0.9rem; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .card-time { font-size: 0.75rem; color: var(--stripe-text-dim); }

        /* LIVE FEED */
        .live-container { 
            display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;
        }
        .live-feed-img {
            max-width: 100%; max-height: 500px; border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1);
        }

        /* CHAT SIDEBAR */
        /* CHAT SIDEBAR */
        .chat-section {
            background: var(--card-bg); backdrop-filter: blur(20px);
            border: 1px solid var(--card-border); border-radius: 16px;
            display: flex; flex-direction: column; overflow: hidden;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
            height: 100%; /* Force height to fill grid, enabling scroll */
        }
        
        /* CUSTOM SCROLLBAR */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.4); }
        .chat-header {
            padding: 16px; background: rgba(0,0,0,0.2); font-weight: 600; font-size: 0.95rem;
            display: flex; align-items: center; gap: 8px; border-bottom: 1px solid var(--card-border);
        }
        .chat-messages { flex: 1; padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
        
        .message { padding: 10px 14px; border-radius: 12px; font-size: 0.9rem; line-height: 1.5; max-width: 85%; }
        .msg-ai { background: rgba(255,255,255,0.1); color: #fff; align-self: flex-start; border-bottom-left-radius: 2px; }
        .msg-user { background: var(--stripe-accent); color: #fff; align-self: flex-end; border-bottom-right-radius: 2px; box-shadow: 0 4px 12px rgba(99, 91, 255, 0.3); }
        
        .chat-input-area { padding: 16px; background: rgba(0,0,0,0.2); border-top: 1px solid var(--card-border); }
        .chat-input {
            width: 100%; background: rgba(255,255,255,0.1); border: 1px solid transparent;
            padding: 12px 16px; border-radius: 8px; color: #fff; outline: none; transition: 0.2s;
        }
        .chat-input:focus { background: rgba(255,255,255,0.15); border-color: rgba(255,255,255,0.2); }
        .chat-input::placeholder { color: rgba(255,255,255,0.3); }

        /* TYPING ANIMATION */
        .typing { display: flex; gap: 4px; padding: 12px 16px; background: rgba(255,255,255,0.1); border-radius: 12px; align-self: flex-start; border-bottom-left-radius: 2px; width: fit-content; }
        .dot { width: 6px; height: 6px; background: #fff; border-radius: 50%; opacity: 0.6; animation: bounce 1.4s infinite ease-in-out both; }
        .dot:nth-child(1) { animation-delay: -0.32s; }
        .dot:nth-child(2) { animation-delay: -0.16s; }
        @keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }

        /* TABLES & FORMS */
        .data-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        .data-table th { text-align: left; padding: 12px; color: var(--stripe-text-dim); border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 0.8rem; text-transform: uppercase; }
        .data-table td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9rem; }
        .data-table tr:hover td { background: rgba(255,255,255,0.02); }
        .status-badge { padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
        .badge-green { background: rgba(0, 217, 36, 0.2); color: #00d924; }
        .badge-red { background: rgba(255, 79, 79, 0.2); color: #ff4f4f; }
        
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; margin-bottom: 8px; color: var(--stripe-text-dim); font-size: 0.9rem; }
        .form-control { 
            width: 100%; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); 
            padding: 10px; border-radius: 8px; color: #fff; font-family: inherit; font-size: 1rem;
        }
        .form-control:focus { border-color: var(--stripe-accent); outline: none; }
        .btn-primary {
            background: var(--stripe-accent); color: white; border: none; padding: 10px 20px; border-radius: 8px;
            font-weight: 600; cursor: pointer; transition: 0.2s;
        }
        .btn-primary:hover { filter: brightness(1.1); }
        
        /* TOGGLE SWITCH */
        .switch { position: relative; display: inline-block; width: 44px; height: 24px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(255,255,255,0.1); transition: .4s; border-radius: 24px; }
        .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }
        input:checked + .slider { background-color: var(--stripe-accent); }
        input:checked + .slider:before { transform: translateX(20px); }

        /* RESPONSIVE */
        @media (max-width: 900px) {
            .container { padding: 15px; gap: 15px; }
            /* Reset fixed height to allow scrolling on mobile */
            .main-layout { 
                grid-template-columns: 1fr; 
                display: flex; flex-direction: column; 
                height: auto; 
                overflow: visible; 
            }
            .content-area { 
                height: auto; 
                min-height: 40vh; 
                max-height: 75vh; /* Limit height to prevent infinite scrolling on page */
                padding: 16px; 
                overflow-y: auto; /* Internal scrollbar */
            }
            .chat-section { height: 600px; } /* Fixed height for chat on mobile */
            .settings-sidebar { height: auto; }
            .grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
        }
    </style>
</head>
<body>

<div class="container">
    <header>
        <div class="brand">
            <div class="brand-icon">V</div>
            Visor AI
        </div>
        <div style="display:flex; align-items:center; gap:12px">
            <div class="status-pill">● AI Online</div>
        </div>
    </header>

    <div class="tabs">
        <button class="tab-btn active" onclick="switchTab('live')">🔴 Live Feed</button>
        <button class="tab-btn" onclick="switchTab('logs')">📋 Logs</button>
        <button class="tab-btn" onclick="switchTab('photos')">🖼️ Photos</button>
        <button class="tab-btn" onclick="switchTab('recordings')">🎥 Recordings</button>
        <button class="tab-btn" onclick="switchTab('notes')">📝 Notes</button>
        <!-- Settings removed from tabs -->
    </div>
    
    <div style="display:flex; gap:10px; align-items:center">
        <button id="rec-btn" class="rec-btn" onclick="toggleRecording()">● REC</button>
    </div>

    <div class="main-layout">
        <!-- LEFT SIDEBAR: SETTINGS -->
        <aside class="settings-sidebar">
            <div>
                <div class="sidebar-title">System Control</div>
                <div class="form-group">
                    <label class="form-label">Mode</label>
                    <select id="set-mode" class="form-control" onchange="saveSettings()">
                        <option value="SURVEILLANCE">Surveillance</option>
                        <option value="ATTENDANCE">Attendance</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Lobby Timeout (s)</label>
                    <input type="number" step="0.5" id="set-threshold" class="form-control" onchange="saveSettings()">
                </div>
                <div class="form-group" style="display:flex; justify-content:space-between; align-items:center">
                    <label class="form-label" style="margin:0">Preview Window</label>
                    <label class="switch">
                        <input type="checkbox" id="set-preview" onchange="saveSettings()">
                        <span class="slider"></span>
                    </label>
                </div>
            </div>
            
            <div style="margin-top:auto; padding-top:20px; border-top:1px solid rgba(255,255,255,0.1)">
                <div class="sidebar-title">Server Status</div>
                <div style="font-size:0.85rem; color:var(--stripe-text-dim); line-height:1.6">
                    <div id="status-mode">Mode: Loading...</div>
                    <div id="status-ollama">AI Model: Checking...</div>
                </div>
            </div>
        </aside>

        <!-- CENTER: CONTENT -->
        <main class="content-area">
            <div id="main-content">
                <!-- Dynamic Content -->
            </div>
        </main>

        <aside class="chat-section">
            <div class="chat-header">
                <div>AI Assistant</div>
            </div>
            <div class="chat-messages" id="chat-box">
                <div class="message msg-ai">Hello! Visor system ready.</div>
            </div>
            <div class="chat-input-area">
                <input type="text" id="user-input" class="chat-input" placeholder="Ask anything..." autocomplete="off">
            </div>
        </aside>
    </div>
</div>

<script>
    const contentDiv = document.getElementById('main-content');
    let currentTab = 'live';
    let currentLogPage = 1;
    const LOGS_PER_PAGE = 12;
    let cachedLogs = []; // Store logs to avoid re-fetching on page change

    function switchTab(tab) {
        currentTab = tab;
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelector(`button[onclick="switchTab('${tab}')"]`).classList.add('active');
        render();
    }

    async function render() {
        if(currentTab === 'live') {
            contentDiv.innerHTML = `
                <div class="live-container">
                    <img src="/video_feed" class="live-feed-img" alt="Live Stream">
                    <p style="margin-top:15px; color:var(--stripe-text-dim)">Real-time Surveillance Feed (MJPEG)</p>
                </div>`;
        } else if(currentTab === 'logs') {
            renderLogs();
        } else if(currentTab === 'logs') {
            renderLogs();
        } else if(currentTab === 'notes') {
            renderNotes();
        } else if(currentTab === 'photos') {
            try {
                const res = await fetch('/api/photos');
                const data = await res.json();
                if(data.length === 0) {
                     contentDiv.innerHTML = '<div style="padding:20px; color:var(--stripe-text-dim)">No photos found.</div>';
                     return;
                }
                contentDiv.innerHTML = '<div class="grid">' + data.map(p => `
                    <div class="card" onclick="window.open('${p.url}', '_blank')">
                        <img src="${p.url}" loading="lazy">
                        <div class="card-body">
                            <div class="card-name">${p.name}</div>
                            <div style="font-size:0.75rem; color:#aaa; margin-top:4px">${p.timestamp}</div>
                        </div>
                    </div>`).join('') + '</div>';
            } catch(e) { contentDiv.innerHTML = 'Error loading photos'; }
        } else if(currentTab === 'recordings') {
            try {
                const res = await fetch('/api/videos');
                const files = await res.json();
                if(files.length === 0) {
                     contentDiv.innerHTML = '<div style="padding:20px; color:var(--stripe-text-dim)">No recordings found.</div>';
                     return;
                }
                contentDiv.innerHTML = '<div class="grid">' + files.map(f => `
                    <div class="card" style="cursor:default">
                        <div style="height:120px; background:rgba(0,0,0,0.3); display:flex; flex-direction:column; align-items:center; justify-content:center; gap:10px">
                            <a href="/recordings/${f}" download class="tab-btn" style="text-decoration:none; background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.2); font-size:0.8rem">⬇ Download</a>
                        </div>
                        <div class="card-body">
                            <div class="card-name" style="font-size:0.85rem">${f}</div>
                        </div>
                    </div>`).join('') + '</div>';
            } catch(e) { contentDiv.innerHTML = 'Error loading videos'; }
        }
    }

    async function renderLogs() {
        // Fetch only if not cached or forcing refresh (we'll just re-fetch for simplicity/live updates)
        const res = await fetch('/api/logs');
        cachedLogs = await res.json();
        updateLogsTable();
    }

    function updateLogsTable() {
        const totalPages = Math.ceil(cachedLogs.length / LOGS_PER_PAGE);
        if (currentLogPage > totalPages) currentLogPage = totalPages;
        if (currentLogPage < 1) currentLogPage = 1;
        
        const start = (currentLogPage - 1) * LOGS_PER_PAGE;
        const end = start + LOGS_PER_PAGE;
        const pageItems = cachedLogs.slice(start, end);
        
        let html = `<h3>Activity Log</h3>
        <table class="data-table">
            <thead><tr><th>Time</th><th>Event</th><th>Name</th><th>Verification</th></tr></thead>
            <tbody>`;
            
        pageItems.forEach(row => {
            const badgeClass = row.Event === 'ENTERED' ? 'badge-green' : 'badge-red';
            html += `<tr>
                <td>${row.Timestamp.split(' ')[1]} ${row.Timestamp.split(' ')[2]}</td>
                <td><span class="status-badge ${badgeClass}">${row.Event}</span></td>
                <td style="font-weight:600">${row.Name}</td>
                <td>${row.PhotoPath ? `<a href="/photos/${row.PhotoPath.split('/').pop()}" target="_blank" style="color:var(--stripe-accent)">View Photo</a>` : '-'}</td>
            </tr>`;
        });
        html += `</tbody></table>`;
        
        // Pagnation Controls
        html += `<div style="display:flex; justify-content:center; align-items:center; gap:15px; margin-top:20px;">
            <button class="tab-btn" onclick="changeLogPage(-1)" ${currentLogPage===1?'disabled style="opacity:0.5"':''}>◀ Prev</button>
            <span style="color:var(--stripe-text-dim); font-size:0.9rem">Page ${currentLogPage} of ${totalPages || 1}</span>
            <button class="tab-btn" onclick="changeLogPage(1)" ${currentLogPage>=totalPages?'disabled style="opacity:0.5"':''}>Next ▶</button>
        </div>`;
        
        contentDiv.innerHTML = html;
    }

    function changeLogPage(delta) {
        currentLogPage += delta;
        updateLogsTable();
    }

    async function renderNotes() {
        // Fetch current notes
        const res = await fetch('/api/notes');
        const data = await res.json();
        
        contentDiv.innerHTML = `
            <h3>Student Notes - AI assistant refers these.</h3>
            <div class="card" style="height:65vh; display:flex; flex-direction:column;">
                <div class="card-body" style="flex:1; display:flex; flex-direction:column; padding:0;">
                    <textarea id="notes-area" class="form-control" style="flex:1; background:transparent; border:none; resize:none; font-family:monospace; line-height:1.6; padding:20px;" disabled>${data.content}</textarea>
                </div>
                <div style="padding:15px; border-top:1px solid rgba(255,255,255,0.1); display:flex; justify-content:flex-end; gap:10px; background:rgba(0,0,0,0.2)">
                    <button id="btn-edit-notes" class="tab-btn" onclick="toggleNotesEdit()" style="background:var(--stripe-accent); color:white">✏️ Edit</button>
                    <button id="btn-save-notes" class="tab-btn" onclick="saveNotes()" style="background:var(--stripe-success); color:white; display:none">💾 Save</button>
                    <button id="btn-cancel-notes" class="tab-btn" onclick="renderNotes()" style="background:rgba(255,255,255,0.1); display:none">❌ Cancel</button>
                </div>
            </div>
        `;
    }

    function toggleNotesEdit() {
        const area = document.getElementById('notes-area');
        const btnEdit = document.getElementById('btn-edit-notes');
        const btnSave = document.getElementById('btn-save-notes');
        const btnCancel = document.getElementById('btn-cancel-notes');
        
        area.disabled = false;
        area.focus();
        area.style.background = "rgba(0,0,0,0.2)"; // Visual cue
        
        btnEdit.style.display = 'none';
        btnSave.style.display = 'block';
        btnCancel.style.display = 'block';
    }

    async function saveNotes() {
        const content = document.getElementById('notes-area').value;
        await fetch('/api/notes', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ content: content })
        });
        alert("Notes Saved!");
        renderNotes(); // Re-render to lock
    }

    async function loadSettingsToSidebar() {
        const res = await fetch('/api/settings');
        const settings = await res.json();
        
        document.getElementById('set-mode').value = settings.mode;
        document.getElementById('set-threshold').value = settings.exit_threshold;
        document.getElementById('set-preview').checked = settings.show_preview;
        document.getElementById('status-mode').innerText = "Mode: " + settings.mode;
    }

    async function saveSettings() {
        // Auto-save on change
        const mode = document.getElementById('set-mode').value;
        const threshold = document.getElementById('set-threshold').value;
        const preview = document.getElementById('set-preview').checked;
        
        // Optimistic UI update
        document.getElementById('status-mode').innerText = "Mode: " + mode;

        await fetch('/api/settings', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ mode: mode, exit_threshold: threshold, show_preview: preview })
        });
        // No alert needed for auto-save, feels smoother
    }

    // Chat Logic
    const chatBox = document.getElementById('chat-box');
    const input = document.getElementById('user-input');
    
    input.addEventListener('keypress', async (e) => {
        if(e.key === 'Enter' && input.value.trim()) {
            const txt = input.value.trim();
            input.value = '';
            chatBox.innerHTML += `<div class="message msg-user">${txt}</div>`;
            chatBox.scrollTop = chatBox.scrollHeight;
            
            // Add Loading Indicator
            const loadingId = 'loading-' + Date.now();
            chatBox.innerHTML += `
                <div class="typing" id="${loadingId}">
                    <div class="dot"></div><div class="dot"></div><div class="dot"></div>
                </div>`;
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                const res = await fetch('/api/chat', {
                    method:'POST', headers:{'Content-Type':'application/json'},
                    body: JSON.stringify({message: txt})
                });
                const data = await res.json();
                
                // Remove Loading
                document.getElementById(loadingId).remove();
                
                chatBox.innerHTML += `<div class="message msg-ai">${data.reply}</div>`;
                chatBox.scrollTop = chatBox.scrollHeight;
            } catch(e) {
                // Remove Loading on error
                const loader = document.getElementById(loadingId);
                if(loader) loader.remove();
                chatBox.innerHTML += `<div class="message msg-ai" style="color:#ff4f4f">Connection Error.</div>`;
            }
        }
    });

    // Start
    render();
    
    // RECORDING LOGIC
    async function toggleRecording() {
        const res = await fetch('/api/record', {method:'POST'});
        const data = await res.json();
        updateRecBtn(data.status);
    }
    function updateRecBtn(active) {
        const btn = document.getElementById('rec-btn');
        if(active) {
            btn.classList.add('active');
            btn.innerText = '⏹ STOP';
        } else {
            btn.classList.remove('active');
            btn.innerText = '● REC';
        }
    }
    // Check initial status
    fetch('/api/status').then(r=>r.json()).then(d=> {
        updateRecBtn(d.recording);
        document.getElementById('status-ollama').innerText = "AI Model: " + (d.ollama_online ? "Online 🟢" : "Offline 🔴");
    });
    
    // Load Settings into Sidebar
    loadSettingsToSidebar();
    
    setInterval(() => { if(currentTab === 'logs') renderLogs(); }, 3000); // Auto refresh Logs only
</script>
</body>
</html>
"""

# ==========================================
# WEB SERVER SETUP
# ==========================================
app = Flask(__name__)
# Suppress Flask server logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/api/record', methods=['POST'])
def toggle_record():
    global manual_recording_active
    manual_recording_active = not manual_recording_active
    return jsonify({'status': manual_recording_active})

@app.route('/api/status')
def server_status():
    # Check Ollama
    is_online = False
    try:
        if requests.get("http://localhost:11434/", timeout=0.2).status_code == 200:
            is_online = True
    except: pass
    
    return jsonify({
        'recording': manual_recording_active,
        'ollama_online': is_online
    })

@app.route('/api/logs')
def get_logs_json():
    """Returns parsed CSV logs as JSON."""
    if not os.path.exists(LOG_FILE): return jsonify([])
    try:
        entries = []
        with open(LOG_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append(row)
        return jsonify(entries[-500:][::-1]) # Return last 500, reversed
    except: return jsonify([])

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    global EXIT_THRESHOLD, show_local_preview, manual_recording_active, current_mode
    
    if request.method == 'POST':
        data = request.json
        if 'exit_threshold' in data: EXIT_THRESHOLD = float(data['exit_threshold'])
        if 'show_preview' in data: show_local_preview = bool(data['show_preview'])
        if 'mode' in data: 
            # Safe mode switch
            if data['mode'] in ['SURVEILLANCE', 'ATTENDANCE']:
                pass
            current_mode = data['mode']
            
        return jsonify({'status': 'ok', 'mode': current_mode})
        
    return jsonify({
        'exit_threshold': EXIT_THRESHOLD,
        'show_preview': show_local_preview,
        'mode': current_mode
    })

@app.route('/api/notes', methods=['GET', 'POST'])
def api_notes():
    if request.method == 'POST':
        data = request.json
        with open(NOTES_FILE, 'w', encoding='utf-8') as f:
            f.write(data.get('content', ''))
        return jsonify({'status': 'ok'})
    else:
        content = ""
        if os.path.exists(NOTES_FILE):
            with open(NOTES_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
        return jsonify({'content': content})

def get_logs_context():
    """Reads the CSV logs and returns them as a string context."""
    if not os.path.exists(LOG_FILE):
        return "No logs available."
    
    try:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
            
        # User requested FULL history context
        # Sending all lines to the AI
        context = "".join(lines)
        return context
    except Exception as e:
        return f"Error reading logs: {str(e)}"

def get_notes_context():
    """Reads the student notes file and returns content."""
    if not os.path.exists(NOTES_FILE):
        return "No specific student notes available."
    
    try:
        with open(NOTES_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading notes: {str(e)}"

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# Removed duplicate /api/status endpoint to fix collision

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_frames():
    """Generator for MJPEG stream from the global `frame` variable."""
    global frame_buffer
    while True:
        # We need to access the latest frame. 
        # In a real multiprocessing app, we'd use a shared Queue or Value.
        # But here, we can actually serve this directly if we run Flask in a thread share.
        # Wait, `multiprocessing` creates a separate memory space!
        # The Flask process CANNOT see the main process `frame` variable directly.
        # FIX: We must use a Manager or Queue to pass frames.
        # SIMPLIFICATION for V2.5: 
        # We will switch Flask to run in a THREAD, not a Process, OR use proper IPC.
        # Given "Ultra-Lite" goal, threading is LIGHTER than multiprocessing.
        # Let's Switch to Threading for the server!
        if frame_buffer is None:
            time.sleep(0.1)
            continue
            
        try:
            ret, buffer = cv2.imencode('.jpg', frame_buffer)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception:
            pass
        time.sleep(0.04) # Limit to ~25 FPS stream

@app.route('/api/videos')
def get_videos():
    rec_dir = os.path.join(BASE_DIR, "recordings")
    if not os.path.exists(rec_dir):
        return jsonify([])
    
    files = [f for f in os.listdir(rec_dir) if f.endswith('.mp4')]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(rec_dir, x)), reverse=True)
    return jsonify(files)

@app.route('/recordings/<path:filename>')
def serve_video(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'recordings'), filename)

@app.route('/photos/<path:filename>')
def serve_photo(filename):
    return send_from_directory(PHOTOS_DIR, filename)

@app.route('/api/photos')
def get_photos():
    if not os.path.exists(PHOTOS_DIR):
        return jsonify([])

    files = [f for f in os.listdir(PHOTOS_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(PHOTOS_DIR, x)), reverse=True)
    
    photo_data = []
    for filename in files:
        parts = filename.split('_')
        display_name = "Unknown"
        
        # Attendance_Name_Date_Time.jpg
        # Safe heuristic for naming
        if len(parts) >= 3 and parts[0] == "Attendance":
             # Re-assemble name parts (vishwajeet_pawar -> vishwajeet pawar)
             name_parts = parts[1:-2]
             display_name = " ".join(name_parts)
        
        filepath = os.path.join(PHOTOS_DIR, filename)
        mod_time = os.path.getmtime(filepath)
        dt = datetime.fromtimestamp(mod_time)
        timestamp_display = dt.strftime("%Y-%m-%d %I:%M:%S %p")

        photo_data.append({
            'filename': filename,
            'name': display_name,
            'timestamp': timestamp_display,
            'url': f'/photos/{filename}'
        })
        
    return jsonify(photo_data)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_msg = data.get('message', '')
    
    # 1. Prepare Context
    logs = get_logs_context()
    notes = get_notes_context()
    
    # 2. Build Prompt
    current_time_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    
    system_prompt = (
        f"Current System Time: {current_time_str}\\n"
        "You are 'Visor', a helpful and friendly AI assistant. You have access to attendance logs and specific student notes.\\n"
        "CSV Structure: Timestamp, Event (ENTERED/EXITED), Name, PhotoPath\\n"
        "Data is standard CSV format with headers.\\n\\n"
        "--- START STUDENT NOTES ---\\n"
        f"{notes}\\n"
        "--- END STUDENT NOTES ---\\n\\n"
        "--- START LOGS ---\\n"
        f"{logs}\\n"
        "--- END LOGS ---\\n\\n"
        f"User Question: {user_msg}\\n\\n"
        "Instructions:\\n"
        "1. **Persona**: You are Visor. Be helpful, friendly, and natural.\\n"
        "2. **Context Aware**: Use the 'Student Notes' to provide personalized context (e.g., if a student dislikes classes).\\n"
        "3. **Attendance Checks**: If the user asks about attendance, use the CSV logs to answer factually.\\n"
        "4. **General Chat**: If the user asks about general topics (life, weather, code, etc.), feel free to chat naturally. You are NOT restricted to only talking about attendance.\\n"
        "5. **Honesty**: If you don't know something, just say so."


    )
    
    # 3. Call Ollama
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.4, # Lower temperature for more factual answers
            "num_mid_ctx": 2048
        }
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=90)
        if response.status_code == 200:
            ai_reply = response.json().get('response', 'Error parsing AI response.')
            return jsonify({'reply': ai_reply})
        else:
            return jsonify({'reply': f"Ollama Error: {response.status_code}"})
    except requests.exceptions.ConnectionError:
        return jsonify({'reply': "Error: Ollama is offline."})
    except Exception as e:
        return jsonify({'reply': f"Server Error: {str(e)}"})



def run_flask_app():
    # Helper to find IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    
    print("-" * 50)
    print(f"NEXUS SERVER STARTED")
    print(f" * UI Address:   http://localhost:5000")
    print(f" * Mobile URL:   http://{IP}:5000")
    print("-" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# ==========================================
# FACE RECOGNITION SYSTEM
# ==========================================
def log_event(event, name, frame=None):
    now_obj = datetime.now()
    now_str = now_obj.strftime("%Y-%m-%d %I:%M:%S %p")
    photo_filename = ""
    
    # If this is an ENTRY event, save a photo
    if event == "ENTERED" and frame is not None:
        # Create a safe filename
        safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '_')]).strip()
        timestamp_for_file = now_obj.strftime("%Y%m%d_%H%M%S")
        photo_filename = f"{PHOTOS_DIR}/Attendance_{safe_name}_{timestamp_for_file}.jpg"
        
        # Draw timestamp on the photo itself for "hardcopy" proof
        evidence_frame = frame.copy()
        # Text at Top-Right to avoid overlap
        h, w = evidence_frame.shape[:2]
        cv2.putText(evidence_frame, f"{now_str} - {name}", (w - 340, 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        cv2.imwrite(photo_filename, evidence_frame)
        print(f"SNAPSHOT SAVED: {photo_filename}")

    print(f"LOG: {event} - {name} at {now_str}")
    
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Event", "Name", "PhotoPath"])
        writer.writerow([now_str, event, name, photo_filename])

def run_face_recognition_loop():
    global frame_buffer
    global manual_recording_active
    global show_local_preview
    global current_mode # Needed for API to update it
    global EXIT_THRESHOLD

    # Load Models
    face_cascade_path = "models/haarcascade_frontalface_default.xml"
    # face_cascade = cv2.CascadeClassifier(face_cascade_path)

    # 1. Setup Directories
    if not os.path.exists(PHOTOS_DIR):
        os.makedirs(PHOTOS_DIR)
    
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Event", "Name", "PhotoPath"])
            
    if not os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, "w", encoding='utf-8') as f:
            f.write("# Student Notes\n# Add notes about students here.\n")

    # 2. Setup Video
    video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        print("ERROR: Could not access the camera.")
        return

    # Set resolution
    frame_width = 640
    frame_height = 480
    video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    # ==========================================
    # INITIALIZATION
    # ==========================================
    import pickle
    import threading
    import pyttsx3
    
    # --- VOICE ENGINE ---
    def speak_text(text):
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 150) # Speed
            engine.say(text)
            engine.runAndWait()
        except:
            pass

    def speak(text):
        # Run in thread to not block video
        threading.Thread(target=speak_text, args=(text,), daemon=True).start()

    # --- IMAGE ENHANCEMENT (Night Vision) ---
    def adjust_gamma(image, gamma=1.0):
        # Build a lookup table mapping the pixel values [0, 255] to their adjusted gamma values
        invGamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** invGamma) * 255
            for i in np.arange(0, 256)]).astype("uint8")
        # Apply gamma correction using the lookup table
        return cv2.LUT(image, table)

    # --- MODELS ---
    model_dir = "models"
    detector_path = os.path.join(model_dir, "face_detection_yunet_2023mar.onnx")
    recognizer_path = os.path.join(model_dir, "face_recognition_sface_2021dec.onnx")
    encodings_path = "face_encodings_sface.pkl"
    # Eye Cascade for Blink
    eye_cascade_path = os.path.join(model_dir, 'haarcascade_eye_tree_eyeglasses.xml')
    eye_detector = cv2.CascadeClassifier(eye_cascade_path)
    
    if not os.path.exists(detector_path) or not os.path.exists(recognizer_path):
        print("CRITICAL ERROR: ONNX Models not found. Please run 'download_models.py'.")
        return

    # 1. Initialize Detector (YuNet) - Ultra Lite 320x240
    # LOWERED THRESHOLD from 0.9 to 0.6 for better dark detection
    det_w, det_h = 320, 240
    detector = cv2.FaceDetectorYN.create(
        detector_path, "", (det_w, det_h), 0.6, 0.3, 5000
    )
    
    # 2. Initialize Recognizer (SFace)
    recognizer = cv2.FaceRecognizerSF.create(recognizer_path, "")
    
    # 3. Load Known Faces
    known_faces = {}
    if os.path.exists(encodings_path):
        with open(encodings_path, 'rb') as f:
            known_faces = pickle.load(f)
        print(f"✅ Loaded {len(known_faces)} faces from fast cache.")
    else:
        print("⚠️ No face cache found. Please run 'reencode_faces.py'.")

    # --- STATE MANGEMENT ---
    present_people = {} 
    
    # MODES: "SURVEILLANCE" (Silent, No Blink) vs "ATTENDANCE" (Voice, Blink Required)
    current_mode = "SURVEILLANCE" 
    
    # --- RECORDING SETUP ---
    RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")
    if not os.path.exists(RECORDINGS_DIR):
        os.makedirs(RECORDINGS_DIR)
        
    video_writer = None
    
    def start_recording(width, height):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(RECORDINGS_DIR, f"Surveillance_{timestamp}.mp4")
        
        # Try 1: H.264 (avc1) - BEST FOR WEB
        fourcc = cv2.VideoWriter_fourcc(*'avc1') 
        writer = cv2.VideoWriter(filename, fourcc, 20.0, (width, height))
        
        if not writer.isOpened():
            print("⚠️ H.264 failed. Trying MP4V (Windows Default)...")
            writer.release()
            # Try 2: MPEG-4 (mp4v) - Robust fallback (but may not play in browser)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(filename, fourcc, 20.0, (width, height))
            
            if not writer.isOpened():
                 print("⚠️ MP4V failed. Trying VP9 (vp09)...")
                 writer.release()
                 # Try 3: VP9
                 fourcc = cv2.VideoWriter_fourcc(*'vp09') # or vp80
                 writer = cv2.VideoWriter(filename, fourcc, 20.0, (width, height))

        print(f"🔴 RECORDING STARTED: {filename}")
        return writer

    def stop_recording(writer):
        if writer is not None:
            writer.release()
            print("⏹️ RECORDING STOPPED.")
        return None

    # Auto-start recording REMOVED (Manual Only)

    # ATTENDANCE STATE MACHINE
    # States: "SEARCHING", "DETECTED", "WAITING_BLINK", "RECOGNIZING", "COOLDOWN"
    attn_state = "SEARCHING"
    state_timer = 0
    blink_counter = 0 # Tracks closed eyes
    target_face_box = None # storing face to track for blink
    
    print("Starting Visor (Dual Mode with Night Vision)...")
    print(" [M] Toggle Mode (Surveillance <-> Attendance)")
    print(" [Q] Quit")
    print(" SERVER: http://localhost:5000 (Running)")

    server_process = None
    COSINE_THRESHOLD = 0.45 
    frame_count = 0
    detected_results = [] 
    night_vision_active = False
    
    # Recording Segment Tracking
    recording_start_time = time.time()
    SEGMENT_DURATION = 600 

    while True:
        ret, frame = video_capture.read()
        if not ret:
            break
        
        current_time_loop = time.time()
        
        # --- 0. ADAPTIVE NIGHT VISION (EARLY PASS) ---
        # We check every frame (fast enough on resize) or keep state
        if frame_count % 6 == 0:
            small_check = cv2.resize(frame, (320, 240))
            avg_brightness = np.mean(small_check)
            if avg_brightness < 90: # Slightly lower threshold to avoid flickering
                night_vision_active = True
            elif avg_brightness > 110: # Hysteresis
                night_vision_active = False

        if night_vision_active:
            # Apply to MAIN frame so everything (Recording, Web, Display) sees it
            frame = adjust_gamma(frame, 1.7) # Stronger Gamma
        
        # --- LOBBY LOGIC (EXIT TRACKING) ---
        # If person not seen for 3 seconds -> Exited
        to_remove = []
        for p_name, last_seen in present_people.items():
            if (current_time_loop - last_seen) > 3.0:
                log_event("EXITED", p_name, frame)
                to_remove.append(p_name)
        
        for p_name in to_remove:
            del present_people[p_name]

        # --- TIMESTAMP OVERLAY ---
        # Add Ticking Date/Time (Minimal Space)
        ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Bottom-left corner, small font
        cv2.putText(frame, ts_str, (10, frame_height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # Share frame with Flask Thread (now includes Night Vision)
        frame_buffer = frame.copy()
            
        # Draw Mode UI
        mode_color = (0, 255, 255) if current_mode == "SURVEILLANCE" else (0, 165, 255) # Yellow vs Orange
        cv2.putText(frame, f"MODE: {current_mode}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, mode_color, 2)
        
        # Draw Recording Indicator
        if video_writer is not None:
            # Flashing Red Dot
            if int(current_time_loop * 2) % 2 == 0:
                cv2.circle(frame, (frame_width - 30, 30), 10, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (frame_width - 65, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
        # Draw Night Vision Indicator (Always visible if active)
        if night_vision_active:
            cv2.putText(frame, "NIGHT VISION", (frame_width - 130, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
            # --- CHUNKING LOGIC ---
            # If recording for > 10 minutes, restart to save file
            if (current_time_loop - recording_start_time) > SEGMENT_DURATION:
                print("🔄 Segement Limit Reached. Starting new chunk...")
                video_writer = stop_recording(video_writer)
                video_writer = start_recording(frame_width, frame_height)
                recording_start_time = current_time_loop
        else:
             # If NOT recording, should we start?
             if manual_recording_active and video_writer is None:
                 video_writer = start_recording(frame_width, frame_height)
                 recording_start_time = current_time_loop
        
        # If recording is active but Manual Flag is FALSE -> Stop
        if not manual_recording_active and video_writer is not None:
             video_writer = stop_recording(video_writer)
             video_writer = None

        # ---------------------------------------------------------
        # MODE 1: SURVEILLANCE (PASSIVE LOGGING)
        # ---------------------------------------------------------
        if current_mode == "SURVEILLANCE":
            # Run Ultra-Lite Detection (Every 6th frame)
            if frame_count % 6 == 0:
                small_frame = cv2.resize(frame, (det_w, det_h))
                
                # (Night Vision already applied to 'frame', so small_frame inherits it)
                
                faces_check = detector.detect(small_frame)
                status = faces_check[0] if faces_check is not None else 0
                faces_data = faces_check[1] if (faces_check is not None and len(faces_check) > 1) else None
                
                detected_results = []
                if status and faces_data is not None:
                    for face in faces_data:
                        box_small = list(map(int, face[:4]))
                        
                        # Use the BRIGHT frame (which is just 'frame' now) for alignment
                        aligned_face = recognizer.alignCrop(small_frame, face)
                        face_feature = recognizer.feature(aligned_face)
                        
                        best_name = "Unknown"
                        max_score = 0.0
                        for name, known_feature in known_faces.items():
                            sim_score = recognizer.match(face_feature, known_feature, cv2.FaceRecognizerSF_FR_COSINE)
                            if sim_score > max_score and sim_score > COSINE_THRESHOLD:
                                max_score = sim_score
                                best_name = name
                        
                        # Scale box
                        scale_x = frame_width / det_w
                        scale_y = frame_height / det_h
                        real_box = [int(box_small[0]*scale_x), int(box_small[1]*scale_y), int(box_small[2]*scale_x), int(box_small[3]*scale_y)]
                        detected_results.append((real_box, best_name, max_score))
                        
                        # Log immediately in surveillance mode
                        if best_name != "Unknown":
                            now_ts = time.time()
                            if best_name not in present_people: # First time seeing them
                                log_event("ENTERED", best_name, frame)
                            
                            # Always update heartbeat so they don't timeout in Lobby logic
                            present_people[best_name] = now_ts

        # ---------------------------------------------------------
        # MODE 2: ATTENDANCE (ACTIVE BLINK + VOICE)
        # ---------------------------------------------------------
        else: # ATTENDANCE MODE
            # We run detection more often for responsiveness (Every 3rd frame)
            if frame_count % 3 == 0:
                small_frame = cv2.resize(frame, (det_w, det_h))
                faces_check = detector.detect(small_frame)
                status = faces_check[0] if faces_check is not None else 0
                faces_data = faces_check[1] if (faces_check is not None and len(faces_check) > 1) else None
                
                # Logic Flow
                current_time = time.time()
                
                if attn_state == "SEARCHING":
                    detected_results = [] # Clear visualization
                    if status and faces_data is not None:
                        # Pick the largest face (closest person)
                        primary_face = max(faces_data, key=lambda f: f[2] * f[3]) 
                        attn_state = "DETECTED"
                        state_timer = current_time
                        
                        # Store face data for next steps
                        target_face_data = primary_face
                        
                        # Visualization
                        box_small = list(map(int, primary_face[:4]))
                        scale_x = frame_width / det_w
                        scale_y = frame_height / det_h
                        real_box = [int(box_small[0]*scale_x), int(box_small[1]*scale_y), int(box_small[2]*scale_x), int(box_small[3]*scale_y)]
                        detected_results = [(real_box, "Please Blink", 0.0)]

                elif attn_state == "DETECTED":
                    # Wait 1.0 second to ensure it's a stable face
                    if (current_time - state_timer) > 1.0:
                        speak("Please blink to register")
                        attn_state = "WAITING_BLINK"
                        state_timer = current_time # Reset timer for timeout
                    
                    # Update tracking of face
                    if status and faces_data is not None:
                        primary_face = max(faces_data, key=lambda f: f[2] * f[3])
                        target_face_data = primary_face
                        # Vis update
                        box_small = list(map(int, primary_face[:4]))
                        scale_x = frame_width / det_w
                        scale_y = frame_height / det_h
                        real_box = [int(box_small[0]*scale_x), int(box_small[1]*scale_y), int(box_small[2]*scale_x), int(box_small[3]*scale_y)]
                        detected_results = [(real_box, "Waiting...", 0.0)]
                    else:
                        attn_state = "SEARCHING" # Lost face

                elif attn_state == "WAITING_BLINK":
                    # Timeout check (8s)
                    if (current_time - state_timer) > 8.0:
                        attn_state = "SEARCHING"
                    
                    if status and faces_data is not None:
                        primary_face = max(faces_data, key=lambda f: f[2] * f[3])
                        target_face_data = primary_face
                        
                        # --- BLINK DETECTION ---
                        # Re-calc box on large frame
                        box_small = list(map(int, primary_face[:4]))
                        scale_x = frame_width / det_w
                        scale_y = frame_height / det_h
                        x, y, w, h = int(box_small[0]*scale_x), int(box_small[1]*scale_y), int(box_small[2]*scale_x), int(box_small[3]*scale_y)
                        
                        # Safety padding
                        x, y = max(0, x), max(0, y)
                        
                        # Eye Region of Interest (ROI) - Top 50%
                        face_roi = frame[y:y+h, x:x+w]
                        eye_roi_h = int(h * 0.50)
                        eye_roi = face_roi[0:eye_roi_h, :]
                        
                        eyes_detected_vis = [] # For drawing
                        
                        if eye_roi.size > 0:
                            gray_eyes = cv2.cvtColor(eye_roi, cv2.COLOR_BGR2GRAY)
                            # Looser threshold: Scale 1.1, Neighbors 3 (easier to find eyes)
                            eyes = eye_detector.detectMultiScale(gray_eyes, 1.1, 3)
                            
                            eyes_open = len(eyes) > 0
                            
                            for (ex, ey, ew, eh) in eyes:
                                eyes_detected_vis.append((x+ex, y+ey, ew, eh))
                            
                            if not eyes_open:
                                blink_counter += 1
                                print(f"Eyes Closed: {blink_counter}")
                            else:
                                # We saw eyes open. Was it closed previously?
                                if blink_counter > 3: # Threshold: at least 3-4 frames (Less sensitive)
                                    print(">>> BLINK TRIGGERED! <<<")
                                    attn_state = "RECOGNIZING"
                                blink_counter = 0

                        # Visual Feedback
                        debug_color = (0, 0, 255) # Red (Closed/Waiting)
                        if blink_counter == 0: debug_color = (255, 0, 0) # Blue (Open)
                        
                        detected_results = [( [x,y,w,h], f"Blink Now ({blink_counter})", 0.0)]
                        
                        # DRAW DEBUGGING
                        # 1. Draw Eye ROI Box (Where it thinks eyes are)
                        cv2.rectangle(frame, (x, y), (x+w, y+eye_roi_h), (255, 255, 0), 1)
                        # 2. Draw Detected Eyes
                        for (ex, ey, ew, eh) in eyes_detected_vis:
                            cv2.rectangle(frame, (ex, ey), (ex+ew, ey+eh), (0, 255, 255), 1)
                            
                    else:
                        attn_state = "SEARCHING"

                elif attn_state == "RECOGNIZING":
                    # Perform Recognition
                    # Uses target_face_data from YuNet (on small frame)
                    aligned_face = recognizer.alignCrop(small_frame, target_face_data)
                    face_feature = recognizer.feature(aligned_face)
                    
                    best_name = "Unknown"
                    max_score = 0.0
                    for name, known_feature in known_faces.items():
                        sim_score = recognizer.match(face_feature, known_feature, cv2.FaceRecognizerSF_FR_COSINE)
                        if sim_score > max_score and sim_score > COSINE_THRESHOLD:
                            max_score = sim_score
                            best_name = name
                    
                    if best_name != "Unknown":
                        log_event("ENTERED", best_name, frame)
                        present_people[best_name] = time.time() # Track in lobby
                        speak(f"Attendance registered, {best_name}")
                        detected_results = [( [x,y,w,h], f"SUCCESS: {best_name}", max_score)]
                        attn_state = "COOLDOWN"
                        state_timer = current_time
                    else:
                        speak("Face not recognized")
                        attn_state = "SEARCHING" # Retry

                elif attn_state == "COOLDOWN":
                    detected_results = [( [x,y,w,h], f"Done. ({int(5.0 - (current_time-state_timer))}s)", 1.0)]
                    if (current_time - state_timer) > 4.0:
                        attn_state = "SEARCHING"

        frame_count += 1
        
        # --- DISPLAY RESULTS (Common) ---
        for box, name, conf in detected_results:
            x, y, w, h = box
            color = (0, 255, 0)
            if name == "Unknown" or "Blink" in name:
                color = (0, 255, 255)
            
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.rectangle(frame, (x, y + h - 35), (x + w, y + h), color, cv2.FILLED)
            label = f"{name}"
            if conf > 0: label += f" ({int(conf*100)}%)"
            cv2.putText(frame, label, (x + 6, y + h - 6), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

        # Show Status
        status_y = 60
        cv2.putText(frame, "LOBBY:", (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        for idx, (name, _) in enumerate(present_people.items()):
            if idx > 4: break # Limit display
            status_y += 25
            cv2.putText(frame, f"- {name}", (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        if show_local_preview:
            cv2.imshow('Visor Attendance (Dual Mode)', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('m'): # TOGGLE MODE
                current_mode = "ATTENDANCE" if current_mode == "SURVEILLANCE" else "SURVEILLANCE"
                print(f"SWITCHED MODE TO: {current_mode}")
                attn_state = "SEARCHING" # Reset
                
                # Recording Logic: MANUAL ONLY now.
                # Switching modes does NOT auto-trigger recording.
        else:
            # If no window, we save CPU but still need to allow interrupt? 
            # With no window, cv2.waitKey won't work for 'q'. 
            # Users must close the console or Use Web UI to stop.
            try:
                cv2.destroyWindow('Visor Attendance (Dual Mode)')
            except: pass
            time.sleep(0.01)

        # --- RECORD FRAME (Works even if preview hidden) ---
        if video_writer is not None:
            video_writer.write(frame)

    video_capture.release()
    cv2.destroyAllWindows()

def run_flask_app():
    # Run server on 0.0.0.0 to allow LAN access
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    # Start Flask in a separate THREAD (not Process) so it can share memory (frame_buffer)
    # This is much more efficient for the Live Stream feature.
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Get Local IP for Mobile Access
    def get_local_ip():
        try:
            # Connect to a public DNS server to find the interface used for internet/LAN (doesn't send data)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            try:
                return socket.gethostbyname(socket.gethostname())
            except:
                return "localhost"

    local_ip = get_local_ip()

    print("---------------------------------------")
    print(" VISOR AI ATTENDANCE SYSTEM v2.5")
    print(" MODE: Dual (Attendance + Surveillance)")
    print(f" SERVER: http://localhost:5000 (Local)")
    print(f" MOBILE: http://{local_ip}:5000 (Same Wi-Fi)")
    print("---------------------------------------")
    
    run_face_recognition_loop()
