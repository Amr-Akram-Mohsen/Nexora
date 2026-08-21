// static/js/features/globe.js
document.addEventListener("DOMContentLoaded", () => {
    const globeContainer = document.getElementById('globeViz');
    if (!globeContainer) return;

    const globeUrl = window.APP?.urls?.globeData || '/api/globe-data';

    // Fetch our geocoded location data
    fetch(globeUrl)
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
                .pointColor(() => '#e11d48')
                .pointAltitude(d => d.size * 0.1) // Height of point
                .pointRadius(d => d.size * 0.5) // Radius of point
                .pointsMerge(true) // Merge for performance
                .pointsTransitionDuration(1000)
                // Add html elements for labels
                .htmlElementsData(points)
                .htmlElement(d => {
                    const el = document.createElement('div');
                    const label = document.createElement('div');
                    label.className = 'globe-label';
                    label.textContent = d.title;
                    el.appendChild(label);
                    el.onclick = () => {
                        window.location.href = d.url || `/sections/news?location=${encodeURIComponent(d.slug)}`;
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
