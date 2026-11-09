// swap_bg.jsx — Phase 2: PNG bg -> video bg in CrossCorr_slide-3/5.
// Replaces bottom bg layer source, sets comp fps=24 + duration=video,
// saves project AS A COPY (original crosscorr.aep untouched on disk),
// closes the copy in the GUI so aerender can open it from disk.
// Leaves AE running (no quit, no dialogs).
(function () {
    var LOG = "C:/Users/FelixR/AppData/Local/Temp/opencode/ae_log.txt";
    var PROJ = "G:/crosscorr/aep/crosscorr.aep";
    var COPY = "G:/crosscorr/media/video_bg/crosscorr_phase2.aep";
    var SLIDES = [3, 5];

    function log(s) {
        var f = new File(LOG);
        f.encoding = "UTF-8";
        f.open("a");
        f.write(s + "\n");
        f.close();
    }
    function norm(s) {
        return String(s).replace(/\\/g, "/");
    }

    try {
        log("swap_bg v1: AE " + app.version);

        var opened = false;
        try {
            if (app.project.file &&
                norm(app.project.file.fsName) === PROJ) {
                opened = true;
            }
        } catch (e) {}
        if (opened) {
            log("project already open: " + PROJ);
        } else {
            log("opening " + PROJ);
            app.open(new File(PROJ));
            log("opened, numItems=" + app.project.numItems);
        }

        for (var s = 0; s < SLIDES.length; s++) {
            var num = SLIDES[s];

            // --- find comp ---
            var comp = null;
            for (var i = 1; i <= app.project.numItems; i++) {
                var it = app.project.item(i);
                if (it instanceof CompItem &&
                    it.name === "CrossCorr_slide-" + num) {
                    comp = it;
                    break;
                }
            }
            if (!comp) { log("MISS comp CrossCorr_slide-" + num); continue; }

            // --- video file ---
            var videoPath =
                "G:/crosscorr/media/video_bg/slide-" + num + "_1080.mp4";
            var vf = new File(videoPath);
            if (!vf.exists) { log("MISS video " + videoPath); continue; }

            // --- find bg layer (name contains -bg, else bottom layer) ---
            var bgLayer = null;
            for (var j = 1; j <= comp.numLayers; j++) {
                if (comp.layer(j).name.indexOf("-bg") >= 0) {
                    bgLayer = comp.layer(j);
                    break;
                }
            }
            if (!bgLayer) bgLayer = comp.layer(comp.numLayers);
            var oldName = bgLayer.name;

            // --- import (reuse if already imported) ---
            var foot = null;
            for (var k = 1; k <= app.project.numItems; k++) {
                var f2 = app.project.item(k);
                if (f2 instanceof FootageItem && f2.file &&
                    norm(f2.file.fsName) === videoPath) {
                    foot = f2;
                    break;
                }
            }
            if (!foot) {
                foot = app.project.importFile(new ImportOptions(vf));
            }
            log(comp.name + ": footage " + foot.name + " dur=" +
                foot.duration + " " + foot.width + "x" + foot.height +
                " @" + foot.mainSource.frameRate);

            // --- swap source, keep transforms ---
            bgLayer.replaceSource(foot, false);
            bgLayer.name = "slide-" + num + "_1080";
            bgLayer.inPoint = 0;
            bgLayer.outPoint = foot.duration;

            // --- comp timing: 24fps + video duration ---
            comp.frameRate = 24;
            comp.duration = foot.duration;
            comp.workAreaStart = 0;
            comp.workAreaDuration = foot.duration;

            log(comp.name + ": '" + oldName + "' -> '" + bgLayer.name +
                "', fps=24, dur=" + comp.duration + ", layers=" +
                comp.numLayers);
        }

        // --- save as copy (open project re-points to COPY), then close ---
        app.project.save(new File(COPY));
        log("saved copy: " + COPY);
        app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
        log("closed copy in GUI; original crosscorr.aep untouched; AE running");
    } catch (err) {
        log("ERROR: " + err);
    }
})();
