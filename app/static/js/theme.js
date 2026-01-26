// Check and apply theme immediately (to prevent FOUC)
(function () {
    const savedTheme = localStorage.getItem('theme');
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme === 'dark' || (!savedTheme && systemDark)) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
})();

document.addEventListener('DOMContentLoaded', () => {
    // Create Toggle Button
    const btn = document.createElement('button');
    btn.className = 'fixed bottom-6 left-6 z-50 p-3 rounded-full shadow-xl transition-all duration-300 backdrop-blur-md border group';

    // Style based on current mode (Reactive classes)
    const updateBtnStyle = () => {
        const isDark = document.documentElement.classList.contains('dark');
        if (isDark) {
            btn.className = 'fixed bottom-6 left-6 z-50 p-3 rounded-full shadow-xl transition-all duration-300 backdrop-blur-md border border-white/20 bg-slate-800/50 text-yellow-400 hover:bg-slate-700 hover:scale-110';
            btn.innerHTML = '☀️'; // Sun icon for switching to light
            btn.title = "Aydınlık Mod'a Geç";
        } else {
            btn.className = 'fixed bottom-6 left-6 z-50 p-3 rounded-full shadow-xl transition-all duration-300 backdrop-blur-md border border-slate-200 bg-white/80 text-slate-700 hover:bg-white hover:scale-110';
            btn.innerHTML = '🌙'; // Moon icon for switching to dark
            btn.title = "Karanlık Mod'a Geç";
        }
    };

    updateBtnStyle();

    btn.onclick = () => {
        document.documentElement.classList.toggle('dark');
        const isDark = document.documentElement.classList.contains('dark');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');

        // Update Canvas Colors if it exists (bg-animation.js)
        if (window.resizeCanvas) window.resizeCanvas();

        updateBtnStyle();
    };

    document.body.appendChild(btn);
});
