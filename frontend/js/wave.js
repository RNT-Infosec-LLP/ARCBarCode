/**
 * Lightweight canvas-based animated "ocean" wave background.
 * Draws several layered sine waves that scroll slowly for a soft, ambient feel.
 */
(function () {
  const canvas = document.getElementById("wave-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  let width, height, dpr;

  // Each layer: color, amplitude, wavelength, speed, vertical offset (0-1 of height), opacity
  const layers = [
    { color: "#c9d7fb", amplitude: 26, wavelength: 480, speed: 0.0035, offset: 0.62, alpha: 0.55 },
    { color: "#b9caf9", amplitude: 34, wavelength: 360, speed: 0.0055, offset: 0.72, alpha: 0.55 },
    { color: "#a7bdf7", amplitude: 22, wavelength: 300, speed: 0.0075, offset: 0.84, alpha: 0.65 },
    { color: "#93aef5", amplitude: 30, wavelength: 260, speed: 0.0095, offset: 0.94, alpha: 0.75 },
  ];

  function resize() {
    dpr = window.devicePixelRatio || 1;
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function drawWave(layer, t) {
    const baseY = height * layer.offset;
    ctx.beginPath();
    ctx.moveTo(0, height);
    ctx.lineTo(0, baseY);
    for (let x = 0; x <= width; x += 8) {
      const y =
        baseY +
        Math.sin(x / layer.wavelength + t * layer.speed) * layer.amplitude +
        Math.sin(x / (layer.wavelength * 0.5) + t * layer.speed * 1.4) * (layer.amplitude * 0.3);
      ctx.lineTo(x, y);
    }
    ctx.lineTo(width, height);
    ctx.closePath();
    ctx.fillStyle = layer.color;
    ctx.globalAlpha = layer.alpha;
    ctx.fill();
  }

  let frame = 0;
  function render() {
    ctx.clearRect(0, 0, width, height);
    layers.forEach((layer) => drawWave(layer, frame));
    ctx.globalAlpha = 1;
    frame += 1;
    requestAnimationFrame(render);
  }

  window.addEventListener("resize", resize);
  resize();
  render();
})();
