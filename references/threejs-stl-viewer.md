# Three.js STL Viewer for Flask Upload Pages

Embed an interactive 3D STL preview in any Flask template using Three.js (CDN). The viewer appears after a user uploads/drops an STL file — they can rotate, zoom, and inspect the model before submitting.

## Dependencies

Load via CDN in the template's `{% block head %}`:

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/STLLoader.js"></script>
```

## Container

Add a div where the viewer will render (initially hidden):

```html
<div id="stl-viewer-container" style="width:100%; height:350px; margin-top:1rem;
     border:1px solid var(--border); border-radius:4px; overflow:hidden; display:none;"></div>
```

## Viewer Class

Save as `static/js/stl-viewer.js`:

```javascript
class STLViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.width = this.container.clientWidth || 400;
        this.height = this.container.clientHeight || 300;

        // Scene setup
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0a12);

        this.camera = new THREE.PerspectiveCamera(45, this.width/this.height, 0.1, 1000);
        this.camera.position.set(15, 10, 15);
        this.camera.lookAt(0, 0, 0);

        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.renderer.setSize(this.width, this.height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.container.appendChild(this.renderer.domElement);

        // Grid + lights
        // ... (ambient, directional key light #f7931a, fill #4488ff, rim #ff4488)

        // Orbit ring particles
        // ... (200 point ring rotating around model)

        // Mouse interaction: drag to rotate, wheel to zoom
        this.isDragging = false;
        this.autoRotate = true;

        this.renderer.domElement.addEventListener('mousedown', ...);
        this.renderer.domElement.addEventListener('mousemove', ...);
        this.renderer.domElement.addEventListener('mouseup', ...);
        this.renderer.domElement.addEventListener('wheel', ...);

        this.mesh = null;
        this.animate();
    }

    loadSTL(url) {
        const loader = new THREE.STLLoader();
        loader.load(url, geometry => {
            if (this.mesh) this.scene.remove(this.mesh);
            geometry.computeVertexNormals();
            geometry.center();
            const material = new THREE.MeshPhongMaterial({
                color: 0xf7931a, specular: 0x111111, shininess: 30,
                emissive: 0x331100, emissiveIntensity: 0.3,
            });
            this.mesh = new THREE.Mesh(geometry, material);
            this.scene.add(this.mesh);
            // Auto-zoom to fit
            geometry.computeBoundingBox();
            const box = geometry.boundingBox;
            const size = Math.max(box.max.x-box.min.x, box.max.y-box.min.y, box.max.z-box.min.z);
            this.camera.position.set(size*1.5, size*1.2, size*1.5);
            this.camera.lookAt(0, 0, 0);
        });
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        if (this.autoRotate && !this.isDragging) this.rotation.y += 0.005;
        if (this.mesh) { this.mesh.rotation.x = this.rotation.x; this.mesh.rotation.y = this.rotation.y; }
        this.ring.rotation.y += 0.003;
        this.renderer.render(this.scene, this.camera);
    }
}
```

## Integration with Upload JS

After the user selects/drops a file and the STL analysis succeeds:

```javascript
const viewerContainer = document.getElementById('stl-viewer-container');
viewerContainer.style.display = 'block';

if (window._stlViewer) {
    // Reuse existing viewer
    window._stlViewer.loadSTL(URL.createObjectURL(file));
} else {
    window._stlViewer = new STLViewer('stl-viewer-container');
    // Small delay to let DOM settle
    setTimeout(() => window._stlViewer.loadSTL(URL.createObjectURL(file)), 500);
}
```

## Key Design Decisions

- **Orange Bitcoin theme:** model color `0xf7931a`, emissive `0x331100`, key light `#f7931a`
- **Dark background:** `0x0a0a12` blends with dark site themes
- **Auto-fit:** after loading, reposition camera based on model bounding box
- **Particle ring:** 200-point orbit ring provides a cyberpunk/bitcoin aesthetic
- **No reset:** reusing the viewer across file changes avoids flicker

## Pitfalls

- **Three.js r128 CDN paths** — the STL loader lives under `examples/js/loaders/`, not the main module
- **STL files from `URL.createObjectURL()`** expire when the page unloads — don't persist the URL
- **Mobile touch** — implement touch equivalents of mousedown/move/up for mobile zoom/rotate
- **Large STLs** — files with >100k triangles may lag during auto-rotate. Set `this.autoRotate = false` on initial drag to give the user control
