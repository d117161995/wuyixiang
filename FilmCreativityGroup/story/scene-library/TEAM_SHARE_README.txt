Team sharing mode (Vite build)

1) One-time setup on host machine
- Install Node.js 18+
- Run in project root: npm install
- Build once: npm run build:web

2) Start shared service on host machine
- Double click: start-dist.cmd
- Default port: 5173
- URLs:
  - local: http://localhost:5173/
  - LAN:   http://<host-ip>:5173/

3) Colleagues access (no Node.js needed)
- Open in browser: http://<host-ip>:5173/
- Key pages:
  - planning page: /泡面番策划展示.html
  - scene library: /scene-library/index.html

4) Update flow
- Image source changes: run tools\update_scene_db.mjs (or use refresh button)
- Web code changes: rerun npm run build:web, then restart start-dist.cmd

5) Troubleshooting
- Page not reachable: open TCP 5173 in host firewall
- Page works but images missing: check SENCE_DIR network path permission
- Slow performance: host should use wired LAN when possible
