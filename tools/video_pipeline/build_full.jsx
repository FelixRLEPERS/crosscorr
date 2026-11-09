// build_full.jsx — FULL Phase 2: build missing comps + swap 3/5 PNG bg -> video.
//
// * For slides in NEW (1,2,4,6,7,8): create CrossCorr_slide-N comp if absent:
//   video bg (slide-N_1080.mp4) + [footline if not plain] + block-01-content
//   + hud-onair-NN + hud-frame, 24fps, comp duration = video duration.
// * For slides 3/5 (existing comps from MVP): replace PNG bg source with
//   video, set comp fps=24 and duration=video duration (as swap_bg.jsx).
// * Saves project AS A COPY (G:/crosscorr/media/video_bg/crosscorr_full.aep);
//   original crosscorr.aep is not modified on disk. Closes the copy in the
//   GUI (so aerender can open it from disk). Leaves AE running, no dialogs.
//
// Run: AfterFX.exe -s "$.evalFile(new File('C:/.../build_full.jsx'))"
(function () {
    var LOG = "C:/Users/FelixR/AppData/Local/Temp/opencode/ae_log.txt";
    var PROJ = "G:/crosscorr/aep/crosscorr.aep";
    var COPY = "G:/crosscorr/media/video_bg/crosscorr_full.aep";
    var LAYERS = "G:/crosscorr/media/ae_layers/";
    var VIDEO = "G:/crosscorr/media/video_bg/";
    var NEW = [1, 2, 4, 6, 7, 8];
    var SWAP = [3, 5];
    var PLAIN = { 1: true, 8: true }; // plain frames in deck: no footline bar

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
    function findComp(name) {
        for (var i = 1; i <= app.project.numItems; i++) {
            var it = app.project.item(i);
            if (it instanceof CompItem && it.name === name) return it;
        }
        return null;
    }
    function importFile(path) {
        for (var i = 1; i <= app.project.numItems; i++) {
            var f2 = app.project.item(i);
            if (f2 instanceof FootageItem && f2.file && norm(f2.file.fsName) === norm(path)) {
                return f2;
            }
        }
        return app.project.importFile(new ImportOptions(new File(path)));
    }

    try {
        log("build_full v1: AE " + app.version);

        var opened = false;
        try {
            if (app.project.file && norm(app.project.file.fsName) === PROJ) opened = true;
        } catch (e) {}
        if (opened) {
            log("project already open: " + PROJ);
        } else {
            log("opening " + PROJ);
            app.open(new File(PROJ));
            log("opened, numItems=" + app.project.numItems);
        }

        // --- 1) build missing comps -------------------------------------
        for (var a = 0; a < NEW.length; a++) {
            var n = NEW[a];
            var cname = "CrossCorr_slide-" + n;
            if (findComp(cname)) {
                log(cname + ": exists, skip build");
                continue;
            }

            var videoPath = VIDEO + "slide-" + n + "_1080.mp4";
            var contentPath = LAYERS + "slide-" + n + "/block-01-content.png";
            if (!new File(videoPath).exists) {
                log("MISS video: " + videoPath + " (build skipped)");
                continue;
            }
            if (!new File(contentPath).exists) {
                log("MISS content: " + contentPath + " (build skipped)");
                continue;
            }

            var vfoot = importFile(videoPath);
            var comp = app.project.items.addComp(cname, 1920, 1080, 1.0, vfoot.duration, 24);

            // layers bottom-up: bg, [footline], content, hud number, hud frame
            var files = [videoPath];
            if (!PLAIN[n]) files.push(LAYERS + "shared/footline-frame.png");
            files.push(contentPath);
            files.push(LAYERS + "shared/hud-onair-0" + n + ".png");
            files.push(LAYERS + "shared/hud-frame.png");

            var count = 0;
            for (var b = 0; b < files.length; b++) {
                var fp = files[b];
                if (!new File(fp).exists) {
                    log("  SKIP (missing): " + fp);
                    continue;
                }
                var foot = importFile(fp);
                var layer = comp.layers.add(foot);
                layer.name = new File(fp).name.replace(/\.(png|mp4)$/i, "");
                count++;
            }
            // normalize layer timing to comp length
            for (var j = 1; j <= comp.numLayers; j++) {
                comp.layer(j).inPoint = 0;
                comp.layer(j).outPoint = comp.duration;
            }
            comp.workAreaStart = 0;
            comp.workAreaDuration = comp.duration;
            log(
                cname + ": BUILT, layers=" + count + "/" + files.length +
                ", dur=" + comp.duration + ", fps=" + comp.frameRate
            );
        }

        // --- 2) swap PNG bg -> video in existing comps 3/5 --------------
        for (var s = 0; s < SWAP.length; s++) {
            var num = SWAP[s];
            var sc = findComp("CrossCorr_slide-" + num);
            if (!sc) {
                log("MISS comp slide-" + num);
                continue;
            }
            var bgLayer = null;
            for (var k = 1; k <= sc.numLayers; k++) {
                if (sc.layer(k).name.indexOf("-bg") >= 0) {
                    bgLayer = sc.layer(k);
                    break;
                }
            }
            if (!bgLayer) bgLayer = sc.layer(sc.numLayers);
            var vpath = VIDEO + "slide-" + num + "_1080.mp4";
            if (!new File(vpath).exists) {
                log("MISS video for swap: " + vpath);
                continue;
            }
            var vf = importFile(vpath);
            bgLayer.replaceSource(vf, false);
            bgLayer.name = "slide-" + num + "_1080";
            bgLayer.inPoint = 0;
            bgLayer.outPoint = vf.duration;
            sc.frameRate = 24;
            sc.duration = vf.duration;
            sc.workAreaStart = 0;
            sc.workAreaDuration = vf.duration;
            log(
                sc.name + ": swapped bg -> video, fps=24, dur=" + sc.duration
            );
        }

        // --- 3) save as copy, close it in GUI ---------------------------
        app.project.save(new File(COPY));
        log("saved copy: " + COPY);
        app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
        log("closed copy in GUI; original crosscorr.aep untouched; AE running");
    } catch (err) {
        log("ERROR: " + err);
    }
})();
