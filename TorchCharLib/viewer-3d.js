(function () {
  "use strict";

  let renderer, scene, camera, controls, animId;
  let currentModel = null;
  let activeContainer = null;

  function initScene(container) {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.prepend(renderer.domElement);

    camera = new THREE.PerspectiveCamera(45, 1, 0.1, 10000);
    camera.position.set(0, 150, 300);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.target.set(0, 80, 0);
    controls.update();

    var ambient = new THREE.AmbientLight(0x404040, 0.6);
    scene.add(ambient);

    var key = new THREE.DirectionalLight(0xffffff, 1.0);
    key.position.set(100, 200, 150);
    scene.add(key);

    var fill = new THREE.DirectionalLight(0xffffff, 0.4);
    fill.position.set(-100, 100, -50);
    scene.add(fill);

    var rim = new THREE.DirectionalLight(0xffffff, 0.3);
    rim.position.set(0, 50, -200);
    scene.add(rim);

    var grid = new THREE.GridHelper(400, 20, 0x333355, 0x222244);
    scene.add(grid);

    resize();
  }

  function resize() {
    if (!renderer || !activeContainer) return;
    var w = activeContainer.offsetWidth;
    var h = activeContainer.offsetHeight;
    if (w === 0 || h === 0) return;
    renderer.setSize(w, h, false);
    renderer.domElement.style.width = w + "px";
    renderer.domElement.style.height = h + "px";
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  function animate() {
    animId = requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }

  function stopAnimate() {
    if (animId) cancelAnimationFrame(animId);
    animId = null;
  }

  function clearModel() {
    if (currentModel) {
      scene.remove(currentModel);
      currentModel.traverse(function (child) {
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
          if (Array.isArray(child.material)) child.material.forEach(function (m) { m.dispose(); });
          else child.material.dispose();
        }
      });
      currentModel = null;
    }
  }

  function fitCamera(object) {
    var box = new THREE.Box3().setFromObject(object);
    var size = box.getSize(new THREE.Vector3());
    var center = box.getCenter(new THREE.Vector3());

    var maxDim = Math.max(size.x, size.y, size.z);
    var fov = camera.fov * (Math.PI / 180);
    var dist = maxDim / (2 * Math.tan(fov / 2));
    dist *= 1.6;

    controls.target.copy(center);
    camera.position.set(center.x + dist * 0.5, center.y + dist * 0.3, center.z + dist);
    camera.lookAt(center);
    controls.update();
  }

  function destroyViewer() {
    stopAnimate();
    clearModel();
    if (activeContainer) hideStats(activeContainer);
    if (renderer) {
      renderer.dispose();
      if (renderer.domElement && renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
      renderer = null;
    }
    if (controls) { controls.dispose(); controls = null; }
    scene = null;
    camera = null;
    activeContainer = null;
  }

  function setProgress(container, pct) {
    var fill = container.querySelector("#progressFill");
    var text = container.querySelector("#progressText");
    if (fill) fill.style.width = pct + "%";
    if (text) text.textContent = pct + "%";
  }

  function hideProgress(container) {
    var el = container.querySelector("#inlineViewerProgress");
    if (el) el.style.display = "none";
  }

  function countVertices(object) {
    var total = 0;
    object.traverse(function (child) {
      if (child.isMesh && child.geometry) {
        var pos = child.geometry.getAttribute("position");
        if (pos) total += pos.count;
      }
    });
    return total;
  }

  function formatNumber(n) {
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  function showStats(container, vertCount) {
    var el = container.querySelector("#inlineViewerStats");
    if (!el) {
      el = document.createElement("div");
      el.className = "inline-viewer-stats";
      el.id = "inlineViewerStats";
      container.appendChild(el);
    }
    el.textContent = "顶点总数: " + formatNumber(vertCount);
    el.style.display = "";
  }

  function hideStats(container) {
    var el = container.querySelector("#inlineViewerStats");
    if (el) el.style.display = "none";
  }

  function loadFBX(container, url, onDone) {
    setProgress(container, 0);

    var loader = new THREE.FBXLoader();
    loader.load(
      url,
      function (fbx) {
        var defaultMat = new THREE.MeshStandardMaterial({
          color: 0x888888,
          roughness: 0.6,
          metalness: 0.1,
          side: THREE.DoubleSide
        });
        fbx.traverse(function (child) {
          if (child.isMesh) {
            if (child.material) {
              if (Array.isArray(child.material)) child.material.forEach(function (m) { m.dispose(); });
              else child.material.dispose();
            }
            child.material = defaultMat;
          }
        });
        scene.add(fbx);
        currentModel = fbx;
        fitCamera(fbx);
        showStats(container, countVertices(fbx));
        setProgress(container, 100);
        setTimeout(function () { hideProgress(container); }, 300);
        if (onDone) onDone();
      },
      function (progress) {
        if (progress.total) {
          var pct = Math.min(99, Math.round((progress.loaded / progress.total) * 100));
          setProgress(container, pct);
        }
      },
      function (err) {
        console.error("FBX load error:", err);
        var text = container.querySelector("#progressText");
        if (text) text.textContent = "加载失败";
        var fill = container.querySelector("#progressFill");
        if (fill) fill.style.background = "#ef4444";
        if (onDone) onDone();
      }
    );
  }

  function initInlineViewer(container, fbxPath, onDone) {
    if (!fbxPath) return;

    destroyViewer();
    activeContainer = container;
    initScene(container);

    requestAnimationFrame(function () {
      resize();
      animate();

      var normalized = fbxPath.replace(/\\/g, "/");
      var url;
      if (window.location.protocol === "file:") {
        var segs = normalized.split("/").filter(Boolean);
        var encoded = segs.map(function (s, i) { return (i === 0 && /:$/.test(s)) ? s : encodeURIComponent(s); }).join("/");
        url = "file:///" + encoded;
      } else {
        var driveMatch = normalized.match(/^([A-Za-z]):\//);
        if (driveMatch) {
          var drive = driveMatch[1].toLowerCase();
          var rest = normalized.slice(3);
          var segs2 = rest.split("/").filter(Boolean);
          var encoded2 = segs2.map(function (s) { return encodeURIComponent(s); }).join("/");
          url = "/" + drive + "-drive/" + encoded2;
        } else {
          var segs3 = normalized.split("/").filter(Boolean);
          var encoded3 = segs3.map(function (s) { return encodeURIComponent(s); }).join("/");
          url = "/local-files/" + encoded3;
        }
      }
      console.log("[3D Viewer] loading:", url);
      loadFBX(container, url, onDone);
    });
  }

  window.addEventListener("resize", resize);
  window.__initInlineViewer = initInlineViewer;
  console.log("[3D Viewer] ready");
})();
