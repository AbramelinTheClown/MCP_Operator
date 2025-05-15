const stage = document.getElementById('stage');
const sceneContainers = stage.querySelectorAll('.scene-container');

function showScene(sceneIdToShow) {
    console.log("Showing scene:", sceneIdToShow); // Debug log

    sceneContainers.forEach(container => {
        if (container.id === sceneIdToShow) {
            container.classList.add('active');
            // Optionally add classes to specific layers for animation when scene becomes active
             const owl = container.querySelector('#night-owl');
             if (owl) owl.classList.add('active');

        } else {
            container.classList.remove('active');
            // Optionally remove animation classes when scene becomes inactive
             const owl = container.querySelector('#night-owl');
             if (owl) owl.classList.remove('active');
        }
    });
}

// Initialize by showing the first scene (optional)
document.addEventListener('DOMContentLoaded', () => {
    if (sceneContainers.length > 0) {
        // Get the ID of the first scene defined in the HTML
        const firstSceneId = sceneContainers[0].id;
        showScene(firstSceneId);
    }
});