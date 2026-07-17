// static/js/features/globe.js
document.addEventListener("DOMContentLoaded", () => {
    const globeContainer = document.getElementById('globeViz');
    if (!globeContainer) return;

    // Fetch our geocoded location data
    fetch('/api/globe-data')
        .then(res => res.json())
        .then(data => {
            // Filter out invalid points just in case
            const points = data.filter(d => d.lat !== null && d.lng !== null);

            // Initialize Globe
            const world = Globe()(globeContainer)
                .globeImageUrl('https://unpkg.com/three-globe/example/img/earth-night.jpg')
                .bumpImageUrl('https://unpkg.com/three-globe/example/img/earth-topology.png')
                .backgroundColor('rgba(0,0,0,0)')
                .pointsData(points)
                .pointLat('lat')
                .pointLng('lng')
                .pointColor('color')
                .pointAltitude(d => d.size * 0.1) // Height of point
                .pointRadius(d => d.size * 0.5) // Radius of point
                .pointsMerge(true) // Merge for performance
                .pointsTransitionDuration(1000)
                // Add html elements for labels
                .htmlElementsData(points)
                .htmlElement(d => {
                    const el = document.createElement('div');
                    el.innerHTML = `
                        <div style="color: #fff; background: rgba(0,0,0,0.6); padding: 2px 6px; border-radius: 4px; font-size: 10px; cursor: pointer; white-space: nowrap; border: 1px solid rgba(225, 29, 72, 0.5); pointer-events: auto;">
                            ${d.title}
                        </div>
                    `;
                    el.onclick = () => {
                        window.location.href = d.url;
                    };
                    return el;
                });

            // Adjust controls
            world.controls().autoRotate = true;
            world.controls().autoRotateSpeed = 0.5;
            world.controls().enableZoom = true;
            
            // Adjust camera distance
            world.camera().position.z = 250;

            // Handle Resize
            window.addEventListener('resize', () => {
                world.width(globeContainer.clientWidth);
                world.height(globeContainer.clientHeight);
            });
        })
        .catch(err => console.error("Error loading globe data:", err));
});
