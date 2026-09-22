#!/usr/bin/env node
/**
 * Рендер PNG-секвенции из анимированного SVG через Puppeteer.
 * Используется Makefile, если svgasm недоступен.
 *
 * Требуется: npm install puppeteer
 */

const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const FPS = 30;
const DURATION = 15;
const TOTAL = FPS * DURATION;

const SVG = path.resolve('assets/final_frame_animated_16x9.svg');
const OUT = path.resolve('exports');

(async () => {
  fs.mkdirSync(OUT, { recursive: true });

  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });

  await page.goto('file://' + SVG, { waitUntil: 'networkidle0' });

  // Пауза, чтобы SMIL стартовал
  await new Promise((r) => setTimeout(r, 500));

  for (let i = 0; i < TOTAL; i++) {
    const file = path.join(OUT, `frame_${String(i).padStart(4, '0')}.png`);
    await page.screenshot({ path: file, omitBackground: false });

    if (i % 30 === 0) {
      process.stdout.write(`  frame ${i + 1}/${TOTAL}\r`);
    }

    await new Promise((r) => setTimeout(r, 1000 / FPS));
  }

  await browser.close();
  console.log(`\n  ✓ ${TOTAL} кадров записано в ${OUT}/`);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});